"""The noise numbers of P77 / P195 recomputed from the source arrays with each
candidate estimator, to show which estimator reproduces each printed number.

Source arrays: 0528_X_train_0_770.npy / 0528_y_train_0_770.npy (repo root; read-only, memory-mapped).
Pools:
  P20  training rows 10,000:30,000 (fig2's ROWS)
  R14  training rows 10,000:110,000, first 40,000 shots of each class (audit_fixes/R14/noise_model_table.py)
  CHR  char_real_readout_noise.py's block sample: 12 blocks of 5,000 spread over the file, first 1,200 shots of each
Estimators (residual = shot - its class mean over the pool):
  sigma   E1 single shot: s.d. over the 770 I samples of the first class-0 shot of P20 (make_fig2_data_noise.py:73)
          E2 pooled per-component s.d. of all residual I samples (P20), and Q
          E3 sqrt(mean per-sample variance) (R14 white_pred x sqrt(770)), per class and I/Q
          E4 complex residual s.d. |r| (char script's np.std of complex residuals) = sqrt(2) x per-component
  offset  O1 per class and quadrature: s.d. over shots of the trace mean / sqrt(mean per-sample var / 770) (R14)
          O2 pooled over classes, per quadrature: s.d. of the trace mean / (pooled residual s.d. / sqrt(770)) (agent 4)
          O3 complex, pooled: s.d. of |complex trace mean|-style offset as in qubit_synth_lib's note
             (sigma_complex*sqrt(PSD0/n) vs measured offset std): measured complex offset s.d. / (sigma_complex/sqrt(770))
  kurtosis K1 pooled I and Q residuals over P20 (scipy, Fisher, biased); K2 per class; K3 the char script's
          Q4 (|0>,|1> real part, subsampled) and SUMMARY (|1> real, every 13th) on CHR; K1 on R14
  stationarity S1 per-sample s.d. profile (I, pooled classes, P20): min/mean and max/mean; S2 char script Q2:
          sigma_0 max/min over the trace (complex residual, class 0, CHR); also per class on R14.
Writes t5_estimators.json.

"""
import json, sys
from pathlib import Path
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT)); from pstats import sha256  # noqa: E402
XTR, YTR = ROOT / "0528_X_train_0_770.npy", ROOT / "0528_y_train_0_770.npy"
X = np.load(XTR, mmap_mode="r"); Y = np.load(YTR, mmap_mode="r")
res = {"sources": {"0528_y_train_0_770.npy": sha256(YTR)}}
N = 770

def resid(rows):
    x = np.asarray(X[rows], dtype=np.float64); y = np.asarray(Y[rows]).reshape(-1).astype(int)
    z = x[:, 0::2] + 1j * x[:, 1::2]
    m = {c: z[y == c].mean(0) for c in (0, 1)}
    r = z - np.where(y[:, None] == 1, m[1], m[0])
    return z, r, y, m

# ---------------- P20
z, r, y, m = resid(slice(10_000, 30_000))
I, Q = r.real, r.imag
i0 = np.flatnonzero(y == 0)
sig = {}
sig["E1_single_shot_first_class0_I"] = float(np.std(z[i0[0]].real - m[0].real))
per_shot = np.std(I[y == 0], axis=1)
sig["E1_spread_over_class0_shots_sd"] = float(per_shot.std()); sig["E1_class0_median"] = float(np.median(per_shot))
sig["E1_class0_mean"] = float(per_shot.mean())
sig["E2_pooled_I"] = float(I.std()); sig["E2_pooled_Q"] = float(Q.std())
sig["E2_class0_I"] = float(I[y == 0].std()); sig["E2_class1_I"] = float(I[y == 1].std())
sig["E4_complex_pooled"] = float(np.std(r))
snr = {"mean|mu1-mu0|/sigma_I": float(np.abs(m[1] - m[0]).mean() / I.std()),
       "mean|mu1-mu0|/sigma_complex": float(np.abs(m[1] - m[0]).mean() / np.std(r)),
       "rms|mu1-mu0|/sigma_complex": float(np.sqrt(np.mean(np.abs(m[1] - m[0]) ** 2)) / np.std(r))}
off = {}
for c in (0, 1):
    for nm, a in (("I", I[y == c]), ("Q", Q[y == c])):
        off[f"O1_P20_class{c}_{nm}"] = float(a.mean(1).std(ddof=1) / np.sqrt(a.var(axis=0, ddof=1).mean() / N))
