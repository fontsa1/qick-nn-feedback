"""Integer reference for NN_live's first layer and its scaled sums, from the deployed weights (no hls4ml, no TF).

  acc_u = b2_u + sum_i w2[u, i] * x_i      x = (I0, Q0, I1, Q1, ...) of the 576 raw window words (int16 each)
  as_u  = K_u * acc_u + B_u                K_u, B_u = raw integers of batchnorm1's scale / bias (ap_fixed<40,8>: x 2^32)
  word  = as_u[47:16] as a signed 32-bit value (what the v1.44d record holds in words 1-4)
Layout of w2.txt as NN_live_test.cpp indexes it: w2[u * 2N + i]. Self-test against the v1.44 records (raw acc words):
"""
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
W = ROOT / "neural_net4_live576s" / "firmware" / "weights"
N = 576

def _txt(name):
    return [s.strip() for s in (W / name).read_text().replace("\n", ",").split(",") if s.strip()]

W2 = np.array([int(float(v)) for v in _txt("w2.txt")], np.int64).reshape(4, 2 * N)
B2 = np.array([int(float(v)) for v in _txt("b2.txt")], np.int64)
# load_weights_from_txt parses each value as a double and casts it to ap_fixed<40,8> (AP_TRN: floor on the 2^-32 grid)
_raw = lambda v: (Fraction(float(v)) * 2**32).__floor__()
K = np.array([_raw(v) for v in _txt("s4.txt")], dtype=object)
B4 = np.array([_raw(v) for v in _txt("b4.txt")], dtype=object)

def x_from_words(words):
    w = np.asarray(words, np.uint32).astype(np.int64)
    i = ((w & 0xFFFF) ^ 0x8000) - 0x8000; q = (((w >> 16) & 0xFFFF) ^ 0x8000) - 0x8000
    x = np.empty(w.shape[:-1] + (2 * N,), np.int64); x[..., 0::2] = i; x[..., 1::2] = q
    return x

def acc(words):
    return x_from_words(words) @ W2.T + B2                 # (shots, 4), exact in int64 (|acc| < 2^25)

def scaled_words(acc_u):
    """as_u[47:16] as signed int32, per shot and unit (Python ints: K * acc exceeds int64 only in theory; be exact)."""
    out = np.empty(acc_u.shape, np.int64)
    for s in range(acc_u.shape[0]):
        for u in range(4):
            a = int(K[u]) * int(acc_u[s, u]) + int(B4[u])
            a &= (1 << 48) - 1                             # ap_int<48> wrap
            wv = (a >> 16) & 0xFFFFFFFF
            out[s, u] = wv - (1 << 32) if wv >= 1 << 31 else wv
    return out

if __name__ == "__main__":
    import glob
    for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/A_run1_0_1000.npz")))[:1] + \
             sorted(glob.glob(str(ROOT / "campaign_v144/final/live/B_run1_50000_51000.npz")))[:1]:
        z = np.load(f)
        a = acc(z["live_words"]); rec = z["live_rec"][:, 1:5].astype(np.int64)
        rec = np.where(rec >= 2**31, rec - 2**32, rec)
        print(Path(f).name, "acc mismatches:", int(np.sum(a != rec)), "of", rec.size,
              "| K raw", [int(k) for k in K], "B raw", [int(b) for b in B4])
