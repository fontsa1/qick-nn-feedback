"""Build 2: fit the paper's boxcar-576 LDA, quantize it for the streaming LDA_live core, and score
float vs fixed point on the v1.44 NN_live captures already on disk.

The LDA is lda_99400.py's "box576" model, unchanged: class moments on rows [0, 180k) of NN_live's own training set
(0528_X_train_box_calibrated.npy, deployed recipe rows 0:10000 + 110000:300000 of 0528_X_train_0_770), ridge chosen
by validation fidelity on rows [180k, 200k) of that same training set, threshold from the training scores. No test row
(test100k_real_*) is used for fitting, ridge choice, threshold, quantization choice or scale choice.

Fixed point (bit-exact with LDA_live.cpp and lda_model.py):
  wq[i]  = round(w[i] * 2^F)  as signed WB-bit integers, F = (WB-1) - ceil(log2(max|w|)) (largest F that fits)
  S      = sum_n wq[2n]*I_n + wq[2n+1]*Q_n           (exact integer, int16 samples)
  T1     = floor(t * 2^F) + 1                        decision = S >= T1   (<=> S/2^F > t for the float rule)
  logit  = sat16(((S - T1) >> SH) + 16)              Q.10 pseudo-logit; logit >= 16 (1/64) <=> decision, so the
                                                     host's NN_live rules (logit >= 1/64, sigmoid > 0.5) still hold
  SH chosen on the TRAINING scores so that the class-mean separation maps to about +-8 logit units.

Writes lda_quant.json (model, per-set fidelities), lda_weights.npz (float w, t, wq, T1, SH) and lda_live_rom.h.
"""
import glob, json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
from r3_stats import fstats, paired  # noqa: E402

CH, NTR, RIDGES, E = 10000, 180000, (1e-4, 1e-3, 1e-2, 1e-1), 576
WB_LIST = (6, 8, 10, 12, 14, 16, 18)
WB_DEPLOY = 16
t0 = time.time()

def fid(pred, y):
    return 100 * (1 - 0.5 * (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)))

