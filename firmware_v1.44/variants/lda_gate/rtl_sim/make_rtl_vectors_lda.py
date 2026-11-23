"""Vectors for tb_lda.sv: K real gate windows from the csim set (lda_words.bin) and their expected outputs from the
bit-exact Python model (lda_model.py), independent of LDA_live's C++.

windows.hex  : K*576 lines, one 32-bit word each (Q<<16 | I)
expected.hex : K lines: logit raw (16 bits), decision (1), D[31:0], D[47:32] sign-extended (32), hex, space-separated
The K windows: the 12 with the largest |D| (6 per class) and 12 nearest the threshold (smallest |D|).
"""
import os
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import lda_model as M  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
TB = Path(os.environ.get("QICK_WORK", "work")) / "hls_lda/tb_data"
raw = np.fromfile(TB / "lda_words.bin", dtype="<u4")
W = raw[1:].reshape(int(raw[0]), 576)
D, dec, logit = M.lda_live(W)
o = np.argsort(D)
pick = np.concatenate([o[:6], o[-6:], np.argsort(np.abs(D))[:12]])
D, dec, logit, W = D[pick], dec[pick], logit[pick], W[pick]
(OUT / "windows.hex").write_text("\n".join(f"{int(v):08x}" for v in W.ravel()) + "\n")
lines = [f"{int(l) & 0xFFFF:04x} {int(d):x} {int(x) & 0xFFFFFFFF:08x} {(int(x) >> 32) & 0xFFFFFFFF:08x}" for l, d, x in zip(logit, dec, D)]
(OUT / "expected.hex").write_text("\n".join(lines) + "\n")
print(f"wrote {len(pick)} windows; decisions {dec.tolist()}; D range {D.min()}..{D.max()}")
