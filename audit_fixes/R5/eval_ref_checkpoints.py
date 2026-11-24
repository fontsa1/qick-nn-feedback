"""R5 (context only): score the reference repo's released 800-input checkpoints for the 0528 dataset
(ml-quantum-readout-ref/notebooks/models/20240528/model_{lo}_{hi}/qmodel_{lo}_{hi}.h5 — single-layer
QDense(2, 6-bit quantized_bits) + BatchNorm, i.e. a quantized linear classifier, NOT the 800-4-1 ternary
network; no 800-4-1 checkpoint is shipped) on the full raw 100k test split, decision = argmax
(as in notebooks/board_comparison.ipynb cell 12, one-hot column 1 = excited, cell 5).
Their training-data provenance for these files is not recorded; scored as released.

  python audit_fixes/R5/eval_ref_checkpoints.py
"""
import os
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from qkeras.utils import _add_supported_quantized_objects

tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REF = ROOT / "ml-quantum-readout-ref" / "notebooks" / "models"   # a clone of fastmachinelearning/ml-quantum-readout


def wilson(k, n, z=1.959964):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - hw), 100 * (c + hw)


yte = np.load(ROOT / "0528_y_test_0_770.npy").astype(int)
Xte = np.load(ROOT / "0528_X_test_0_770.npy", mmap_mode="r")
co = {}
_add_supported_quantized_objects(co)
res = {}
for date in ("20240528", "20240527"):
    for lo, hi in ((100, 500), (150, 550), (50, 450), (0, 400)):
        f = REF / date / f"model_{lo}_{hi}" / f"qmodel_{lo}_{hi}.h5"
        if not f.exists():
            continue
        m = tf.keras.models.load_model(f, custom_objects=co, compile=False)
        X = np.asarray(Xte[:, 2 * lo:2 * hi], dtype=np.float32)
        pred = np.argmax(m.predict(X, batch_size=8192, verbose=0), axis=1)
        p10, p01 = float(np.mean(pred[yte == 0] != 0)), float(np.mean(pred[yte == 1] != 1))
        k = int((pred == yte).sum())
        lo95, hi95 = wilson(k, len(yte))
        key = f"{date}/model_{lo}_{hi}"
        res[key] = dict(fid=100 * (1 - 0.5 * (p10 + p01)), lo=lo95, hi=hi95, p10=100 * p10, p01=100 * p01)
        print(f"{key}: balanced fidelity {res[key]['fid']:.3f}% [{lo95:.2f}, {hi95:.2f}]  "
              f"P(1|0) {100 * p10:.2f}  P(0|1) {100 * p01:.2f}", flush=True)
        tf.keras.backend.clear_session()
(HERE / "ref_checkpoints_results.json").write_text(json.dumps(res, indent=1))
