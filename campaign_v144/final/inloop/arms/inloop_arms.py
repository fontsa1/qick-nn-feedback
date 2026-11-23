"""Does the conditional pulse disturb the classification it follows, or later shots?

Same shot as audit_fixes/R18/inloop_campaign.py (imported, unchanged): NN_live decides, dac_gate passes or blanks the
conditional pulse on generator 0, the returning pulse is captured on the loopback ADC. Here every row is run under
several ARMS that differ only in the conditional pulse, interleaved block by block (arm order rotates per block) so slow
drift cannot masquerade as an arm effect:
  nominal  cp_gain1 = 0.6 (the campaign's value), gate enabled pass1/blank0
  zero     cp_gain1 = 0.0, gate enabled (the pulse path runs, nothing is played)
  max      cp_gain1 = 1.0, gate enabled
  gateoff  gate disabled (en = 0: no pulse can play), cp_gain1 = 0.6
The quantity compared is NN_live's own decision for the shot (its record), against the label and paired by row across
arms (exact McNemar). If the pulse (this shot's or an earlier one's) leaked into a readout window, the decision
fidelity would depend on the arm. Also recorded per shot: gate flags, pulse plateau, L_buf, NN_live record.

"""
import argparse, os, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R18"))
import inloop_campaign as IC  # noqa: E402  (connects to the board named by QICK_NS_HOST)

