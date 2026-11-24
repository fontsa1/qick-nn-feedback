"""R5: train the reference paper's exact released NN configuration and score it on the full test split.

Configuration copied from ml-quantum-readout-ref/final/train.ipynb (cells 0, 4, 8, 10, 11):
  * keras.utils.set_random_seed(32)                         (cell 0)
  * window [100, 500): X[:, 200:1000] -> 800 inputs, raw ADC values, no scaling   (cells 4-6)
  * QDense(4, activation=None, ternary kernel+bias) -> BatchNormalization ->
    QDense(1, sigmoid, ternary kernel+bias); no ReLU, no regularisers             (cell 8)
  * Adam(1e-3), BinaryCrossentropy(from_logits=False), batch 256, epochs 50,
    validation_split 0.05 (Keras: the LAST 5% = 45,000 rows, taken before shuffling),
    shuffle=True (full reshuffle every epoch), EarlyStopping(val_loss, patience 10,
    restore_best_weights=True)                                                    (cells 10-11)
  * all 900,000 training rows (855,000 fit + 45,000 validation)
  * decision: sigmoid >= 0.5 -> 1 (cell 13: np.where(p < 0.5, 0, 1))

Memory: the window is pre-extracted to float32 by prep_window.py and memory-mapped; batches
are streamed by a keras Sequence that reshuffles all 855k fit rows every epoch (same
semantics as Keras' array shuffle=True). Only the 45k validation rows and the 100k test
rows are held in RAM (~0.5 GB).

  python audit_fixes/R5/train_exact.py --seed 32 [--lr 1e-3] [--epochs 50]
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
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

tf.config.threading.set_intra_op_parallelism_threads(int(os.environ["TF_NUM_INTRAOP_THREADS"]))
tf.config.threading.set_inter_op_parallelism_threads(int(os.environ["TF_NUM_INTEROP_THREADS"]))

from tensorflow.keras.layers import BatchNormalization  # noqa: E402
from qkeras.qlayers import QDense  # noqa: E402
from qkeras.quantizers import ternary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


class ShuffledMemmap(tf.keras.utils.Sequence):
    def __init__(self, X, y, n, batch, seed):
        super().__init__()
        self.X, self.y, self.n, self.batch = X, y, n, batch
        self.rng = np.random.default_rng(seed)
        self.order = self.rng.permutation(n)

    def __len__(self):
        return (self.n + self.batch - 1) // self.batch

    def __getitem__(self, i):
        idx = np.sort(self.order[i * self.batch:(i + 1) * self.batch])
        return self.X[idx].astype(np.float32), self.y[idx]

    def on_epoch_end(self):
        self.order = self.rng.permutation(self.n)


def build_reference_model(lr):
    model = tf.keras.models.Sequential()
    model.add(QDense(4, activation=None, name="fc1", input_shape=(800,),
                     kernel_quantizer=ternary(), bias_quantizer=ternary()))
    model.add(BatchNormalization(name="batchnorm1"))
    model.add(QDense(1, name="fc2", activation="sigmoid",
                     kernel_quantizer=ternary(), bias_quantizer=ternary()))
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
                  loss=tf.keras.losses.BinaryCrossentropy(from_logits=False), metrics=["accuracy"])
    return model


class EpochLog(tf.keras.callbacks.Callback):
    def on_epoch_begin(self, epoch, logs=None):
        self.t0 = time.time()

    def on_epoch_end(self, epoch, logs=None):
        print(f"epoch {epoch + 1}: " + " ".join(f"{k} {v:.5f}" for k, v in (logs or {}).items())
              + f"  ({time.time() - self.t0:.0f} s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--patience", type=int, default=10)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--max-steps", type=int, default=0, help="smoke test: steps per epoch cap")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    tag = a.tag or f"exact_s{a.seed}_lr{a.lr:g}"
    out = HERE / "runs" / tag
    out.mkdir(parents=True, exist_ok=True)

    Xtr = np.load(DATA / "Xtr_w100_500_f32.npy", mmap_mode="r")
    ytr = np.load(ROOT / "0528_y_train_0_770.npy").astype(np.float32)
    n = len(ytr)
    n_fit = int(np.floor(n * (1 - a.val_frac)))   # tf_keras train_validation_split: floor(n*(1-split))
    n_val = n - n_fit
    Xval = np.asarray(Xtr[n_fit:])
    yval = ytr[n_fit:]
    # Random row gathers from a Windows memmap cost ~78 ms/batch, so hold the fit rows in RAM as int16
    # (1.37 GB). Exact: every value is an integer in [-4883, 4654] (checked by prep_window.py).
    Xfit = np.empty((n_fit, Xtr.shape[1]), np.int16)
    for i in range(0, n_fit, 50000):
        blk = np.asarray(Xtr[i:min(i + 50000, n_fit)])
        assert np.array_equal(blk.astype(np.int16).astype(np.float32), blk)
        Xfit[i:i + len(blk)] = blk
    del Xtr
    print(f"[{tag}] fit rows [0,{n_fit}) val rows [{n_fit},{n}) (val class-1 frac {yval.mean():.4f}); "
          f"seed {a.seed} lr {a.lr:g} batch {a.batch} epochs {a.epochs} patience {a.patience}; "
          f"threads intra {tf.config.threading.get_intra_op_parallelism_threads()} "
          f"inter {tf.config.threading.get_inter_op_parallelism_threads()}", flush=True)

    tf.keras.utils.set_random_seed(a.seed)
    model = build_reference_model(a.lr)
    model.summary(print_fn=lambda s: print(s, flush=True))
    seq = ShuffledMemmap(Xfit, ytr, n_fit, a.batch, a.seed)
    es = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=a.patience, restore_best_weights=True)
    t0 = time.time()
    h = model.fit(seq, validation_data=(Xval, yval), epochs=a.epochs, shuffle=False, verbose=0,
                  steps_per_epoch=(a.max_steps or None), callbacks=[es, EpochLog()],
                  workers=1, use_multiprocessing=False)
    train_s = time.time() - t0
    vl = h.history["val_loss"]
    best_epoch = int(np.argmin(vl)) + 1
    model.save_weights(out / "weights.h5")

    Xte = np.load(DATA / "Xte_w100_500_f32.npy")
    yte = np.load(ROOT / "0528_y_test_0_770.npy").astype(int)
    p = model.predict(Xte, batch_size=4096, verbose=0).ravel().astype(np.float32)
    np.save(out / "test_prob.npy", p)
    pred = np.where(p < 0.5, 0, 1)
    e_acc = float(np.mean(pred[yte == 1] == 1))
    g_acc = float(np.mean(pred[yte == 0] == 0))
    res = dict(tag=tag, seed=a.seed, lr=a.lr, batch=a.batch, epochs_run=len(vl), best_epoch=best_epoch,
               best_val_loss=float(min(vl)), stopped_early=len(vl) < a.epochs, train_seconds=train_s,
               n_fit=n_fit, n_val=n_val, test_acc=100 * float(np.mean(pred == yte)),
               test_balanced_fidelity=100 * 0.5 * (e_acc + g_acc),
               p10=100 * (1 - g_acc), p01=100 * (1 - e_acc),
               history={k: [float(v) for v in vs] for k, vs in h.history.items()},
               tf_version=tf.__version__)
    (out / "result.json").write_text(json.dumps(res, indent=1))
    print(f"[{tag}] DONE: {len(vl)} epochs (best {best_epoch}, val_loss {min(vl):.5f}), "
          f"test balanced fidelity {res['test_balanced_fidelity']:.3f}% (acc {res['test_acc']:.3f}%), "
          f"P(1|0) {res['p10']:.2f} P(0|1) {res['p01']:.2f}; train {train_s / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
