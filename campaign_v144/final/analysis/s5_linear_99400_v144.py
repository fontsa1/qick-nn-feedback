"""The linear baselines scored on every replayed row of the NN_live campaign, not only the 19,400-row
NN_axi subset. Same training and recipes as linear_v144.py:
  MF and LDA (pooled covariance + ridge lam*tr(S)/d*I, lam 1e-2) from rows [0:200k) of 0528_X_train_0_770 through
  (k2, c2), threshold on the training scores; window-tradeoff LDA (rows [0:180k), ridge chosen on [180k:200k)) at
  E = 770, 640, 576.
Input: the QICK FIR readout buffer recorded with every NN_live shot (campaign_v144/final/live/<board>_run<r>_*.npz,
field 'fir', 770 complex samples), i.e. the same stream NN_axi reads. Each row is scored on the board and run it was
replayed in; rows 1000:1600 (the domain-map rows) are excluded, as everywhere.

Reported, each paired (exact McNemar) against NN_live's own decisions on the same shots:
  headline  run 1 of each board, half the split each (A rows 0-49,999, B rows 50,000-99,999): 99,400 rows
  A_all     board A, runs 1 and 2 (every row once): 99,400 rows; B_all likewise
Writes s5_linear_99400_v144.json.

  python campaign_v144/final/analysis/s5_linear_99400_v144.py
"""
import glob
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
sys.path.insert(0, str(ROOT / "analysis_scripts" / "analysis"))
import task33_three_way_comparison as T  # noqa: E402
from r3_stats import fstats, paired, calmask  # noqa: E402

CH = 10000
RIDGES_TRADE = (1e-4, 1e-3, 1e-2, 1e-1)


def fid(pred, y):
    return 100 * (1 - 0.5 * (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)))