G, C, L, soc, soccfg, FS_RO = IC.G, IC.C, IC.L, IC.soc, IC.soccfg, IC.FS_RO
ARMS = {"nominal": (0.6, 1), "zero": (0.0, 1), "max": (1.0, 1), "gateoff": (0.6, 0)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=20000)
    ap.add_argument("--shots", type=int, default=15000)
    ap.add_argument("--block", type=int, default=250)
    ap.add_argument("--arms", default="nominal,zero,max,gateoff")
    ap.add_argument("--slack", type=float, default=-0.064)
    ap.add_argument("--margin", type=float, default=0.035)
    ap.add_argument("--pre", type=float, default=0.15)
    ap.add_argument("--nn-advance", type=float, default=0.1135)
    ap.add_argument("--rf-thr", type=int, default=2048)
    ap.add_argument("--x", default="test100k_real_X.npy")
    ap.add_argument("--y", default="test100k_real_y.npy")
    ap.add_argument("--scale-ref", default="test20k_real_X.npy")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = ROOT / a.out; out.parent.mkdir(parents=True, exist_ok=True)
    arms = a.arms.split(",")

    banner = IC.BC.firmware_banner(soc)["built"]
    print("host", os.environ.get("QICK_NS_HOST"), "| banner", banner, flush=True)
    print("boxcar path:", soc.box_config(sel=1, shift=7, m=11))
    k, c = C.calib.load_kc(strict=False)
    print(f"calibration |k| {abs(k):.5f} arg {np.degrees(np.angle(k)):.2f} deg")
    maxv = soccfg["gens"][0]["maxv"]
    Xall = np.load(ROOT / a.x, mmap_mode="r"); yall = np.load(ROOT / a.y).astype(int)
    wf = IC.waveforms(Xall, np.load(ROOT / a.scale_ref, mmap_mode="r"), k, c, maxv)
    n_win = max(4, int(0.5 * 0.2 * FS_RO))
    base = dict(cp_gain0=0.0, cp_gain1=0.6, cp_len=0.2, cp_pre=a.pre, trig_width=0.5, fb_margin=a.margin,
                fb_thr=16, win_extra=0.05, nn_adv=a.nn_advance, split=True)

    # gate calibration exactly as inloop_campaign.py (domain-map rows, never scored)
    soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=1, pass_stale=1))
    mp, plats = [], []
    for r in IC.CAL_ROWS:
        res = IC.shot(wf(r)[0], dict(base, cp_slack=0.0), n_win)
        mp.append(int(res["gate"][7])); plats.append(res["plat"])
    if int(soc.gate_stats()[11]) != G.GAT4:
        raise SystemExit("gate magic is not GAT4")
    delay = min(mp) - G.DELAY_LEAD
    plat_pass = float(np.median(plats))
    print(f"marker -> pulse {sorted(set(mp))} cycles, DELAY {delay}; plateau {plat_pass:.0f}", flush=True)
    seg_thr = G.seg_threshold([wf(r)[0] for r in IC.CAL_ROWS[:4]], dict(base, cp_slack=0.0))
    soc.seg_write(1, seg_thr); soc.seg_write(4, a.rf_thr)

    rows = np.arange(a.start, a.start + a.shots)
    rows = rows[~np.isin(rows, np.arange(1000, 1600))]
    keys = ("gate", "plat", "rec", "fresh", "dec", "L_buf", "late", "n_clip", "t", "order")
    acc = {arm: {k_: [] for k_ in keys} for arm in arms}
    done_blocks = 0
    if out.exists():
        z = np.load(out, allow_pickle=True)
        assert int(z["start"]) == a.start and list(z["arms"]) == arms and int(z["block"]) == a.block
        done_blocks = int(z["done_blocks"])
        n = done_blocks * a.block
        for arm in arms:
            for k_ in keys:
                acc[arm][k_] = list(z[f"{arm}__{k_}"][:n])
        print(f"resuming after {done_blocks} blocks", flush=True)

    def save(nb):
        d = dict(start=a.start, rows=rows, y=yall[rows], arms=np.array(arms), block=a.block, done_blocks=nb, slack=a.slack,
                 margin=a.margin, pre=a.pre, nn_adv=a.nn_advance, delay=delay, plat_pass=plat_pass, banner=banner,
                 host=os.environ.get("QICK_NS_HOST"), k=k, c=c, arm_def=str(ARMS))
        for arm in arms:
            for k_ in keys:
                d[f"{arm}__{k_}"] = np.array(acc[arm][k_])
        tmp = out.with_suffix(".tmp.npz"); np.savez(tmp, **d); os.replace(tmp, out)

    nblocks = int(np.ceil(len(rows) / a.block))
    late_prev = int(soc.gate_stats()[12])
    t0 = time.time(); shots0 = 0
    try:
        for b in range(done_blocks, nblocks):
            br = rows[b * a.block:(b + 1) * a.block]
            order = arms[b % len(arms):] + arms[:b % len(arms)]
            for pos, arm in enumerate(order):
                gain1, en = ARMS[arm]
                if en:
                    soc.gate_write(0, G.cfg_word(en=1, pass1=1, pass0=0, pass_stale=0, delay=delay))
                else:
                    soc.gate_write(0, G.cfg_word(en=0, delay=delay))
                for r in br:
                    w, n_clip = wf(r)
                    res = IC.shot(w, dict(base, cp_gain1=gain1, cp_slack=a.slack), n_win)
                    late_now = int(res["gate"][12]); res["late"] = late_now - late_prev; late_prev = late_now
                    res["n_clip"] = n_clip; res["t"] = time.time(); res["order"] = pos
                    for k_ in keys:
                        acc[arm][k_].append(res[k_])
                    shots0 += 1
            save(b + 1)
            y = yall[rows[:(b + 1) * a.block]][:len(acc[arms[0]]["dec"])]
            msg = "  ".join(f"{arm} {IC.fid(np.array(acc[arm]['dec']), y)[0]:.2f}" for arm in arms)
            print(f"block {b + 1}/{nblocks}  {shots0 / (time.time() - t0):.2f} shots/s  NN_live decision F: {msg}", flush=True)
    finally:
        soc.gate_write(0, G.cfg_word(en=0, delay=delay))
        print("gate left disabled", flush=True)
    print("ARMS DONE", flush=True)

if __name__ == "__main__":
    main()
