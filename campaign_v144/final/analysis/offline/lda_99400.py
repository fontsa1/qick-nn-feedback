"""LDA at the headline's n, paired with NN_live on the same shots.

The paper's LDA numbers (Table II, P100, P178, P186) are scored on 19,400 rows of the 20k NN_axi replay (FIR stream).
The v1.44 NN_live campaign stored, for every replayed row on both boards, the FIR stream ('fir') and the boxcar stream
NN_live classified ('box'), plus NN_live's decision (live_rec[:, 7]). So LDA can be scored on exactly the shots the
95.60% headline uses, and paired with NN_live shot by shot (exact McNemar).

  FIR LDA  linear_v144.py's window_tradeoff recipe, unchanged: rows [0, 180k) of 0528_X_train_0_770 through (k2, c2) and
           hw_raw_transform, ridge chosen on rows [180k, 200k); windows E = 770 and 576.
  box LDA  the same recipe on NN_live's own training set (0528_X_train_box_calibrated.npy: the boxcar-path domain map
           applied to the deployed recipe's rows), window 576, scored on the 'box' stream NN_live classified: the
           like-for-like linear discriminator (B05 Q8).
Sets: the headline mosaic (run 1: board A rows 0-49,999, board B rows 50,000-99,999, map rows 1000:1600 excluded = 99,400),
and each board's full split (run 1 + run 2 = every row once on that board, 99,400). Development rows (0-19,999) and the
80,000 fresh rows are also reported separately.

Writes lda_99400.json and lda_99400_preds.npz next to this script. Read-only on everything else.
"""
import glob, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2")); sys.path.insert(0, str(ROOT / "analysis_scripts" / "analysis"))
import task33_three_way_comparison as T  # noqa: E402
from r3_stats import fstats, paired  # noqa: E402

CH, NTR, RIDGES = 10000, 180000, (1e-4, 1e-3, 1e-2, 1e-1)
t0 = time.time()

def fid(pred, y):
    return 100 * (1 - 0.5 * (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)))

