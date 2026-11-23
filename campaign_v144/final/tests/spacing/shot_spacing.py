"""The minimum spacing between classified windows the loop tolerates.

The in-loop shot of audit_fixes/R18/inloop_campaign.py (GateProg: trace, NN_live window, gate window, conditional pulse,
capture) is repeated REPS times inside ONE tProc program (QICK reps, final_delay = the idle time between repetitions),
for a list of final_delay values. Two traces: one NN_live classifies 1 with a large margin (the pulse must play every
repetition) and one it classifies 0 (it must never play). Per spacing:
  records    NN_live's record count advances by exactly REPS; frame errors do not change; shot numbers are consecutive
  decisions  every repetition's decision equals the single-shot decision of the same trace
  loop       pulse played on every repetition for the "1" trace and on none for the "0" trace; the gate's late counter and
             binding rejects do not change
The shot period is the program body (window, decision, pulse, capture) plus final_delay; both are reported.

"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R18"))
import inloop_campaign as IC  # noqa: E402

G, C, L, soc, soccfg, FS_RO, CFG0 = IC.G, IC.C, IC.L, IC.soc, IC.soccfg, IC.FS_RO, IC.CFG0

def run(w, cf, reps, fd, n_win):
    w = C.trim_wf(w)
    cfg = dict(CFG0, waveform_I=w[0::2], waveform_Q=w[1::2], **cf)
    cfg["reps"], cfg["final_delay"] = reps, fd
    h0 = np.array(soc.live_read_block(0, 3), np.int64); g0 = np.array(soc.gate_stats(), np.int64)
    iq = np.asarray(G.GateProg(soccfg, cfg).acquire_decimated(soc, progress=False))
    h1 = np.array(soc.live_read_block(0, 3), np.int64); g1 = np.array(soc.gate_stats(), np.int64)
    caps = iq.reshape(-1, iq.shape[-2], 2)
    pulse_caps = caps[1::2] if len(caps) == 2 * reps else caps[-reps:]
    plats = np.array([L.onset_interp(cp, n_win)[1] for cp in pulse_caps])
    n_new = int(h1[0] - h0[0])
    recs = [C.live_record(n) for n in range(int(h0[0]) + 1, int(h1[0]) + 1)][-min(n_new, C.REC_N):] if n_new > 0 else []
    shots = np.array([r[0] for r in recs]); decs = np.array([int(r[7] & 1) for r in recs])
    return dict(n_new=n_new, frame_err=int(h1[1] - h0[1]), consecutive=bool(len(shots) and np.all(np.diff(shots) == 1)),
                decs=decs, plats=plats, late=int(g1[12] - g0[12]), rejects=int(g1[19] - g0[19]), n_caps=len(caps))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delays", default="50,20,10,5,3,2,1.5,1,0.75,0.5,0.4,0.3,0.2,0.15,0.1,0.05,0.02,0")
    ap.add_argument("--reps", type=int, default=14)  # 14 x 2 trigs x 576 samples fits the 16,384-sample decimated buffer
    ap.add_argument("--slack", type=float, default=-0.064)
    ap.add_argument("--margin", type=float, default=0.035)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    banner = IC.BC.firmware_banner(soc)["built"]
    print("host", os.environ.get("QICK_NS_HOST"), "| banner", banner, flush=True)
    soc.box_config(sel=1, shift=7, m=11)
    k, c = C.calib.load_kc(strict=False)
    maxv = soccfg["gens"][0]["maxv"]
    Xall = np.load(ROOT / "test100k_real_X.npy", mmap_mode="r"); yall = np.load(ROOT / "test100k_real_y.npy").astype(int)
    wf = IC.waveforms(Xall, np.load(ROOT / "test20k_real_X.npy", mmap_mode="r"), k, c, maxv)
    n_win = max(4, int(0.5 * 0.2 * FS_RO))
    base = dict(cp_gain0=0.0, cp_gain1=0.6, cp_len=0.2, cp_pre=0.15, trig_width=0.5, fb_margin=a.margin,
                fb_thr=16, win_extra=0.05, nn_adv=0.1135, split=True, cp_slack=a.slack)
    # gate calibration as inloop_campaign.py
    soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=1, pass_stale=1))
    mp, plats = [], []
    for r in IC.CAL_ROWS:
        res = IC.shot(wf(r)[0], dict(base, cp_slack=0.0), n_win)
        mp.append(int(res["gate"][7])); plats.append(res["plat"])
    delay = min(mp) - G.DELAY_LEAD; plat_pass = float(np.median(plats))
    soc.seg_write(1, G.seg_threshold([wf(r)[0] for r in IC.CAL_ROWS[:4]], dict(base, cp_slack=0.0))); soc.seg_write(4, 2048)
    soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=0, pass_stale=0, delay=delay))
    # pick a clear-1 and a clear-0 trace by NN_live's own logit (rows outside every scored region of this study)
    pick = {}
    for r in range(40000, 40400):
        res = IC.shot(wf(r)[0], base, n_win)
        lg = int(np.int16(res["rec"][5] & 0xFFFF))
        if res["dec"] == 1 and lg > 3000 and 1 not in pick:
            pick[1] = (r, lg)
        if res["dec"] == 0 and lg < -3000 and 0 not in pick:
            pick[0] = (r, lg)
        if len(pick) == 2:
            break
    print("traces:", pick, "| plateau", plat_pass, "| DELAY", delay, flush=True)
    full = dict(CFG0, **base)
    t_dec = full["adc_trig_offset"] - full["nn_adv"] + C.live_len(full) + full["fb_margin"]
    body = t_dec + base["cp_slack"] + base["cp_len"] + 0.1
    out = dict(banner=banner, host=os.environ.get("QICK_NS_HOST"), reps=a.reps, body_us=body, traces={str(k_): v for k_, v in pick.items()},
               plat_pass=plat_pass, points=[])
    try:
        for fd in (float(x) for x in a.delays.split(",")):
            p = dict(final_delay_us=fd, period_us_nominal=body + fd)
            for want, (row, _) in pick.items():
                try:
                    r = run(wf(row)[0], base, a.reps, fd, n_win)
                except Exception as e:  # a spacing the program or the firmware refuses is a result too
                    p[f"t{want}"] = dict(error=f"{type(e).__name__}: {e}"); continue
                played = r["plats"] > 0.5 * plat_pass
                p[f"t{want}"] = dict(n_new=r["n_new"], frame_err=r["frame_err"], consecutive=r["consecutive"],
                                    dec_ok=int(np.sum(r["decs"] == want)), n_dec=int(len(r["decs"])),
                                    played=int(played.sum()), n_caps=r["n_caps"], late=r["late"], rejects=r["rejects"])
            ok = all(isinstance(p.get(f"t{w}"), dict) and "error" not in p[f"t{w}"] and p[f"t{w}"]["n_new"] == a.reps
                     and p[f"t{w}"]["frame_err"] == 0 and p[f"t{w}"]["dec_ok"] == a.reps and p[f"t{w}"]["late"] == 0
                     and p[f"t{w}"]["rejects"] == 0 and p[f"t{w}"]["played"] == (a.reps if w == 1 else 0) for w in (0, 1))
            p["clean"] = bool(ok)
            out["points"].append(p)
            print(f"final_delay {fd:6.2f} us (period ~{body + fd:.2f} us): {'CLEAN' if ok else 'NOT CLEAN'}  "
                  f"t1 {p.get('t1')}  t0 {p.get('t0')}", flush=True)
            json.dump(out, open(a.out, "w"), indent=1, default=int)
    finally:
        soc.gate_write(0, G.cfg_word(en=0, delay=delay))
    clean = [p["final_delay_us"] for p in out["points"] if p["clean"]]
    out["min_clean_final_delay_us"] = min(clean) if clean else None
    json.dump(out, open(a.out, "w"), indent=1, default=int)
    print("SPACING DONE; smallest clean final_delay:", out["min_clean_final_delay_us"], "us; body", round(body, 3), "us", flush=True)

if __name__ == "__main__":
    main()
