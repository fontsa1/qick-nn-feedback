"""The loop on QICK's stock FIR readout path, against the boxcar path, same session.

For each readout path the conditional pulse's slack is swept through the late cliff with the gate passing every fresh
decision (PASS1 = PASS0 = 1, stale blanks), so a shot with no returning pulse is a late decision. Per slack: shots played,
the gate's late counter, and L_buf (window's last sample -> pulse 50% point at readout 0, the in-loop campaign's per-shot
number). The earliest slack with every shot played is each path's operating limit; the difference of L_buf there is
what the boxcar path saves in the whole loop (Fig. 7 measured the stream-level saving, 108.0 ns).
  box  NN_live on the boxcar stream (sel = 1, nn_adv = 0.1135 us): the deployed configuration
  fir  NN_live on the stock FIR stream (sel = 0, nn_adv = 0): the stock path. NN_live was trained on the boxcar stream, so
       on this path only timing is meaningful (as in tproc_path_v143.py)

"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R18"))
import inloop_campaign as IC  # noqa: E402

G, C, L, soc, soccfg, FS_RO = IC.G, IC.C, IC.L, IC.soc, IC.soccfg, IC.FS_RO
PATHS = {"box": (dict(sel=1, shift=7, m=11), 0.1135), "fir": (dict(sel=0), 0.0)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=40)
    ap.add_argument("--box-slacks", default=",".join(f"{x:.3f}" for x in np.arange(-0.090, -0.0399, 0.002)))
    ap.add_argument("--fir-slacks", default=",".join(f"{x:.3f}" for x in np.arange(-0.140, 0.0601, 0.004)))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    banner = IC.BC.firmware_banner(soc)["built"]
    print("host", os.environ.get("QICK_NS_HOST"), "| banner", banner, flush=True)
    k, c = C.calib.load_kc(strict=False)
    maxv = soccfg["gens"][0]["maxv"]
    Xall = np.load(ROOT / "test100k_real_X.npy", mmap_mode="r")
    wf = IC.waveforms(Xall, np.load(ROOT / "test20k_real_X.npy", mmap_mode="r"), k, c, maxv)
    n_win = max(4, int(0.5 * 0.2 * FS_RO))
    rows = np.arange(41000, 41000 + a.shots)
    W = [wf(r)[0] for r in rows]
    out = dict(banner=banner, host=os.environ.get("QICK_NS_HOST"), shots=a.shots, rows=[int(rows[0]), int(rows[-1])], paths={})
    try:
        for path, (sel, adv) in PATHS.items():
            soc.box_config(**sel)
            base = dict(cp_gain0=0.6, cp_gain1=0.6, cp_len=0.2, cp_pre=0.15, trig_width=0.5, fb_margin=0.035,
                        fb_thr=16, win_extra=0.05, nn_adv=adv, split=True)
            soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=1, pass_stale=1))
            mp, plats = [], []
            for r in IC.CAL_ROWS:
                res = IC.shot(wf(r)[0], dict(base, cp_slack=0.0), n_win)
                mp.append(int(res["gate"][7])); plats.append(res["plat"])
            delay = min(mp) - G.DELAY_LEAD; plat_pass = float(np.median(plats))
            soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=1, pass_stale=0, delay=delay))
            slacks = [float(x) for x in (a.box_slacks if path == "box" else a.fir_slacks).split(",")]
            pts = []
            for sl in slacks:
                g0 = int(soc.gate_stats()[12])
                rr = [IC.shot(w, dict(base, cp_slack=sl), n_win) for w in W]
                played = np.array([r["plat"] > 0.5 * plat_pass for r in rr])
                lb = np.array([r["L_buf"] for r in rr])
                p = dict(slack_ns=round(1e3 * sl, 1), played=int(played.sum()), late=int(soc.gate_stats()[12]) - g0,
                         L_buf_median=float(np.nanmedian(lb[played])) if played.any() else None,
                         L_buf_sd=float(np.nanstd(lb[played])) if played.any() else None)
                pts.append(p)
                print(f"{path} slack {p['slack_ns']:+7.1f} ns: played {p['played']}/{a.shots}  late {p['late']}  "
                      f"L_buf {p['L_buf_median']}", flush=True)
            clean = [p for p in pts if p["played"] == a.shots]
            out["paths"][path] = dict(nn_adv=adv, delay=delay, plat_pass=plat_pass, points=pts,
                                      earliest_clean=min(clean, key=lambda p: p["slack_ns"]) if clean else None)
            json.dump(out, open(a.out, "w"), indent=1)
            print(f"{path}: earliest clean slack {out['paths'][path]['earliest_clean']}", flush=True)
    finally:
        soc.gate_write(0, G.cfg_word(en=0))
        soc.box_config(sel=1, shift=7, m=11)
    b, f = out["paths"].get("box", {}).get("earliest_clean"), out["paths"].get("fir", {}).get("earliest_clean")
    if b and f:
        out["fir_minus_box_L_buf_ns"] = f["L_buf_median"] - b["L_buf_median"]
    json.dump(out, open(a.out, "w"), indent=1)
    print("PATHS DONE; FIR - box L_buf at each path's limit:", out.get("fir_minus_box_L_buf_ns"), flush=True)

if __name__ == "__main__":
    main()
