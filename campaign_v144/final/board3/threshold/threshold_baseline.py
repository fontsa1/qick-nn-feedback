"""A same-board, same-build threshold-feedback baseline for "an NN costs no latency".

Stock QICK feedback on our v1.44 build: readout 0 (the stock FIR path) accumulates the same 576-sample window and sends its
sum to tProc input 0 ("feedback to tProc input 0" in the board banner); the tProc program waits, reads that input
(DPORT_RD, exactly what QICK's read_and_jump emits), compares I with a threshold and plays the conditional pulse ASAP
(cp_slack < 0, as tproc_path_v143.py). Measured exactly like the NN tProc path (tproc_path_v143.py, same L_buf: window's
last sample to the pulse's 50% point, both on readout 0's time base), in the same session, so three numbers are directly
comparable: threshold via tProc, NN_live via tProc, NN_live via the gate (L_buf of the in-loop campaign).

Freshness for the threshold read: the port value is fresh if it tracks this shot's window sum (from the host's own
capture of the same window) better than the previous shot's. Branch correctness: branch == (I >= threshold). Forced
branches (threshold far outside the range) give the two pulse levels, as in tproc_path_v143.py.

  QICK_NS_HOST=$QICK_BOARD_A QICK_LIVE_N=576 QICK_BANNER="Nov  7 19:57:07" python campaign_v144/final/board3/threshold/threshold_baseline.py \
      --out campaign_v144/final/board3/threshold/A_threshold.json
"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "analysis_scripts" / "diagnostics"))
import tproc_path_v143 as T  # noqa: E402  (brings up soc; QICK_BANNER selects the expected build)

L, C, h, soc, soccfg, CFG0 = T.L, T.C, T.h, T.soc, T.soccfg, T.CFG0
RO_IN = soccfg["readouts"][0]["tproc_ch"]          # tProc input fed by readout 0's accumulated result


class ThrProg(L.LatProg):
    """Stock threshold feedback: trace + readout 0 window, wait, DPORT_RD readout 0's input, TEST I - thr, branch, pulse."""

    def _body(s, cf):
        s.pulse(ch=cf["gen_ch"], name="p")
        s.send_readoutconfig(ch=cf["ro_ch"], name="r", t=0)
        s.trigger(ros=[cf["ro_ch"]], t=cf["adc_trig_offset"], width=cf["trig_width"])
        t_dec = cf["adc_trig_offset"] + C.live_len(cf) + cf["fb_margin"]
        t_cp = t_dec + cf["cp_slack"]
        s.trigger(ros=[cf["ro_ch"]], t=t_dec + cf["adc_trig_offset"] - cf["cp_pre"], width=cf["trig_width"])
        s.wait(t=t_dec)
        s.asm_inst({"CMD": "DPORT_RD", "DST": str(RO_IN)})
        s.cond_jump("fb_one", "s_port_l", "NS", "-", cf["fb_thr"])
        s.pulse(ch=cf["gen_ch"], name="c0", t=t_cp)
        s.write_dmem(2, 0)
        s.jump("fb_done")
        s.label("fb_one")
        s.pulse(ch=cf["gen_ch"], name="c1", t=t_cp)
        s.write_dmem(2, 1)
        s.label("fb_done")
        s.write_dmem(0, "s_port_l")
        s.write_dmem(1, "s_port_h")


def thr_shot(wf, cf, n_win):
    wf = C.trim_wf(wf)
    cfg = dict(CFG0, waveform_I=wf[0::2], waveform_Q=wf[1::2], **cf)
    iq = np.asarray(ThrProg(soccfg, cfg).acquire_decimated(soc, progress=False))
    iq = iq.reshape(-1, iq.shape[-2], 2)
    m = np.asarray(soc.tproc.read_mem("dmem", length=3)).reshape(-1).astype(np.int64)
    on, pk = L.onset_interp(iq[1], n_win)      # read 1 = the capture around the conditional pulse
    full = dict(CFG0, **cf)
    t_dec = full["adc_trig_offset"] + C.live_len(full) + full["fb_margin"]
    t2 = round((t_dec + full["adc_trig_offset"] - full["cp_pre"]) / L.TICK) * L.TICK
    arr = (t2 - t_dec) + on / L.FS_RO
    w0 = iq[0]                                 # read 0 = the classified window itself, as the host sees it
    return dict(arr=arr, pk=pk, br=int(m[2]), i_early=int(np.int32(np.uint32(m[0]))), q_early=int(np.int32(np.uint32(m[1]))),
                s_i=float(np.sum(w0[:, 0])), s_q=float(np.sum(w0[:, 1])))


