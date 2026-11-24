"""R5: re-run the NN arm of analysis_scripts/analysis/task51_raw_reference.py (our reproduction, the
number quoted as 96.00 +- 0.03%) and SAVE per-shot test probabilities, which the original run did not,
so the exact-config model can be compared shot by shot (exact McNemar).

Identical recipe to task51 (same build_model from export_signed_domain_model.py, same
hw_raw_transform, rows [0, 200k), per-seed numpy permutation, validation_split 0.2, batch 32,
<= 50 epochs, EarlyStopping patience 5 restore_best_weights, seeds 20260901/2/3, decision p > 0.5).
Only change: memory-lean loading (int16 staging; exact because every value is an integer within
int16, so hw_raw_transform is the identity) and 4 TF threads (the original used the default thread
pool, so the re-run need not be bit-identical; its accuracies are compared to task51_raw_reference.json).

  python audit_fixes/R5/reproduce_ours.py --seed 20260901
"""
import os
os.environ.setdefault("KERAS_BACKEND", "tensorflow")
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "4")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

tf.config.threading.set_intra_op_parallelism_threads(int(os.environ["TF_NUM_INTRAOP_THREADS"]))
tf.config.threading.set_inter_op_parallelism_threads(int(os.environ["TF_NUM_INTEROP_THREADS"]))

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "analysis_scripts" / "acquisition"))
import export_signed_domain_model as E  # noqa: E402


def load_int16(path, n):
    X = np.load(path, mmap_mode="r")
    n = n or X.shape[0]
    out = np.empty((n, X.shape[1]), np.int16)
    for i in range(0, n, 20000):
        blk = np.asarray(X[i:min(i + 20000, n)])
        h = E.hw_raw_transform(blk, E.SCALING_FACTOR)          # same transform as task51
        assert np.array_equal(h, blk.astype(np.float32))         # identity on this integer data
        out[i:i + len(blk)] = h.astype(np.int16)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-train", type=int, default=200000)
    a = ap.parse_args()
    out = HERE / "runs" / f"ours_s{a.seed}"
    out.mkdir(parents=True, exist_ok=True)

    ytr = np.load(ROOT / "0528_y_train_0_770.npy")[:a.n_train].astype(int)
    Xtr16 = load_int16(ROOT / "0528_X_train_0_770.npy", a.n_train)
    print(f"[ours_s{a.seed}] train rows [0,{a.n_train}), 1540 inputs; threads intra "
          f"{tf.config.threading.get_intra_op_parallelism_threads()}", flush=True)

    tf.keras.utils.set_random_seed(a.seed)
    perm = np.random.default_rng(a.seed).permutation(len(ytr))
    Xp = Xtr16[perm].astype(np.float32)
    del Xtr16
    yp = ytr[perm].astype("float32")
    m = E.build_model(Xp.shape[1])
    es = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    t0 = time.time()
    h = m.fit(Xp, yp, validation_split=0.2, epochs=50, batch_size=32, verbose=2, callbacks=[es])
    train_s = time.time() - t0
    del Xp
    m.save_weights(out / "weights.h5")

    Xte = load_int16(ROOT / "0528_X_test_0_770.npy", 0).astype(np.float32)
    yte = np.load(ROOT / "0528_y_test_0_770.npy").astype(int)
    p = m.predict(Xte, batch_size=4096, verbose=0).ravel().astype(np.float32)
    np.save(out / "test_prob.npy", p)
    pred = (p > 0.5).astype(int)
    e_acc = float(np.mean(pred[yte == 1] == 1))
    g_acc = float(np.mean(pred[yte == 0] == 0))
    vl = h.history["val_loss"]
    res = dict(tag=f"ours_s{a.seed}", seed=a.seed, epochs_run=len(vl), best_epoch=int(np.argmin(vl)) + 1,
               best_val_loss=float(min(vl)), train_seconds=train_s, test_acc=100 * float(np.mean(pred == yte)),
               test_balanced_fidelity=100 * 0.5 * (e_acc + g_acc), p10=100 * (1 - g_acc), p01=100 * (1 - e_acc),
               history={k: [float(v) for v in vs] for k, vs in h.history.items()})
    ref = json.loads((ROOT / "results/task51_raw_reference.json").read_text())
    orig = [r for r in ref["nn_seeds"] if r["seed"] == a.seed]
    if orig:
        res["task51_original_acc"] = orig[0]["acc"]
        res["task51_original_epochs"] = orig[0]["epochs"]
    (out / "result.json").write_text(json.dumps(res, indent=1))
    print(f"[ours_s{a.seed}] DONE: {len(vl)} epochs, test balanced fidelity {res['test_balanced_fidelity']:.3f}% "
          f"(task51 original {res.get('task51_original_acc')}); train {train_s / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
