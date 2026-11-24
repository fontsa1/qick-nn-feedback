"""R5: extract the reference window [100, 500) (800 interleaved I/Q values) as float32.

Streams the float64 0528 files in chunks (memmap) so peak RAM stays small.
Outputs (new files, in audit_fixes/R5/data/):
  Xtr_w100_500_f32.npy  (900000, 800)  rows in the original file order (needed for
                                        Keras validation_split = last 5% semantics)
  Xte_w100_500_f32.npy  (100000, 800)
Also checks that every value is integer-valued (so float32 is exact and our int16
rounding in task51 is the identity on this data).
"""
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
LO, HI = 100, 500
CH = 20000

for src, dst in (("0528_X_test_0_770.npy", "Xte_w100_500_f32.npy"),
                 ("0528_X_train_0_770.npy", "Xtr_w100_500_f32.npy")):
    X = np.load(ROOT / src, mmap_mode="r")
    n = X.shape[0]
    Y = np.lib.format.open_memmap(OUT / dst, mode="w+", dtype=np.float32, shape=(n, 2 * (HI - LO)))
    nonint = 0
    vmin, vmax = np.inf, -np.inf
    for i in range(0, n, CH):
        blk = np.asarray(X[i:i + CH, 2 * LO:2 * HI])
        nonint += int(np.count_nonzero(blk != np.round(blk)))
        vmin, vmax = min(vmin, blk.min()), max(vmax, blk.max())
        Y[i:i + CH] = blk.astype(np.float32)
    Y.flush()
    del Y
    print(f"{src} -> {dst}: {n} rows, window [{LO},{HI}), range {vmin:.0f}..{vmax:.0f}, non-integer values {nonint}",
          flush=True)