def freshness(rr):
    """The tProc's read is this shot's window sum if it tracks this shot's host-side sum better than the previous one's."""
    e = np.array([r["i_early"] for r in rr], float); s_ = np.array([r["s_i"] for r in rr], float)
    if np.std(s_) == 0:
        return np.zeros(len(rr), bool), np.nan
    g = np.polyfit(s_[1:], e[1:], 1)            # port value = gain * host sum + offset, if fresh
    fit_this = np.abs(e[1:] - np.polyval(g, s_[1:])); fit_prev = np.abs(e[1:] - np.polyval(g, s_[:-1]))
    f = np.concatenate([[False], fit_this < fit_prev])
    return f, float(np.corrcoef(s_[1:], e[1:])[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margins", default="-0.02,0,0.01,0.02,0.03,0.04,0.05,0.06,0.08,0.10,0.15,0.20,0.30")
    ap.add_argument("--trig-width", type=float, default=0.5)
    ap.add_argument("--skip-nn", action="store_true")
    ap.add_argument("--nn-margins", default="0.02,0.03,0.04,0.05,0.06,0.07,0.08")
    ap.add_argument("--shots", type=int, default=60)
    ap.add_argument("--n-force", type=int, default=20)
    ap.add_argument("--advance", type=float, default=0.1135)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    banner = str(soc.get_cfg().get("fw_timestamp", ""))
    print("BANNER:", banner, "| readout 0 -> tProc input", RO_IN, flush=True)
    assert T.BANNER in banner, banner
    k, c = C.calib.load_kc(strict=False)
    X_all = np.load("test20k_real_X.npy", mmap_mode="r")
    n = max(a.shots, a.n_force)
    X = np.asarray(X_all[2000:2000 + n])
    D = h.prepare_chunk(X, k, c) * (C.S.raw_peak(X, k, c) / C.S.raw_peak(X_all, k, c))
    WF = [h.prepare_waveform(d) for d in D]
    n_win = int(0.5 * 0.2 * L.FS_RO)
    out = dict(banner=banner, host=os.environ.get("QICK_NS_HOST"), ro_tproc_input=int(RO_IN), threshold={}, nn_tproc={})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)

    for path in ("fir", "box"):
        # stock readout 0 on the FIR path (sel=0) and with the boxcar selected (sel=1), if the select reaches readout 0
        print("readout path:", soc.box_config(sel=0) if path == "fir" else soc.box_config(sel=1, shift=7, m=11), flush=True)
        base = dict(cp_gain0=0.2, cp_gain1=0.6, cp_len=0.2, cp_pre=0.05, trig_width=a.trig_width, cp_slack=-0.2, nn_adv=0.0)
        # the threshold: median I of this path's window sums, read late (fresh by construction)
        probe = [thr_shot(WF[i], dict(base, fb_margin=0.3, fb_thr=0), n_win) for i in range(a.shots)]
        thr = int(np.median([p["i_early"] for p in probe]))
        fpr, rho = freshness(probe)
        print(f"  {path}: median I read {thr}; at margin 0.3 port vs host sum r = {rho:.4f}, fresh {int(fpr.sum())}/{a.shots - 1}", flush=True)
        pts = []
        for mg in (float(x) for x in a.margins.split(",")):
            cf = dict(base, fb_margin=mg)
            lv, Lf = {}, {}
            for want, t in ((0, 2**23 - 1), (1, -2**23)):  # tProc v2 immediates are 24-bit signed
                rr = [thr_shot(WF[i], dict(cf, fb_thr=t), n_win) for i in range(a.n_force)]
                lv[want] = float(np.mean([r["pk"] for r in rr])); Lf[want] = L.l_buf(cf, np.array([r["arr"] for r in rr]))
            mid = 0.5 * (lv[0] + lv[1])
            rr = [thr_shot(WF[i], dict(cf, fb_thr=thr), n_win) for i in range(a.shots)]
            Lb = L.l_buf(cf, np.array([r["arr"] for r in rr]))
            fresh, rho = freshness(rr)
            br = np.array([r["br"] for r in rr]); want = np.array([int(r["i_early"] >= thr) for r in rr])
            played = np.array([int(r["pk"] > mid) for r in rr])
            p = dict(margin=mg, n=a.shots, L_median=float(np.nanmedian(Lb)), L_min=float(np.nanmin(Lb)), L_max=float(np.nanmax(Lb)),
                     L_sd=float(np.nanstd(Lb)), L_forced0=float(np.nanmedian(Lf[0])), L_forced1=float(np.nanmedian(Lf[1])),
                     fresh=int(fresh.sum()), r_port_host=rho, br_ok=int((br == want).sum()), played_eq_br=int((played == br).sum()))
            pts.append(p)
            print(f"  thr/{path} margin {mg:+.3f}: L {p['L_median']:.1f} [{p['L_min']:.1f}, {p['L_max']:.1f}]  fresh {p['fresh']}/{a.shots}  "
                  f"br ok {p['br_ok']}  played==br {p['played_eq_br']}", flush=True)
            out["threshold"][path] = dict(thr=thr, points=pts)
            json.dump(out, open(a.out, "w"), indent=1)
        good = [p for p in pts if p["fresh"] == p["n"] - 1 and p["n"] == p["br_ok"] == p["played_eq_br"]]
        out["threshold"][path]["earliest_clean"] = good[0] if good else None
        print(f"  thr/{path}: earliest clean margin", f"{good[0]['margin']:+.3f}, L {good[0]['L_median']:.1f} ns" if good else "none", flush=True)
        json.dump(out, open(a.out, "w"), indent=1)

    if a.skip_nn:
        soc.box_config(sel=1, shift=7, m=11); print("THRESHOLD BASELINE DONE; boxcar path restored", flush=True); return
    # NN_live via the tProc on the boxcar path, same session (tproc_path_v143.py's "qick" variant)
    print("readout path:", soc.box_config(sel=1, shift=7, m=11), flush=True)
    base = dict(cp_gain0=0.2, cp_gain1=0.6, cp_len=0.2, cp_pre=0.05, trig_width=0.5, cp_slack=-0.2, nn_adv=a.advance)
    pts = []
    for mg in (float(x) for x in a.nn_margins.split(",")):
        cf = dict(base, variant="qick", fb_margin=mg)
        res = [T.shot(WF[i], dict(cf, fb_thr=16), n_win) for i in range(a.shots)]
        Lb = L.l_buf(cf, np.array([r[0] for r in res]))
        fresh = np.array([r[4] for r in res]); br = np.array([r[2] for r in res]); dec = np.array([r[3] for r in res])
        p = dict(margin=mg, n=a.shots, L_median=float(np.nanmedian(Lb)), L_min=float(np.nanmin(Lb)), L_max=float(np.nanmax(Lb)),
                 fresh=int(fresh.sum()), br_eq_dec=int((fresh & (br == dec)).sum()))
        pts.append(p)
        print(f"  nn/tproc margin {mg:+.3f}: L {p['L_median']:.1f}  fresh {p['fresh']}/{a.shots}  br==dec {p['br_eq_dec']}", flush=True)
    good = [p for p in pts if p["fresh"] == p["n"] == p["br_eq_dec"]]
    out["nn_tproc"] = dict(points=pts, earliest_clean=good[0] if good else None)
    json.dump(out, open(a.out, "w"), indent=1)
    soc.box_config(sel=1, shift=7, m=11)
    print("THRESHOLD BASELINE DONE; boxcar path restored", flush=True)


if __name__ == "__main__":
    main()
