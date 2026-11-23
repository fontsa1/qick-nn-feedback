"""What the boxcar readout path costs LDA, against QICK's FIR path, at NN_live's 576-sample window.

Question: P139 says the boxcar path "costs no fidelity" (true for NN_live) and P152 compares NN_live with an LDA core
on the boxcar path. How much of that LDA core's deficit is the path rather than the classifier?

Reads the per-shot LDA decisions of lda_99400.py (lda_99400_preds.npz beside this script; in DATA_MANIFEST.csv) and scores, on the same shots:
LDA boxcar-576 against LDA FIR-576, LDA FIR-576 against NN_live, for the headline mosaic and each board's full split.
F = 1 - (P(1|0) + P(0|1)) / 2; exact two-sided McNemar on the discordant shots.

    python campaign_v144/final/analysis/offline/lda_box_vs_fir.py   ->  lda_box_vs_fir.json beside it
"""
import json
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
d = np.load(HERE / "lda_99400_preds.npz")


def fid(pred, y):
    return 100 * (1 - (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)) / 2)


def mcnemar(a_ok, b_ok):
    b, c = int(np.sum(a_ok & ~b_ok)), int(np.sum(~a_ok & b_ok))
    n, k = b + c, min(b, c)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    return b, c, p


out = {}
for s in ("headline_mosaic", "A_full", "B_full"):
    y = d[f"{s}_y"]
    P = {k: d[f"{s}_{k}"].astype(int) for k in ("box576", "fir576", "fir770", "NN_live")}
    F = {k: fid(v, y) for k, v in P.items()}
    r = {"n": int(len(y)), "F": {k: round(v, 4) for k, v in F.items()}}
    for a, b in (("box576", "fir576"), ("fir576", "NN_live"), ("box576", "NN_live")):
        bo, co, p = mcnemar(P[a] == y, P[b] == y)
        r[f"{a}-{b}"] = {"dF": round(F[a] - F[b], 4), "a_only": bo, "b_only": co, "p_exact": p}
    out[s] = r
(HERE / "lda_box_vs_fir.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