def best_thr(s, y):
    o = np.sort(s); cand = o[::max(1, len(o) // 4000)]
    return cand[int(np.argmax([fid((s > t).astype(int), y) for t in cand]))]

def train(X, y, E):
    """window_tradeoff recipe: class moments on [0, NTR), ridge by validation fidelity on [NTR, 200k)."""
    d = 2 * E
    s1 = {0: np.zeros(d), 1: np.zeros(d)}; s2 = {0: np.zeros((d, d)), 1: np.zeros((d, d))}; n = {0: 0, 1: 0}
    for i in range(0, NTR, CH):
        A = X[i:i + CH, :d].astype(np.float64); yy = y[i:i + CH]
        for c in (0, 1):
            Ac = A[yy == c]; s1[c] += Ac.sum(0); s2[c] += Ac.T @ Ac; n[c] += len(Ac)
    m = {c: s1[c] / n[c] for c in (0, 1)}
    S = sum(s2[c] - n[c] * np.outer(m[c], m[c]) for c in (0, 1)) / (n[0] + n[1])
    sc = lambda lo, hi, w: np.concatenate([X[i:min(i + CH, hi), :d].astype(np.float64) @ w for i in range(lo, hi, CH)])
    best = None
    for lam in RIDGES:
        w = np.linalg.solve(S + lam * np.trace(S) / d * np.eye(d), m[1] - m[0])
        t = best_thr(sc(0, NTR, w), y[:NTR]); fv = fid((sc(NTR, 200000, w) > t).astype(int), y[NTR:200000])
        if best is None or fv > best[0]:
            best = (fv, lam, w, t)
    print(f"  trained E={E}: ridge {best[1]:g}, validation {best[0]:.3f} ({time.time()-t0:.0f}s)", flush=True)
    return best

# ---- the stored v1.44 NN_live captures (preallocated per board/run, int16 streams; memory-light)
files = {}
for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run*_*.npz"))):
    nm = Path(f).stem; files.setdefault((nm.split("_")[0], nm.split("_")[1]), []).append(f)
S = {}
for key, fl in files.items():
    n = sum(len(np.load(f)["rows"]) for f in fl)
    d = dict(rows=np.empty(n, np.int64), y=np.empty(n, np.int64), dec=np.empty(n, np.int64), weq=np.empty(n, bool),
             fir=np.empty((n, 1540), np.int16), box=np.empty((n, 1540), np.int16))
    k = 0
    for f in fl:
        z = np.load(f); m = len(z["rows"])
        d["rows"][k:k + m] = z["rows"]; d["y"][k:k + m] = z["y"]; d["dec"][k:k + m] = z["live_rec"][:, 7] & 1
        d["weq"][k:k + m] = z["window_eq_buffer"]; d["fir"][k:k + m] = z["fir"]; d["box"][k:k + m] = z["box"]; k += m
    keep = ~((d["rows"] >= 1000) & (d["rows"] < 1600))
    if not keep.all():
        d = {kk: v[keep] for kk, v in d.items()}
    S[key] = d
    print(f"{key}: {len(d['rows'])} rows {d['rows'].min()}-{d['rows'].max()}, window==buffer {d['weq'].mean():.4f}", flush=True)

y100 = np.load(ROOT / "test100k_real_y.npy").astype(int)
for k, d in S.items():
    assert np.array_equal(d["y"], y100[d["rows"]]), f"labels differ from test100k_real_y for {k}"

# ---- FIR LDA (k2/c2 map, as linear_v144.py)
k2 = complex(np.load(ROOT / "k2_loopback.npy")); c2 = complex(np.load(ROOT / "c2_loopback.npy"))
Xm = np.load(ROOT / "0528_X_train_0_770.npy", mmap_mode="r"); ytr = np.load(ROOT / "0528_y_train_0_770.npy")[:200000].astype(int)
X = np.empty((200000, Xm.shape[1]), np.float32)
for i in range(0, 200000, CH):
    X[i:i + CH] = T.hw_raw_transform(T.apply_affine(np.asarray(Xm[i:i + CH]).astype(np.float32), k2, c2))
print(f"FIR training pool loaded ({time.time()-t0:.0f}s)", flush=True)
models = {f"fir{E}": (train(X, ytr, E), "fir", E) for E in (770, 576)}
del X
# ---- box LDA (NN_live's own training set, row order = 0528_X_train_box_calibrated_rows.npy)
Xb = np.load(ROOT / "0528_X_train_box_calibrated.npy", mmap_mode="r")
rb = np.load(ROOT / "0528_X_train_box_calibrated_rows.npy")
yb = np.load(ROOT / "0528_y_train_0_770.npy")[rb].astype(int)
# rows in the deployed set's order (0:10000, then 110000:300000); validation = the last 20,000 of them, as for FIR
models["box576"] = (train(Xb, yb, 576), "box", 576)

# ---- score
res = dict(note=__doc__.split("\n")[0], models={k: dict(ridge=v[0][1], val_fid=v[0][0], stream=v[1], E=v[2]) for k, v in models.items()},
           sets={})
preds = {}
def score(d, mk):
    (fv, lam, w, t), stream, E = models[mk]
    Z = T.hw_raw_transform(d[stream][:, :2 * E].astype(np.float64)).astype(np.float64) if stream == "fir" else d[stream][:, :2 * E].astype(np.float64)
    return (Z @ w > t).astype(int)

sets = {
    "headline_mosaic": [(("A", "run1"), lambda r: r < 50000), (("B", "run1"), lambda r: r >= 50000)],
    "A_full": [(("A", "run1"), lambda r: r >= 0), (("A", "run2"), lambda r: r >= 0)],
    "B_full": [(("B", "run1"), lambda r: r >= 0), (("B", "run2"), lambda r: r >= 0)],
}
for sn, parts in sets.items():
    rows, y, dec = [], [], []; P = {mk: [] for mk in models}
    for key, sel in parts:
        d = S[key]; m = sel(d["rows"])
        dd = {k: v[m] for k, v in d.items()}
        rows.append(dd["rows"]); y.append(dd["y"]); dec.append(dd["dec"])
        for mk in models:
            P[mk].append(score(dd, mk))
    rows, y, dec = np.concatenate(rows), np.concatenate(y), np.concatenate(dec); P = {k: np.concatenate(v) for k, v in P.items()}
    assert len(np.unique(rows)) == len(rows)
    r = dict(n=int(len(rows)), NN_live=fstats(dec, y))
    for mk in models:
        r[mk] = fstats(P[mk], y); r[f"NN_live_vs_{mk}"] = paired(dec, P[mk], y)
        preds[f"{sn}_{mk}"] = P[mk]
    for sub, msk in (("dev_0_19999", rows < 20000), ("fresh_20000_99999", rows >= 20000)):
        r[sub] = {"NN_live": fstats(dec[msk], y[msk]), **{mk: fstats(P[mk][msk], y[msk]) for mk in models},
                  **{f"NN_live_vs_{mk}": paired(dec[msk], P[mk][msk], y[msk]) for mk in models}}
    preds[f"{sn}_rows"] = rows; preds[f"{sn}_y"] = y; preds[f"{sn}_NN_live"] = dec
    res["sets"][sn] = r
    print(f"{sn} (n={len(rows)}): NN_live {r['NN_live']['fid']:.3f}  " + "  ".join(
        f"{mk} {r[mk]['fid']:.3f} (NN-{mk} {r[f'NN_live_vs_{mk}'].get('diff', float('nan')) if isinstance(r[f'NN_live_vs_{mk}'], dict) else ''} p={r[f'NN_live_vs_{mk}']['p_exact']:.3g})"
        for mk in models), flush=True)

# consistency with the paper's 20k NN_axi-replay LDA on the same rows (board A, rows 0-19,999)
lp = np.load(ROOT / "campaign_v144/final/analysis/linear_preds_A.npz")
d = S[("A", "run1")]; m = d["rows"] < 20000
mine = score({k: v[m] for k, v in d.items()}, "fir770"); theirs = lp["wt_lda_770"][d["rows"][m]]
res["check_vs_linear_v144_A_wt_lda_770"] = dict(n=int(m.sum()), agree=float(np.mean(mine == theirs)),
                                                 fid_mine=fid(mine, d["y"][m]), fid_paper_replay=fid(theirs, d["y"][m]))
print("check vs linear_v144 (A, rows 0-19,999 excl. map):", res["check_vs_linear_v144_A_wt_lda_770"], flush=True)
np.savez(OUT / "lda_99400_preds.npz", **preds)
(OUT / "lda_99400.json").write_text(json.dumps(res, indent=1, default=float))
print(f"done ({time.time()-t0:.0f}s)")
