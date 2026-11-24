"""Spectrum of the noise the replay channel adds, per board (pass 18, 2026-11-23; answers the authors' "colored, mostly
high-frequency noise" comment). Same linear time-invariant fit as campaign_v140L1/arch_aug.py's fit_channel, on the same
4,000 fit shots: L(f) = H(f) S(f) + N(f), with S the source trace under the board's loopback calibration, aligned by the
best integer lag, and L the replayed trace (replay20k_<board>.npy, rows 0-3,999). The residual N is what the channel adds.
For comparison, the source's own within-class noise (deviation from its class mean) is analysed the same way.

Reports, per band of the 552.96 MS/s complex stream: the share of the residual's power, the share a white noise would
have (the band's share of bins), and the residual's power relative to the source noise's in that band.

  python campaign_v144/final/analysis/channel_noise_v144.py      -> channel_noise_v144.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "analysis_scripts" / "analysis"))
import task33_three_way_comparison as T  # noqa: E402

N_FIT = 4000
LAGS = range(-8, 9)
BANDS = ((0, 5), (5, 20), (20, 60), (60, 150), (150, 277))
FS = 552.96


def cplx(X):
    return X[:, 0::2] + 1j * X[:, 1::2]


def shift(z, d):
    if d == 0:
        return z
    out = np.empty_like(z)
    out[..., d:] = z[..., :-d]
    out[..., :d] = z[..., :1]
    return out


def residual(zs, zl):
    """arch_aug.fit_channel's fit; returns the residual traces and |H|."""
    ds, dl = zs - zs.mean(0), zl - zl.mean(0)
    C = np.array([[np.abs(np.vdot(np.roll(ds[i], l)[10:-10], dl[i][10:-10])) for l in LAGS] for i in range(len(zs))])
    lag = np.array(LAGS)[C.argmax(1)]
    al = np.stack([shift(zs[i:i + 1], int(lag[i]))[0] for i in range(len(zs))])
    S, L = np.fft.fft(al, axis=1), np.fft.fft(zl, axis=1)
    H = (np.conj(S) * L).sum(0) / (np.abs(S) ** 2).sum(0)
    r = zl - np.fft.ifft(H * S, axis=1)
    return r - r.mean(0), H, Counter(lag.tolist())


def psd(z):
    return (np.abs(np.fft.fft(z, axis=1)) ** 2).mean(0)


def main():
    k2 = complex(np.load(ROOT / "calibration/k2_loopback.npy")); c2 = complex(np.load(ROOT / "calibration/c2_loopback.npy"))
    src = cplx(T.apply_affine(np.load(ROOT / "data/test20k_real_X.npy")[:N_FIT].astype(np.float64), k2, c2))
    y = np.load(ROOT / "data/loopback20k_real_y.npy")[:N_FIT].astype(int)   # equals s2/y20k.npy (s2_prep_v144.py asserts it)
    srcn = src.copy()
    for c in (0, 1):
        srcn[y == c] -= src[y == c].mean(0)
    f = np.abs(np.fft.fftfreq(src.shape[1], 1 / FS))
    P_src = psd(srcn)
    out = {"n_fit": N_FIT, "bands_MHz": BANDS, "boards": {}}
    for b in "AB":
        zl = cplx(np.load(ROOT / f"campaign_v144/final/analysis/replay20k_{b}.npy")[:N_FIT].astype(np.float64))
        r, H, lags = residual(src, zl)
        P = psd(r)
        res = {"resid_std": float(np.abs(r).std()), "source_noise_std": float(np.abs(srcn).std()),
               "lags": dict(sorted(lags.items())), "bands": []}
        for lo, hi in BANDS:
            m = (f >= lo) & (f < hi)
            res["bands"].append(dict(lo=lo, hi=hi, share=float(P[m].sum() / P.sum()), white_share=float(m.mean()),
                                     H_abs=float(np.abs(H[m]).mean()), vs_source=float(P[m].sum() / P_src[m].sum())))
        hi = f >= 60
        res["share_above_60MHz"] = float(P[hi].sum() / P.sum())
        res["white_share_above_60MHz"] = float(hi.mean())
        res["source_share_above_60MHz"] = float(P_src[hi].sum() / P_src.sum())
        out["boards"][b] = res
        print(b, f"resid std {res['resid_std']:.1f} (source noise {res['source_noise_std']:.1f});",
              f"share >= 60 MHz {res['share_above_60MHz']:.3f} (white {res['white_share_above_60MHz']:.3f},",
              f"source noise {res['source_share_above_60MHz']:.3f})")
        for x in res["bands"]:
            print(f"   {x['lo']:>3}-{x['hi']:<3} MHz share {x['share']:.3f} white {x['white_share']:.3f} |H| {x['H_abs']:.2f}"
                  f" resid/source {x['vs_source']:.2f}")
    p = Path(__file__).with_name("channel_noise_v144.json")
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", p.name)


if __name__ == "__main__":
    main()
