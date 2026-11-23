"""Does the fixed-point network on the chip decide like the floating-point Keras model it was converted from?

P92 says the hls4ml default type is "overridden layer by layer so that the hardware matches the floating-point model".
This scores both on the chip's own input: for every replayed shot of the v1.44 NN_live campaign the per-shot files hold
the 576-sample window NN_live classified ('live_words') and its recorded decision (live_rec[:, 7]). Each window goes
through
  float   the QKeras model (model_signed_domain_seed20260901_w576_box.h5) in floating point, on the same scaled input
          (hw_raw_transform) the hls4ml model gets;
  hls4ml  the hls4ml fixed-point model of the same file, the emulator analyze_v144.py checks the chip's sigmoid against.
Decisions use the chip's rule, logit >= 1/64, written for a probability as p >= sigmoid(1/64); the float model is also
scored at p >= 0.5. The hls4ml model gives only its quantized sigmoid (steps of 1/1024), so its thresholded decisions
can differ from the chip's, which come from the logit; the chip's sigmoid itself equals the hls4ml model's on every shot
(analyze_v144.py, bit_exact).
Sets: the headline (run 1, map rows 1000:1600 excluded, 99,400 shots) and each board's full split (run 1 + run 2,
99,400 each).

Writes keras_vs_hls4ml.json next to this script. Read-only on everything else.
"""
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.update(KERAS_BACKEND="tensorflow", TF_USE_LEGACY_KERAS="1", TF_CPP_MIN_LOG_LEVEL="3")
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
D = ROOT / "campaign_v144" / "final"
sys.path[:0] = [str(ROOT / "audit_fixes" / "R3_R2"), str(ROOT / "analysis_scripts" / "analysis"),
                str(ROOT / "analysis_scripts" / "acquisition"), str(ROOT)]
from r3_stats import fstats, paired, calmask  # noqa: E402
import task33_three_way_comparison as T  # noqa: E402
import fixed_point_emulator as FP  # noqa: E402
from qkeras.utils import load_qmodel  # noqa: E402

LIVE_MODEL = "model_signed_domain_seed20260901_w576_box.h5"
P_THR = 1 / (1 + np.exp(-1 / 64))          # the chip's rule, logit >= 1/64, as a probability
t0 = time.time()

m = load_qmodel(str(ROOT / LIVE_MODEL), compile=False)
hm = FP.fixed_point_model(m, Path(os.environ.get("TEMP", ".")) / "hls4ml_fixed_point_emulator" / Path(LIVE_MODEL).stem)

def words_to_x(words):
    words = words.astype(np.uint32)
    x = np.empty((len(words), 1152), dtype=np.int64)
    x[:, 0::2] = (words & 0xFFFF).astype(np.uint16).view(np.int16).astype(np.int64)
    x[:, 1::2] = (words >> 16).astype(np.uint16).view(np.int16).astype(np.int64)
    return x

def load(board, run):
    fs = sorted(glob.glob(str(D / "live" / f"{board}_run{run}_*.npz")), key=lambda f: int(re.findall(r"_(\d+)_\d+\.npz", f)[0]))
    assert len(fs) == 50, (board, run, len(fs))
    R, Y, C, PF, PH = [], [], [], [], []
    for f in fs:
        z = np.load(f)
        assert int(z["live_n"]) == 576
        X = T.hw_raw_transform(words_to_x(z["live_words"]).astype(np.float64)).astype(np.float32)
        PF.append(np.asarray(m.predict(X, batch_size=4096, verbose=0), dtype=np.float64).reshape(-1))
        PH.append(np.asarray(hm.predict(np.ascontiguousarray(X))).astype(np.float64).reshape(-1))
        R.append(z["rows"]); Y.append(z["y"]); C.append(z["live_rec"][:, 7] & 1)
    d = dict(rows=np.concatenate(R), y=np.concatenate(Y).astype(int), chip=np.concatenate(C).astype(int),
             pf=np.concatenate(PF), ph=np.concatenate(PH))
    o = np.argsort(d["rows"])
    print(board, "run", run, f"{time.time() - t0:.0f} s", flush=True)
    return {k: v[o] for k, v in d.items()}

L = {(b, r): load(b, r) for b in "AB" for r in (1, 2)}

def join(a, b):
    out = {k: np.concatenate([a[k], b[k]]) for k in a}
    o = np.argsort(out["rows"])
    return {k: v[o] for k, v in out.items()}

def report(d, mask):
    d = {k: v[mask] for k, v in d.items()}
    df = (d["pf"] >= P_THR).astype(int); dh = (d["ph"] >= P_THR).astype(int)
    diff = np.abs(d["pf"] - d["ph"])
    flip = np.flatnonzero(df != dh)
    return dict(
        n=int(len(d["y"])),
        float_vs_hls4ml_decisions_agree=int((df == dh).sum()),
        hls4ml_vs_chip_decisions_agree=int((dh == d["chip"]).sum()),
        float_vs_chip_decisions_agree=int((df == d["chip"]).sum()),
        float_p05_vs_chip_decisions_agree=int(((d["pf"] >= 0.5).astype(int) == d["chip"]).sum()),
        prob_absdiff_median=float(np.median(diff)), prob_absdiff_p99=float(np.quantile(diff, 0.99)), prob_absdiff_max=float(diff.max()),
        fid_float=fstats(df, d["y"]), fid_hls4ml=fstats(dh, d["y"]), fid_chip=fstats(d["chip"], d["y"]),
        float_vs_chip_paired=paired(df, d["chip"], d["y"]),
        flipped_shots=[dict(row=int(d["rows"][i]), y=int(d["y"][i]), p_float=float(d["pf"][i]), p_hls4ml=float(d["ph"][i]),
                            chip=int(d["chip"][i])) for i in flip[:50]],
    )

H = join(L[("A", 1)], L[("B", 1)])
A = join(L[("A", 1)], L[("A", 2)])
B = join(L[("B", 2)], L[("B", 1)])
assert np.array_equal(H["rows"], np.arange(100000))
res = dict(model=LIVE_MODEL, rule="decide 1 when p >= sigmoid(1/64) (the chip's logit >= 1/64)",
           headline=report(H, calmask(H["rows"])), boardA_full=report(A, calmask(A["rows"])), boardB_full=report(B, calmask(B["rows"])),
           seconds=round(time.time() - t0))
json.dump(res, open(OUT / "keras_vs_hls4ml.json", "w"), indent=1)
for k in ("headline", "boardA_full", "boardB_full"):
    r = res[k]
    print(k, r["n"], "float=hls4ml", r["float_vs_hls4ml_decisions_agree"], "hls4ml=chip", r["hls4ml_vs_chip_decisions_agree"],
          "float=chip", r["float_vs_chip_decisions_agree"], "fid float/hls4ml/chip",
          round(r["fid_float"]["fid"], 3), round(r["fid_hls4ml"]["fid"], 3), round(r["fid_chip"]["fid"], 3),
          "max |dp|", round(r["prob_absdiff_max"], 5))
