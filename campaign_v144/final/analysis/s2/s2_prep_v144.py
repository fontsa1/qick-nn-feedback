"""S2 inputs: one board's NN_axi session on v1.44 (the 20,000 replayed traces of replay20k_<board>.npy, in row order), its
labels, and the chip's own probabilities (the deployed ternary 4-unit network) as arch_aug.py's clean reference.

  python campaign_v144/final/analysis/s2/s2_prep_v144.py [A|B]     (default A; B added 2026-11-23)
Board A writes A_axi_probs20k.npy and y20k.npy (the 2026-11-14 names); board B writes B_axi_probs20k.npy and y20k_B.npy.
"""
import sys
import glob
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
D = ROOT / "campaign_v144/final"
BOARD = sys.argv[1] if len(sys.argv) > 1 else "A"
assert BOARD in ("A", "B")
fs = sorted(glob.glob(str(D / f"axi/{BOARD}_axi_*.npz")), key=lambda f: int(re.findall(r"_axi_(\d+)\.npz", f)[0]))
P, I, Y = [], [], []
for f in fs:
    z = np.load(f, allow_pickle=True)
    P.append(z["probs"]); I.append(z["idx"]); Y.append(z["y"])
I = np.concatenate(I); o = np.argsort(I); assert np.array_equal(I[o], np.arange(20000))
P, Y = np.concatenate(P)[o].astype(np.float64), np.concatenate(Y)[o].astype(int)
ref = np.load(ROOT / "data/loopback20k_real_y.npy").astype(int)
assert np.array_equal(Y, ref), "labels differ from loopback20k_real_y.npy"
np.save(D / f"analysis/s2/{BOARD}_axi_probs20k.npy", P)
np.save(D / ("analysis/s2/y20k.npy" if BOARD == "A" else "analysis/s2/y20k_B.npy"), Y)
print(BOARD, "chip fidelity on rows 4000+:", round(100 * (((P[4000:] > .5) == Y[4000:]).mean()), 3))
