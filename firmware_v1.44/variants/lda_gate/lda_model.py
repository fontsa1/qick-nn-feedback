"""Bit-exact Python model of LDA_live (hls/firmware/LDA_live.cpp), and the csim test-vector writer.

Model, for one window of N_SAMP = 576 words {Q << 16 | I} (int16 each) and the deployed constants (lda_weights.npz):
    D        = sum_n wI[n]*I_n + wQ[n]*Q_n - T1             (int64; exact, |D| < 2^40)
    decision = D >= 0
    logit    = clip((D >> SH) + 16, -32768, 32767)           (raw Q.10, >> is an arithmetic shift = floor)
    record   = [shot, D & 0xFFFFFFFF, (D >> 32) & 0xFFFFFFFF, T1 & 0xFFFFFFFF, SH, logit & 0xFFFF, sigmoid, decision]

`python lda_model.py --tb <dir>` writes, for every v1.44 NN_live capture on disk (campaign_v144/final/live, both
boards, both runs, all rows including the map rows), the words exactly as the gate passed them (live_words):
    <dir>/lda_words.bin   int32 N, then N*576 uint32
    <dir>/lda_expect.bin  int32 N, then N int64 D, N int32 logit (raw, sign-extended), N int32 decision
    <dir>/lda_index.npz   board, run, rows, y, NN_live decision per shot (for scoring the csim output)
"""
import argparse, glob
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N_SAMP = 576


def load_consts():
    z = np.load(HERE / "lda_weights.npz")
    wq = z["wq"].astype(np.int64)
    return wq[0::2], wq[1::2], int(z["T1"]), int(z["SH"])


def split_words(words):
    words = np.asarray(words, np.uint32)
    I = (words & 0xFFFF).astype(np.uint16).view(np.int16).astype(np.int64)
    Q = (words >> 16).astype(np.uint16).view(np.int16).astype(np.int64)
    return I, Q


def lda_live(words, consts=None):
    """words: (n, 576) uint32. Returns D (int64), decision (int), logit raw (int, -32768..32767)."""
    wI, wQ, T1, SH = consts or load_consts()
    I, Q = split_words(words)
    D = I @ wI + Q @ wQ - T1
    dec = (D >= 0).astype(np.int64)
    logit = np.clip((D >> SH) + 16, -32768, 32767)
    return D, dec, logit


def write_tb(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    consts = load_consts()
    W, meta = [], dict(board=[], run=[], rows=[], y=[], nn_dec=[])
    for f in sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run*_*.npz"))):
        nm = Path(f).stem.split("_"); z = np.load(f)
        W.append(z["live_words"].astype(np.uint32)); n = len(z["rows"])
        meta["board"] += [nm[0]] * n; meta["run"] += [nm[1]] * n
        meta["rows"].append(z["rows"]); meta["y"].append(z["y"]); meta["nn_dec"].append(z["live_rec"][:, 7] & 1)
    W = np.concatenate(W)
    D, dec, logit = lda_live(W, consts)
    N = np.int32(len(W))
    with open(out / "lda_words.bin", "wb") as fh:
        fh.write(N.tobytes()); fh.write(np.ascontiguousarray(W).tobytes())
    with open(out / "lda_expect.bin", "wb") as fh:
        fh.write(N.tobytes()); fh.write(D.astype(np.int64).tobytes())
        fh.write(logit.astype(np.int32).tobytes()); fh.write(dec.astype(np.int32).tobytes())
    np.savez(out / "lda_index.npz", board=np.array(meta["board"]), run=np.array(meta["run"]),
             rows=np.concatenate(meta["rows"]), y=np.concatenate(meta["y"]), nn_dec=np.concatenate(meta["nn_dec"]),
             D=D, dec=dec, logit=logit)
    print(f"wrote {len(W)} windows to {out}; decisions=1: {dec.mean():.4f}; logit saturated: "
          f"{int(((logit == 32767) | (logit == -32768)).sum())}; |D| max 2^{np.log2(np.abs(D).max()):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tb", required=True)
    write_tb(ap.parse_args().tb)