def best_thr(s, y):
    o = np.sort(s); cand = o[::max(1, len(o) // 4000)]
    f = [fid((s > t).astype(int), y) for t in cand]
    return cand[int(np.argmax(f))]


t0 = time.time()
k2 = complex(np.load(ROOT / "calibration/k2_loopback.npy")); c2 = complex(np.load(ROOT / "calibration/c2_loopback.npy"))
Xm = np.load(ROOT / "0528_X_train_0_770.npy", mmap_mode="r")
y = np.load(ROOT / "0528_y_train_0_770.npy")[:200000].astype(int)
X = np.empty((200000, Xm.shape[1]), np.float32)
for i in range(0, 200000, CH):
    X[i:i + CH] = T.hw_raw_transform(T.apply_affine(np.asarray(Xm[i:i + CH]).astype(np.float32), k2, c2))
D = X.shape[1]
cum = {}
s1 = {0: np.zeros(D), 1: np.zeros(D)}; s2 = {0: np.zeros((D, D)), 1: np.zeros((D, D))}; nn = {0: 0, 1: 0}
for i in range(0, 200000, CH):
    A = X[i:i + CH].astype(np.float64); yy = y[i:i + CH]
    for c in (0, 1):
        Ac = A[yy == c]; s1[c] += Ac.sum(0); s2[c] += Ac.T @ Ac; nn[c] += len(Ac)
    if i + CH in (180000, 200000):
        cum[i + CH] = ({c: s1[c].copy() for c in (0, 1)}, {c: s2[c].copy() for c in (0, 1)}, dict(nn))
del s2
print(f"moments ({time.time() - t0:.0f}s)", flush=True)


def class_stats(N, d):
    S1, S2, n = cum[N]
    m = {c: S1[c][:d] / n[c] for c in (0, 1)}
    S = sum(S2[c][:d, :d] - n[c] * np.outer(m[c], m[c]) for c in (0, 1)) / (n[0] + n[1])
    return m[0], m[1], S


def scores(lo, hi, w):
    d = len(w)
    return np.concatenate([X[i:min(i + CH, hi), :d].astype(np.float64) @ w for i in range(lo, hi, CH)])


W = {}   # name -> (weights, threshold)
m0, m1, S = class_stats(200000, D)
w = m1 - m0
W["MF"] = (w, best_thr(scores(0, 200000, w), y))
wl = np.linalg.solve(S + 1e-2 * np.trace(S) / D * np.eye(D), w)
W["LDA_ridge0.01"] = (wl, best_thr(scores(0, 200000, wl), y))
for E in (770, 640, 576):
    d = 2 * E
    m0, m1, S = class_stats(180000, d)
    best = None
    for lam in RIDGES_TRADE:
        wl = np.linalg.solve(S + lam * np.trace(S) / d * np.eye(d), m1 - m0)
        t = best_thr(scores(0, 180000, wl), y[:180000])
        fv = fid((scores(180000, 200000, wl) > t).astype(int), y[180000:])
        if best is None or fv > best[0]:
            best = (fv, lam, wl, t)
    W[f"LDA_window{E}"] = (best[2], best[3])
    print(f"E={E}: ridge {best[1]:g} val {best[0]:.3f} ({time.time() - t0:.0f}s)", flush=True)
del X

# score every recorded shot
dec = {}
for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run*_*.npz"))):
    b, r = re.findall(r"([AB])_run(\d)_", Path(f).name)[0]
    z = np.load(f, allow_pickle=True)
    Xe = T.hw_raw_transform(z["fir"].astype(np.float64)).astype(np.float64)
    nnd = (z["live_rec"][:, 7] & 1).astype(int)
    d_ = dec.setdefault((b, r), {"rows": [], "y": [], "NN_live": [], **{k: [] for k in W}})
    d_["rows"].append(z["rows"]); d_["y"].append(z["y"]); d_["NN_live"].append(nnd)
    for k, (w_, t_) in W.items():
        d_[k].append((Xe[:, :len(w_)] @ w_ > t_).astype(int))
for v in dec.values():
    for k in v:
        v[k] = np.concatenate(v[k])
print("runs:", {f"{b}{r}": len(v["rows"]) for (b, r), v in dec.items()}, f"({time.time() - t0:.0f}s)", flush=True)


def sel(parts):
    """Concatenate (board, run, row filter) parts, then drop the map rows."""
    out = {}
    for b, r, keep in parts:
        v = dec[(b, r)]; m = keep(v["rows"])
        for k in v:
            out.setdefault(k, []).append(v[k][m])
    out = {k: np.concatenate(x) for k, x in out.items()}
    m = calmask(out["rows"])
    return {k: x[m] for k, x in out.items()}


SETS = {"headline": [("A", "1", lambda r: r < 50000), ("B", "1", lambda r: r >= 50000)],
        "A_all": [("A", "1", lambda r: r >= 0), ("A", "2", lambda r: r >= 0)],
        "B_all": [("B", "1", lambda r: r >= 0), ("B", "2", lambda r: r >= 0)]}
res = {"recipes": {"MF": "w = mu1 - mu0, 200k rows", "LDA_ridge0.01": "linear_baselines LDA, 200k rows, ridge 1e-2",
                   **{f"LDA_window{E}": f"window_tradeoff LDA, window [0, {E})" for E in (770, 640, 576)}}}
for name, parts in SETS.items():
    s = sel(parts)
    assert len(np.unique(s["rows"])) == len(s["rows"]), f"{name}: a row appears twice"
    yy = s["y"].astype(int)
    r = {"n": int(len(yy)), "NN_live": fstats(s["NN_live"], yy)}
    for k in W:
        r[k] = dict(fid=fstats(s[k], yy), vs_NN_live=paired(s[k], s["NN_live"], yy))
    res[name] = r
    print(name, r["n"], "NN_live", round(r["NN_live"]["fid"], 3), "  ".join(f"{k} {r[k]['fid']['fid']:.3f}" for k in W), flush=True)
(OUT / "s5_linear_99400_v144.json").write_text(json.dumps(res, indent=1, default=float))
print(f"done ({time.time() - t0:.0f}s)")
