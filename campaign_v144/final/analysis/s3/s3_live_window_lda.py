"""S3: what a live readout would see with the deployed window. Replay plays the recorded traces
1.80x fast (3.25 ns recorded, 1.808 ns replayed per sample), so the deployed 576-sample window covers 1.87 us of recorded
readout but only 1.04 us of a live one at this decimation, i.e. the first 320 recorded samples.

Offline, raw traces, no hardware: LDA (window_tradeoff.py's recipe: pooled covariance + ridge lam*tr(S)/d*I, rows
[0:180k) of 0528_X_train_0_770, ridge chosen on rows [180k:200k), threshold on the training scores) on the window
[0, E) of recorded samples, scored on the 100,000-row test split (test100k_real_X). E sweeps from 160 recorded samples
(0.52 us) to the full 770 (2.50 us). The row for E = 320 is the deployed window on a live readout; E = 576 is the
deployed window as replayed here.

Writes s3_live_window_lda.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
from r3_stats import fstats, paired  # noqa: E402

GRID = (160, 192, 224, 256, 288, 320, 352, 384, 448, 512, 576, 640, 704, 770)
RIDGES = (1e-4, 1e-3, 1e-2, 1e-1)
CH, NTR, NALL = 10000, 180000, 200000

def fid(pred, y):
    return 100 * (1 - 0.5 * (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)))

def best_thr(s, y):
    o = np.sort(s); cand = o[::max(1, len(o) // 4000)]
    return cand[int(np.argmax([fid((s > t).astype(int), y) for t in cand]))]

t0 = time.time()
Xm = np.load(ROOT / "0528_X_train_0_770.npy", mmap_mode="r")
y = np.load(ROOT / "0528_y_train_0_770.npy")[:NALL].astype(int)
X = np.empty((NALL, Xm.shape[1]), np.float32)
for i in range(0, NALL, CH):
    X[i:i + CH] = np.asarray(Xm[i:i + CH], dtype=np.float32)
Xt = np.load(ROOT / "test100k_real_X.npy", mmap_mode="r")
yt = np.load(ROOT / "test100k_real_y.npy").astype(int)
D = X.shape[1]
s1 = {0: np.zeros(D), 1: np.zeros(D)}; s2 = {0: np.zeros((D, D)), 1: np.zeros((D, D))}; nn = {0: 0, 1: 0}
for i in range(0, NTR, CH):
    A = X[i:i + CH].astype(np.float64); yy = y[i:i + CH]
    for c in (0, 1):
        Ac = A[yy == c]; s1[c] += Ac.sum(0); s2[c] += Ac.T @ Ac; nn[c] += len(Ac)
print(f"moments ({time.time() - t0:.0f}s)", flush=True)

def scores(Z, lo, hi, w):
    d = len(w)
    return np.concatenate([np.asarray(Z[i:min(i + CH, hi), :d], dtype=np.float64) @ w for i in range(lo, hi, CH)])

res = {"grid_recorded_samples": GRID, "ns_per_recorded_sample": 3.25, "points": {}}
P = {}
for E in GRID:
    d = 2 * E
    m = {c: s1[c][:d] / nn[c] for c in (0, 1)}
    S = sum(s2[c][:d, :d] - nn[c] * np.outer(m[c], m[c]) for c in (0, 1)) / (nn[0] + nn[1])
    best = None
    for lam in RIDGES:
        w = np.linalg.solve(S + lam * np.trace(S) / d * np.eye(d), m[1] - m[0])
        t = best_thr(scores(X, 0, NTR, w), y[:NTR])
        fv = fid((scores(X, NTR, NALL, w) > t).astype(int), y[NTR:])
        if best is None or fv > best[0]:
            best = (fv, lam, w, t)
    fv, lam, w, t = best
    P[E] = (scores(Xt, 0, len(yt), w) > t).astype(int)
    res["points"][str(E)] = dict(qubit_time_us=round(E * 3.25e-3, 4), ridge=lam, val_fid=fv, test=fstats(P[E], yt))
    print(f"E={E} ({E * 3.25e-3:.2f} us): ridge {lam:g} val {fv:.3f} test {res['points'][str(E)]['test']['fid']:.3f} "
          f"({time.time() - t0:.0f}s)", flush=True)
for E in GRID:
    res["points"][str(E)]["vs576"] = paired(P[E], P[576], yt)
(OUT / "s3_live_window_lda.json").write_text(json.dumps(res, indent=1, default=float))
print(f"done ({time.time() - t0:.0f}s)")
