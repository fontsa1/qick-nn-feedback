"""After the build-2 board run: check LDA_live on hardware bit for bit, and score it.

For every box_live_capture.py chunk (*.npz with live_words, live_rec, live_hdr, y, rows) under the given folder(s):
  * recompute D, logit and decision from the captured window words with lda_model.py and compare with the on-chip
    record (word 1/2 = D, word 5 = logit, word 7 = decision) and with the header (word 2 "NNL1", word 3 "LDA1" is not
    stored by box_live_capture, so the hwh/banner identifies the build);
  * fidelity per board and run, the paper's sets (headline mosaic = run 1 of A rows <50k and of B rows >=50k; map rows
    1000:1600 excluded), and the paired difference against the v1.44 NN_live decisions on the same rows
    (campaign_v144/final/live) and against the offline float LDA (lda_quant_preds.npz).
"""
import glob, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
import lda_model as M  # noqa: E402
from r3_stats import fstats, paired  # noqa: E402

D_IN = Path(sys.argv[1])
consts = M.load_consts()
S, bad = {}, dict(D=0, logit=0, dec=0, n=0)
for f in sorted(glob.glob(str(D_IN / "*_run*_*.npz"))):
    nm = Path(f).stem.split("_"); z = np.load(f)
    Dm, dec, logit = M.lda_live(z["live_words"], consts)
    rec = z["live_rec"].astype(np.int64)
    Dchip = (rec[:, 1] & 0xFFFFFFFF) | ((rec[:, 2] & 0xFFFFFFFF) << 32)   # int64: the shift wraps to the signed value
    lchip = rec[:, 5] & 0xFFFF; lchip = np.where(lchip >= 32768, lchip - 65536, lchip)
    bad["D"] += int((Dchip != Dm).sum()); bad["logit"] += int((lchip != logit).sum()); bad["dec"] += int(((rec[:, 7] & 1) != dec).sum())
    bad["n"] += len(dec)
    k = (nm[0], nm[1]); S.setdefault(k, dict(rows=[], y=[], dec=[]))
    S[k]["rows"].append(z["rows"]); S[k]["y"].append(z["y"]); S[k]["dec"].append(rec[:, 7] & 1)
S = {k: {kk: np.concatenate(v) for kk, v in d.items()} for k, d in S.items()}

# v1.44 NN_live on the same rows (gate idle campaign) and the offline float LDA
nn = {}
for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run*_*.npz"))):
    nm = Path(f).stem.split("_"); z = np.load(f)
    for r, d in zip(z["rows"], z["live_rec"][:, 7] & 1):
        nn[(nm[0], nm[1], int(r))] = int(d)
res = dict(bit_exact_vs_lda_model=bad, sets={})
sets = {"headline_mosaic": [("A", "run1", lambda r: r < 50000), ("B", "run1", lambda r: r >= 50000)],
        "A_full": [("A", "run1", lambda r: r >= 0), ("A", "run2", lambda r: r >= 0)],
        "B_full": [("B", "run1", lambda r: r >= 0), ("B", "run2", lambda r: r >= 0)]}
for sn, parts in sets.items():
    rows, y, dec, nnd = [], [], [], []
    for b, ru, sel in parts:
        if (b, ru) not in S:
            continue
        d = S[(b, ru)]; m = sel(d["rows"]) & ~((d["rows"] >= 1000) & (d["rows"] < 1600))
        rows.append(d["rows"][m]); y.append(d["y"][m]); dec.append(d["dec"][m])
        nnd.append(np.array([nn.get((b, ru, int(r)), -1) for r in d["rows"][m]]))
    if not rows:
        continue
    rows, y, dec, nnd = map(np.concatenate, (rows, y, dec, nnd))
    r = dict(n=int(len(y)), LDA_live_board=fstats(dec, y))
    ok = nnd >= 0
    if ok.any():
        r["NN_live_v144_same_rows"] = fstats(nnd[ok], y[ok]); r["NN_live_vs_LDA_live"] = paired(nnd[ok], dec[ok], y[ok])
    res["sets"][sn] = r
    print(f"{sn}: n={r['n']} LDA_live (board) {r['LDA_live_board']['fid']:.3f}"
          + (f"  NN_live v1.44 {r['NN_live_v144_same_rows']['fid']:.3f}" if ok.any() else ""))
print("bit-exact vs lda_model:", bad)
(D_IN / "check_board_lda.json").write_text(json.dumps(res, indent=1, default=float))
