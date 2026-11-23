"""Pulse-gain arms on the full split (nominal 0.6 / zero 0.0 conditional-pulse amplitude): NN_live decision fidelity per arm,
exact McNemar between arms, and against the gate-idle v1.44 final/ captures of the same rows (run1 and run2).
  """
import glob, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
from r3_stats import fstats, paired  # noqa: E402
out = {}
for b in sys.argv[1:]:
    z = np.load(ROOT / f"campaign_v144/final/inloop/arms/{b}_arms_full.npz")
    y = z["y"].astype(int); rows = z["rows"]; arms = list(z["arms"])
    r = dict(host=str(z["host"]), banner=str(z["banner"]), n=int(len(y)), rows=[int(rows.min()), int(rows.max())], arm_def=str(z["arm_def"]), arms={})
    dec = {a: z[f"{a}__dec"].astype(int) for a in arms}
    for a in arms:
        rec_dec = (z[f"{a}__rec"][:, 7] & 1).astype(int)
        fr = z[f"{a}__fresh"]
        r["arms"][a] = dict(all=fstats(dec[a], y), fresh_frac=float(fr.mean()), fresh_only=fstats(dec[a][fr], y[fr]),
                            dec_eq_rec=int(np.sum(dec[a] == rec_dec)), late=int(np.sum(z[f"{a}__late"] > 0)),
                            L_buf_med=float(np.nanmedian(z[f"{a}__L_buf"])), n_clip=int(np.sum(z[f"{a}__n_clip"] > 0)))
    r["paired_vs_nominal"] = {a: paired(dec[a], dec["nominal"], y) for a in arms if a != "nominal"}
    # same rows, gate-idle v1.44 final/ captures
    for run in (1, 2):
        m = {}
        for f in glob.glob(str(ROOT / f"campaign_v144/final/live/{b}_run{run}_*.npz")):
            q = np.load(f)
            for rw, d in zip(q["rows"], q["live_rec"][:, 7] & 1): m[int(rw)] = int(d)
        have = np.array([int(rw) in m for rw in rows])
        if have.sum() == 0: continue
        fd = np.array([m[int(rw)] for rw in rows[have]])
        r[f"final_run{run}"] = dict(n=int(have.sum()), fid=fstats(fd, y[have]),
                                   paired={a: paired(dec[a][have], fd, y[have]) for a in arms})
    out[b] = r
    print(b, r["host"], r["banner"], "n", r["n"], "rows", r["rows"])
    for a in arms:
        s = r["arms"][a]; print(f"  {a:8s} F {s['all']['fid']:.3f}  fresh {s['fresh_frac']:.4f} (F {s['fresh_only']['fid']:.3f})  dec==rec {s['dec_eq_rec']}  late {s['late']}  L_buf med {s['L_buf_med']:.2f}  clip {s['n_clip']}")
    for k in ("paired_vs_nominal",):
        for a, p in r[k].items(): print(f"  {k} {a}: {p}")
    for run in (1, 2):
        if f"final_run{run}" in r:
            fr = r[f"final_run{run}"]; print(f"  final run{run} same rows n {fr['n']} F {fr['fid']['fid']:.3f}")
            for a, p in fr["paired"].items(): print(f"    {a} vs final run{run}: {p}")
(ROOT / "campaign_v144/final/inloop/arms/arms_full_analysis.json").write_text(json.dumps(out, indent=1, default=float))
