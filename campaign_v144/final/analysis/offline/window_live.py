"""What a live-length window costs.

The replay plays the 3.25 ns recorded samples at the 1.808 ns readout rate (x1.80 time compression), so NN_live's
576-sample window carries 576 recorded samples = 1.87 us of readout. On a live resonator at the same decimation, 576
samples are 1.04 us of readout, i.e. the information of ~320 recorded samples (576 * 1.808 / 3.25 = 320.4).
This script measures the fidelity cost of that shorter window with the paper's LDA recipe (window_tradeoff arm, ridge
chosen on validation rows, window = the first E complex samples), for E on a grid that reaches below the swept range of
Fig. 5 (384..770):
  raw     trained on raw training rows, scored on the raw (recorded, not replayed) test rows: what a live system with no
          replay channel would see, at the recorded sample spacing
  replay  trained through (k2, c2) as linear_v144.py, scored on the FIR stream of the v1.44 replays (headline mosaic,
          99,400 shots): the replay apparatus at each window
Same rows for every E, so the E-to-E differences are paired (exact McNemar against E = 576 and E = 320).

"""
import glob, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2")); sys.path.insert(0, str(ROOT / "analysis_scripts" / "analysis"))
import task33_three_way_comparison as T  # noqa: E402
from r3_stats import fstats, paired  # noqa: E402

GRID = (192, 224, 256, 288, 320, 352, 384, 448, 512, 576, 640, 770)
CH, NTR, RIDGES = 10000, 180000, (1e-4, 1e-3, 1e-2, 1e-1)
t0 = time.time()

def fid(p, y):
    return 100 * (1 - 0.5 * (np.mean(p[y == 0] != 0) + np.mean(p[y == 1] != 1)))

def best_thr(s, y):
    o = np.sort(s); cand = o[::max(1, len(o) // 4000)]
    return cand[int(np.argmax([fid((s > t).astype(int), y) for t in cand]))]

def moments(X, y):
    D = X.shape[1]; s1 = {0: np.zeros(D), 1: np.zeros(D)}; s2 = {0: np.zeros((D, D)), 1: np.zeros((D, D))}; n = {0: 0, 1: 0}
    for i in range(0, NTR, CH):
        A = X[i:i + CH].astype(np.float64); yy = y[i:i + CH]
        for c in (0, 1):
            Ac = A[yy == c]; s1[c] += Ac.sum(0); s2[c] += Ac.T @ Ac; n[c] += len(Ac)
    return s1, s2, n

def lda_for(X, y, mom, E):
    s1, s2, n = mom; d = 2 * E
    m = {c: s1[c][:d] / n[c] for c in (0, 1)}
    S = sum(s2[c][:d, :d] - n[c] * np.outer(m[c], m[c]) for c in (0, 1)) / (n[0] + n[1])
    sc = lambda lo, hi, w: np.concatenate([X[i:min(i + CH, hi), :d].astype(np.float64) @ w for i in range(lo, hi, CH)])
    best = None
    for lam in RIDGES:
        w = np.linalg.solve(S + lam * np.trace(S) / d * np.eye(d), m[1] - m[0])
        t = best_thr(sc(0, NTR, w), y[:NTR]); fv = fid((sc(NTR, 200000, w) > t).astype(int), y[NTR:200000])
        if best is None or fv > best[0]:
            best = (fv, lam, w, t)
    return best

Xm = np.load(ROOT / "0528_X_train_0_770.npy", mmap_mode="r"); ytr = np.load(ROOT / "0528_y_train_0_770.npy")[:200000].astype(int)
y100 = np.load(ROOT / "test100k_real_y.npy").astype(int)
X100 = np.load(ROOT / "test100k_real_X.npy", mmap_mode="r")
rows_h = np.arange(100000); rows_h = rows_h[~((rows_h >= 1000) & (rows_h < 1600))]

# replay evaluation set: the headline mosaic's FIR stream
fir, rows_r, y_r = [], [], []
for b, cond in (("A", lambda r: r < 50000), ("B", lambda r: r >= 50000)):
    for f in sorted(glob.glob(str(ROOT / f"campaign_v144/final/live/{b}_run1_*.npz"))):
        z = np.load(f); m = cond(z["rows"]) & ~((z["rows"] >= 1000) & (z["rows"] < 1600))
        fir.append(z["fir"][m]); rows_r.append(z["rows"][m]); y_r.append(z["y"][m])
fir = np.concatenate(fir); rows_r = np.concatenate(rows_r); y_r = np.concatenate(y_r)
print(f"replay set {len(rows_r)} shots ({time.time()-t0:.0f}s)", flush=True)

res = dict(note=__doc__.split("\n")[0], grid=GRID, live_equivalent_E_of_576=576 * 1.808 / 3.25, domains={})
for dom in ("raw", "replay"):
    X = np.empty((200000, Xm.shape[1]), np.float32)
    for i in range(0, 200000, CH):
        A = np.asarray(Xm[i:i + CH]).astype(np.float32)
        if dom == "replay":
            A = T.hw_raw_transform(T.apply_affine(A, complex(np.load(ROOT / "k2_loopback.npy")), complex(np.load(ROOT / "c2_loopback.npy"))))
        X[i:i + CH] = A
    mom = moments(X, ytr)
    print(f"{dom}: moments ({time.time()-t0:.0f}s)", flush=True)
    if dom == "raw":
        Xev = np.asarray(X100[rows_h], np.float64); yev = y100[rows_h]
    else:
        Xev = T.hw_raw_transform(fir.astype(np.float64)).astype(np.float64); yev = y_r
    P, r = {}, {}
    for E in GRID:
        fv, lam, w, t = lda_for(X, ytr, mom, E)
        P[E] = (Xev[:, :2 * E] @ w > t).astype(int)
        r[str(E)] = dict(ridge=lam, val=fv, test=fstats(P[E], yev), qubit_time_us=E * 3.25e-3,
                         live_samples_needed_at_1808ps=int(round(E * 3.25 / 1.808)))
        print(f"  {dom} E={E:4d}: test {r[str(E)]['test']['fid']:.3f}  (val {fv:.3f}, ridge {lam:g})  ({time.time()-t0:.0f}s)", flush=True)
    for E in GRID:
        r[str(E)]["vs576"] = paired(P[E], P[576], yev); r[str(E)]["vs320"] = paired(P[E], P[320], yev)
    res["domains"][dom] = dict(n=int(len(yev)), points=r)
    (OUT / "window_live.json").write_text(json.dumps(res, indent=1, default=float))
    del X
print(f"done ({time.time()-t0:.0f}s)")