def best_thr(s, y):
    o = np.sort(s); cand = o[::max(1, len(o) // 4000)]
    return cand[int(np.argmax([fid((s > t).astype(int), y) for t in cand]))]

# ---------------- fit (lda_99400.py train(), verbatim logic)
Xb = np.load(ROOT / "0528_X_train_box_calibrated.npy", mmap_mode="r")
rb = np.load(ROOT / "0528_X_train_box_calibrated_rows.npy")
yb = np.load(ROOT / "0528_y_train_0_770.npy")[rb].astype(int)
d = 2 * E
s1 = {0: np.zeros(d), 1: np.zeros(d)}; s2 = {0: np.zeros((d, d)), 1: np.zeros((d, d))}; n = {0: 0, 1: 0}
for i in range(0, NTR, CH):
    A = np.asarray(Xb[i:i + CH, :d]).astype(np.float64); yy = yb[i:i + CH]
    for c in (0, 1):
        Ac = A[yy == c]; s1[c] += Ac.sum(0); s2[c] += Ac.T @ Ac; n[c] += len(Ac)
m = {c: s1[c] / n[c] for c in (0, 1)}
Sw = sum(s2[c] - n[c] * np.outer(m[c], m[c]) for c in (0, 1)) / (n[0] + n[1])
sc = lambda lo, hi, w: np.concatenate([np.asarray(Xb[i:min(i + CH, hi), :d]).astype(np.float64) @ w for i in range(lo, hi, CH)])
best = None
for lam in RIDGES:
    w = np.linalg.solve(Sw + lam * np.trace(Sw) / d * np.eye(d), m[1] - m[0])
    t = best_thr(sc(0, NTR, w), yb[:NTR]); fv = fid((sc(NTR, 200000, w) > t).astype(int), yb[NTR:200000])
    print(f"  ridge {lam:g}: validation {fv:.3f}", flush=True)
    if best is None or fv > best[0]:
        best = (fv, lam, w, t)
val_fid, lam, w, t = best
print(f"box576 LDA: ridge {lam:g}, validation {val_fid:.3f}, t {t:.6g} ({time.time()-t0:.0f}s)", flush=True)
str_train = sc(0, NTR, w)
ytr = yb[:NTR]

# ---------------- quantization (training rows only)
def quant(WB):
    F = (WB - 1) - int(np.ceil(np.log2(np.max(np.abs(w)))))
    wq = np.round(w * 2.0 ** F).astype(np.int64)
    lim = 2 ** (WB - 1)
    if wq.max() > lim - 1 or wq.min() < -lim:   # rounding up of the largest weight
        F -= 1; wq = np.round(w * 2.0 ** F).astype(np.int64)
    T1 = int(np.floor(t * 2.0 ** F)) + 1
    return F, wq, T1

def int_score(Xint, wq):
    """exact integer score, int64 (|S| < 2^47 for WB <= 18)"""
    return np.concatenate([Xint[i:i + CH].astype(np.int64) @ wq for i in range(0, len(Xint), CH)])

F, wq, T1 = quant(WB_DEPLOY)
# SH: map the training class-mean separation of S to about 2 * 8 logit units of 2^-10 (raw 2 * 8192)
Str = np.concatenate([np.round(np.asarray(Xb[i:i + CH, :d])).astype(np.int64) @ wq for i in range(0, NTR, CH)])
sep = abs(Str[ytr == 1].mean() - Str[ytr == 0].mean())
SH = max(0, int(round(np.log2(sep / (2 * 8192)))))
acc_bound = int(np.abs(wq).sum()) * 32768
ACC_W = acc_bound.bit_length() + 1
print(f"deploy WB={WB_DEPLOY}: F={F}, T1={T1}, SH={SH}, |S| bound {acc_bound} -> ACC_W {ACC_W}", flush=True)

# ---------------- test captures (v1.44 NN_live, both boards, both runs; same exclusion as lda_99400.py)
files = {}
for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run*_*.npz"))):
    nm = Path(f).stem; files.setdefault((nm.split("_")[0], nm.split("_")[1]), []).append(f)
S = {}
for key, fl in files.items():
    parts = [np.load(f) for f in fl]
    dd = dict(rows=np.concatenate([z["rows"] for z in parts]).astype(np.int64),
              y=np.concatenate([z["y"] for z in parts]).astype(np.int64),
              dec=np.concatenate([z["live_rec"][:, 7] & 1 for z in parts]).astype(np.int64),
              weq=np.concatenate([z["window_eq_buffer"] for z in parts]),
              words=np.concatenate([z["live_words"] for z in parts]),
              box=np.concatenate([z["box"][:, :d] for z in parts]))
    keep = ~((dd["rows"] >= 1000) & (dd["rows"] < 1600))
    S[key] = {k: v[keep] for k, v in dd.items()}
    print(f"{key}: {keep.sum()} rows ({time.time()-t0:.0f}s)", flush=True)
y100 = np.load(ROOT / "test100k_real_y.npy").astype(int)
for k, dd in S.items():
    assert np.array_equal(dd["y"], y100[dd["rows"]])

def words_to_x(words):
    """(n, 576) uint32 {Q<<16 | I} -> (n, 1152) int16 interleaved I, Q (LOAD_L order)"""
    x = np.empty((len(words), d), np.int16)
    x[:, 0::2] = (words & 0xFFFF).astype(np.uint16).view(np.int16)
    x[:, 1::2] = (words >> 16).astype(np.uint16).view(np.int16)
    return x

for dd in S.values():
    dd["x"] = words_to_x(dd["words"])
    dd["x_eq_box"] = np.all(dd["x"] == dd["box"], axis=1)
    del dd["words"]

sets = {
    "headline_mosaic": [(("A", "run1"), lambda r: r < 50000), (("B", "run1"), lambda r: r >= 50000)],
    "A_full": [(("A", "run1"), lambda r: r >= 0), (("A", "run2"), lambda r: r >= 0)],
    "B_full": [(("B", "run1"), lambda r: r >= 0), (("B", "run2"), lambda r: r >= 0)],
}
ref = np.load(ROOT / "campaign_v144/final/analysis/offline/lda_99400_preds.npz")
qs = {WB: quant(WB) for WB in WB_LIST}
res = dict(note=__doc__.split("\n")[0], fit=dict(ridge=lam, val_fid=val_fid, t=float(t), train_rows="0528_X_train_box_calibrated rows [0,180k) moments, [180k,200k) ridge",
                                                   train_fid_float=fid((str_train > t).astype(int), ytr)),
           deploy=dict(WB=WB_DEPLOY, F=F, T1=T1, SH=SH, ACC_W=ACC_W, acc_bound=acc_bound,
                       wq_min=int(wq.min()), wq_max=int(wq.max()), wq_zero=int((wq == 0).sum())),
           sets={})
for WB, (Fb, wqb, T1b) in qs.items():
    Sq = np.round(np.asarray(Xb[:NTR, :d][::9])).astype(np.int64) @ wqb   # every 9th training row, quick
    res.setdefault("train_subsample_fid_by_WB", {})[WB] = fid((Sq >= T1b).astype(int), ytr[::9])
preds = {}
for sn, parts in sets.items():
    cat = {k: [] for k in ("rows", "y", "dec", "x", "box", "weq", "x_eq_box")}
    for key, sel in parts:
        dd = S[key]; msk = sel(dd["rows"])
        for k in cat:
            cat[k].append(dd[k][msk])
    c = {k: np.concatenate(v) for k, v in cat.items()}
    y = c["y"]
    flt_box = ((c["box"].astype(np.float64) @ w) > t).astype(int)     # the paper's / lda_99400's box576 numbers
    flt_win = ((c["x"].astype(np.float64) @ w) > t).astype(int)       # same LDA on the exact window the gate passes
    r = dict(n=int(len(y)), window_eq_box=int(c["x_eq_box"].sum()), NN_live=fstats(c["dec"], y),
             float_lda_box=fstats(flt_box, y), float_lda_window=fstats(flt_win, y),
             agree_with_lda_99400_preds=float(np.mean(flt_box == ref[f"{sn}_box576"])) if f"{sn}_box576" in ref.files else None,
             rows_match_lda_99400=bool(np.array_equal(c["rows"], ref[f"{sn}_rows"])) if f"{sn}_rows" in ref.files else None,
             by_WB={})
    for WB, (Fb, wqb, T1b) in qs.items():
        Sq = int_score(c["x"], wqb)
        q = (Sq >= T1b).astype(int)
        r["by_WB"][WB] = dict(fid=fid(q, y), dF_vs_float_window=fid(q, y) - fid(flt_win, y),
                              flips_vs_float=int((q != flt_win).sum()), vs_float=paired(q, flt_win, y))
        if WB == WB_DEPLOY:
            preds[f"{sn}_q"] = q; preds[f"{sn}_S"] = Sq
    r["NN_live_vs_LDAq"] = paired(c["dec"], preds[f"{sn}_q"], y)
    for sub, msk in (("dev_0_19999", c["rows"] < 20000), ("fresh_20000_99999", c["rows"] >= 20000)):
        r[sub] = dict(n=int(msk.sum()), float_lda_window=fstats(flt_win[msk], y[msk]),
                      LDAq=fstats(preds[f"{sn}_q"][msk], y[msk]), NN_live=fstats(c["dec"][msk], y[msk]))
    preds[f"{sn}_rows"] = c["rows"]; preds[f"{sn}_y"] = y; preds[f"{sn}_float_window"] = flt_win
    res["sets"][sn] = r
    q = r["by_WB"][WB_DEPLOY]
    print(f"{sn} n={len(y)}: NN_live {r['NN_live']['fid']:.3f}  LDA float(box) {r['float_lda_box']['fid']:.3f}  "
          f"float(window) {r['float_lda_window']['fid']:.3f}  LDA q{WB_DEPLOY} {q['fid']:.3f} (flips {q['flips_vs_float']}); "
          f"agree lda_99400 {r['agree_with_lda_99400_preds']}", flush=True)
    print("   by WB: " + "  ".join(f"{WB}:{v['fid']:.3f}/{v['flips_vs_float']}" for WB, v in r["by_WB"].items()), flush=True)

# ---------------- outputs
np.savez(HERE / "lda_weights.npz", w=w, t=t, ridge=lam, wq=wq, F=F, T1=T1, SH=SH, WB=WB_DEPLOY, ACC_W=ACC_W)
np.savez(HERE / "lda_quant_preds.npz", **preds)
(HERE / "lda_quant.json").write_text(json.dumps(res, indent=1, default=float))
wi = wq[0::2]; wqq = wq[1::2]
lines = ["// GENERATED by firmware_v1.44/variants/lda_gate/lda_fit_quant.py -- do not edit.",
         "// box576 LDA (lda_99400.py recipe, training rows only), quantized: wq = round(w * 2^F).",
         "#ifndef LDA_LIVE_ROM_H_", "#define LDA_LIVE_ROM_H_", "#include \"ap_int.h\"", "",
         f"#define LDA_WB {WB_DEPLOY}", f"#define LDA_F {F}", f"#define LDA_SH {SH}", f"#define ACC_W {ACC_W}",
         f"// decision = S >= LDA_T1; float threshold t = {t!r}, ridge {lam:g}",
         f"static const long long LDA_T1 = {T1}LL;", "",
         f"// per sample n: bits [{WB_DEPLOY-1}:0] = weight of I_n, bits [{2*WB_DEPLOY-1}:{WB_DEPLOY}] = weight of Q_n (two's complement)",
         f"static const ap_uint<{2*WB_DEPLOY}> LROM[{E}] = {{"]
for k in range(0, E, 8):
    lines.append("    " + ", ".join(f"0x{((int(b) & 0xFFFF) << 16 | (int(a) & 0xFFFF)):08x}" for a, b in zip(wi[k:k+8], wqq[k:k+8])) + ",")
lines += ["};", "", "#endif", ""]
assert WB_DEPLOY == 16
(HERE / "hls" / "firmware").mkdir(parents=True, exist_ok=True)
(HERE / "hls" / "firmware" / "LDA_live_rom.h").write_text("\n".join(lines))
print(f"done ({time.time()-t0:.0f}s)")