off["O2_P20_pooled_I"] = float(I.mean(1).std() / (I.std() / np.sqrt(N)))
off["O2_P20_pooled_Q"] = float(Q.mean(1).std() / (Q.std() / np.sqrt(N)))
cm = r.mean(1)
off["O3_P20_complex_pooled"] = float(np.std(cm) / (np.std(r) / np.sqrt(N)))
kur = {"K1_P20_pooled_I": float(stats.kurtosis(I.ravel())), "K1_P20_pooled_Q": float(stats.kurtosis(Q.ravel()))}
kur["K1_P20_pooled_IQ"] = float(stats.kurtosis(np.concatenate([I.ravel(), Q.ravel()])))
for c in (0, 1):
    kur[f"K2_P20_class{c}_I"] = float(stats.kurtosis(I[y == c].ravel())); kur[f"K2_P20_class{c}_Q"] = float(stats.kurtosis(Q[y == c].ravel()))
prof = I.std(0)
sta = {"S1_P20_I_min_over_mean": float(prof.min() / prof.mean()), "S1_P20_I_max_over_mean": float(prof.max() / prof.mean()),
       "S1_P20_I_max_over_min": float(prof.max() / prof.min())}
del z, r, I, Q

# ---------------- R14 pool (first 40k per class of rows 10,000:110,000)
yy = np.asarray(Y[10_000:110_000]).reshape(-1).astype(int)
for c in (0, 1):
    idx = 10_000 + np.flatnonzero(yy == c)[:40_000]
    xc = np.asarray(X[idx], dtype=np.float64)
    mc = xc.mean(0); R = xc - mc   # R14 uses the mean over all class shots of the pool; first 40k for stats
    allc = 10_000 + np.flatnonzero(yy == c)
    mfull = np.zeros(2 * N)
    for k in range(0, len(allc), 10000):
        mfull += np.asarray(X[allc[k:k + 10000]], dtype=np.float64).sum(0)
    mfull /= len(allc); R = xc - mfull
    for ch, nm in ((0, "I"), (1, "Q")):
        a = R[:, ch::2]
        wp = np.sqrt(a.var(axis=0, ddof=1).mean() / N)
        off[f"O1_R14_class{c}_{nm}"] = float(a.mean(1).std(ddof=1) / wp)
        sig[f"E3_R14_class{c}_{nm}"] = float(wp * np.sqrt(N))
        kur[f"K1_R14_class{c}_{nm}"] = float(stats.kurtosis(a.ravel()))
        p = a.std(0); sta[f"S1_R14_class{c}_{nm}_max_over_min"] = float(p.max() / p.min())
        sta[f"S1_R14_class{c}_{nm}_maxdev_from_mean"] = float(max(p.max() / p.mean() - 1, 1 - p.min() / p.mean()))
    del xc, R

# ---------------- CHR (char_real_readout_noise.py's sample)
yall = np.load(YTR).astype(int)
BLOCK, NB, PB = 5000, 12, 1200
nblk = X.shape[0] // BLOCK
picks = np.linspace(0, nblk - 2, NB).astype(int)
idx = {0: [], 1: []}
for b in picks:
    lo = b * BLOCK; idx[int(yall[lo])].append(np.arange(lo, lo + PB))
zc = {}
for c in (0, 1):
    if idx[c]:
        a = np.asarray(X[np.concatenate(idx[c])], dtype=np.float64); zc[c] = a[:, 0::2] + 1j * a[:, 1::2]
r0 = zc[0] - zc[0].mean(0); r1 = zc[1] - zc[1].mean(0)
res["CHR_rows"] = {c: [int(v[0]) for v in idx[c]] for c in (0, 1)}
res["CHR_note"] = "char script reads the WHOLE training file, including rows used for training and the fit pool"
sig["E4_CHR_complex_class0"] = float(np.std(r0)); sig["E4_CHR_complex_class1"] = float(np.std(r1))
st0 = np.std(r0, axis=0)
sta["S2_CHR_sigma0_max_over_min"] = float(st0.max() / st0.min())
for lab, rr in (("0", r0), ("1", r1)):
    f = rr.real.ravel() / np.std(rr.real); f = f[::max(1, len(f) // 200000)]
    kur[f"K3_CHR_Q4_class{lab}"] = float(stats.kurtosis(f))
kur["K3_CHR_SUMMARY_class1"] = float(stats.kurtosis(r1.real.ravel()[::13]))
res.update(sigma=sig, snr=snr, offset_ratio=off, kurtosis=kur, stationarity=sta)
(OUT / "t5_estimators.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: res[k] for k in ("sigma", "snr", "offset_ratio", "kurtosis", "stationarity")}, indent=1))
