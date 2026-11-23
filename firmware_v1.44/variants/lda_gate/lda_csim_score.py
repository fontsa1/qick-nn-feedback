import os
"""Score the LDA_live csim output (every v1.44 NN_live capture, both boards, both runs) against the float LDA, the
bit-exact Python model and NN_live, on the paper's sets (map rows 1000:1600 excluded, as lda_99400.py).

  python firmware_v1.44/variants/lda_gate/lda_csim_score.py [tb_dir]
Writes lda_csim_score.json next to this script.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
from r3_stats import fstats, paired  # noqa: E402

TB = Path(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("QICK_WORK", "work"), "hls_lda/tb_data"))
ix = np.load(TB / "lda_index.npz")
raw = np.fromfile(TB / "lda_csim_out.bin", dtype=np.int32)
n = int(raw[0]); dec_c = raw[1:1 + n]; logit_c = raw[1 + n:1 + 2 * n]
assert n == len(ix["rows"]), "csim ran on a subset (LDA_N set?)"
z = np.load(HERE / "lda_weights.npz"); w = z["w"]; t = float(z["t"])

# float LDA on the exact gate windows (recomputed from the stored words)
W = np.fromfile(TB / "lda_words.bin", dtype=np.uint32)[1:].reshape(n, 576)
X = np.empty((n, 1152), np.float64)
X[:, 0::2] = (W & 0xFFFF).astype(np.uint16).view(np.int16); X[:, 1::2] = (W >> 16).astype(np.uint16).view(np.int16)
flt = (X @ w > t).astype(int); del X, W

res = dict(n_windows=n, csim_vs_python_model=dict(decision_mismatch=int((dec_c != ix["dec"]).sum()),
                                                  logit_mismatch=int((logit_c != ix["logit"]).sum())),
           csim_vs_float_all_windows=dict(flips=int((dec_c != flt).sum()), frac=float(np.mean(dec_c != flt))), sets={})
notmap = ~((ix["rows"] >= 1000) & (ix["rows"] < 1600))
sets = {
    "headline_mosaic": [("A", "run1", lambda r: r < 50000), ("B", "run1", lambda r: r >= 50000)],
    "A_full": [("A", "run1", lambda r: r >= 0), ("A", "run2", lambda r: r >= 0)],
    "B_full": [("B", "run1", lambda r: r >= 0), ("B", "run2", lambda r: r >= 0)],
}
for sn, parts in sets.items():
    m = np.zeros(n, bool)
    for b, ru, sel in parts:
        m |= (ix["board"] == b) & (ix["run"] == ru) & sel(ix["rows"]) & notmap
    y = ix["y"][m]
    r = dict(n=int(m.sum()), LDA_fixed_csim=fstats(dec_c[m], y), LDA_float=fstats(flt[m], y),
             NN_live=fstats(ix["nn_dec"][m], y), fixed_minus_float_pts=fstats(dec_c[m], y)["fid"] - fstats(flt[m], y)["fid"],
             fixed_vs_float=paired(dec_c[m], flt[m], y), NN_live_vs_LDA_fixed=paired(ix["nn_dec"][m], dec_c[m], y))
    res["sets"][sn] = r
    print(f"{sn:16s} n={r['n']}: LDA fixed (csim) {r['LDA_fixed_csim']['fid']:.3f}  float {r['LDA_float']['fid']:.3f}  "
          f"(fixed - float {r['fixed_minus_float_pts']:+.4f} pts, flips {int((dec_c[m] != flt[m]).sum())})  "
          f"NN_live {r['NN_live']['fid']:.3f}")
print("csim vs Python model:", res["csim_vs_python_model"], " csim vs float, all windows:", res["csim_vs_float_all_windows"])
(HERE / "lda_csim_score.json").write_text(json.dumps(res, indent=1, default=float))
