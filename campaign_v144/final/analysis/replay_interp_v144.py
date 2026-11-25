"""What the replay's resampling does to the replayed traces, per board: how much of the replay channel's low-pass
response the linear interpolation accounts for, the time stretch it leaves, and the noise power the replayed traces
carry.

tools/run_loopback.py resamples each 770-sample trace to 11,000 envelope samples by linear interpolation on
np.linspace grids, so one source interval spans 10,999 / 769 = 14.303 DAC samples. The readout decimates the DAC's
7864.32 MS/s to 552.96 MS/s, 14.222 DAC samples per readout sample. Three results:

  1. Interpolation response. Linear interpolation passes frequency f with amplitude sinc^2(f / f_i), where
     f_i = 7864.32 / 14.303 MHz is the source sample rate on the DAC's time axis. Its power response, averaged over the
     bands of channel_noise_v144.py and taken relative to the 0-20 MHz band, is compared with the whole replay
     channel's |H|^2 from the same linear time-invariant fit (channel_noise_v144.residual, on the same 4,000 fit shots).
     A simulation of the resampling followed by an ideal band limit at the readout's Nyquist frequency checks the
     formula on the source traces' own noise.
  2. Time stretch. Each class mean of the replayed traces is fitted as g * s(a * m + b) + d over samples 8-759, where
     s is the source class mean, linearly interpolated; a is source samples per replayed sample, expected
     14.222 / 14.303.
  3. Noise power. The within-class noise of the replayed traces (each trace minus its class mean), over that of the
     source traces scaled by |g|^2, on samples 8-759 of all 20,000 shots.

  python campaign_v144/final/analysis/replay_interp_v144.py      -> replay_interp_v144.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import channel_noise_v144 as CN  # noqa: E402

SOURCE_X = ROOT / "data" / "test20k_real_X.npy"            # the 20,000 recorded traces run_loopback.py replayed
LABELS = ROOT / "data" / "loopback20k_real_y.npy"
K2, C2 = ROOT / "calibration" / "k2_loopback.npy", ROOT / "calibration" / "c2_loopback.npy"
REPLAY = HERE / "replay20k_{}.npy"                # the same traces replayed on v1.44, per board

F_DAC, FS = 7864.32, 552.96                       # MS/s: generator, decimated readout
N_SRC, N_ENV = 770, 11000
DAC_PER_SRC = (N_ENV - 1) / (N_SRC - 1)           # 14.303 DAC samples per source interval
F_I = F_DAC / DAC_PER_SRC                         # 549.83 MHz
LO, HI = 8, 760                                   # samples fitted, away from the trace ends
REF = (0, 20)                                     # MHz; band the relative responses are taken against
N_SIM = 2000


def cplx(X):
    X = np.asarray(X, np.float64)
    return X[:, 0::2] + 1j * X[:, 1::2]


def within_class(z, y):
    r = z.copy()
    for c in (0, 1):
        r[y == c] -= z[y == c].mean(0)
    return r


def band_mean(f, v, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(v[m].mean())


def rel_db(f, v, bands):
    ref = band_mean(f, v, *REF)
    return [float(10 * np.log10(band_mean(f, v, lo, hi) / ref)) for lo, hi in bands]


def interp_power(f):
    """Power response of linear interpolation at f MHz."""
    return np.sinc(f / F_I) ** 4


def simulate(z):
    """run_loopback.py's resampling, then an ideal readout: band limit to +-FS/2 and sample at FS. 11,008 DAC samples
    give 774 readout samples exactly (FS / F_DAC = 9 / 128)."""
    xo, xn = np.linspace(0, 1, N_SRC), np.linspace(0, 1, N_ENV)
    d = np.stack([np.interp(xn, xo, r.real) + 1j * np.interp(xn, xo, r.imag) for r in z])
    L, M = 11008, 774
    S = np.fft.fft(np.pad(d, ((0, 0), (0, L - N_ENV))), axis=1)
    P = np.zeros((len(z), M), complex)
    P[:, :M // 2], P[:, M - M // 2:] = S[:, :M // 2], S[:, L - M // 2:]
    return np.fft.ifft(P, axis=1) * (M / L)


def seg_psd(r):
    w = np.hanning(HI - LO)
    return (np.abs(np.fft.fft(r[:, LO:HI] * w, axis=1)) ** 2).mean(0)


def fit_warp(s_means, c_means):
    """a, b and the mean |g| of c(m) = g * s(a * m + b) + d over both classes, by grid search on the summed residual."""
    m = np.arange(LO, HI, dtype=float)
    k = np.arange(N_SRC, dtype=float)

    def fit(a, b):
        err, gains = 0.0, []
        for s_, c_ in zip(s_means, c_means):
            x = a * m + b
            ok = (x >= 0) & (x <= N_SRC - 1)
            s = np.interp(x[ok], k, s_.real) + 1j * np.interp(x[ok], k, s_.imag)
            A = np.vstack([s, np.ones_like(s)]).T
            sol, *_ = np.linalg.lstsq(A, c_[LO:HI][ok], rcond=None)
            err += np.mean(np.abs(c_[LO:HI][ok] - A @ sol) ** 2)
            gains.append(abs(sol[0]))
        return err, float(np.mean(gains))

    grid = [(fit(a, b)[0], a, b) for a in np.arange(0.985, 1.0101, 0.001) for b in np.arange(-12, 12.01, 0.25)]
    _, a0, b0 = min(grid)
    grid = [(fit(a, b)[0], a, b) for a in np.arange(a0 - 0.0015, a0 + 0.0015, 0.0001) for b in np.arange(b0 - 0.5, b0 + 0.501, 0.02)]
    _, a, b = min(grid)
    return float(a), float(b), fit(a, b)[1]


def main():
    X = np.load(SOURCE_X)
    y = np.load(LABELS).astype(int)
    raw = cplx(X)
    k2, c2 = complex(np.load(K2)), complex(np.load(C2))
    src_cal = k2 * raw + c2                               # the source under the loopback calibration, as channel_noise_v144.py
    bands = CN.BANDS
    out = {"f_interp_MHz": F_I, "dac_per_source_sample": DAC_PER_SRC, "dac_per_readout_sample": F_DAC / FS,
           "stretch_expected_a": (F_DAC / FS) / DAC_PER_SRC, "bands_MHz": bands, "reference_band_MHz": REF, "boards": {}}

    f = np.abs(np.fft.fftfreq(N_SRC, 1 / FS))
    out["interp_dB"] = rel_db(f, interp_power(f), bands)

    # simulation check of the formula, on the source traces' within-class noise (bands below 150 MHz: above it the
    # ideal band limit lets the interpolation's first image in)
    zs = raw[:N_SIM]
    p_in = seg_psd(within_class(zs, y[:N_SIM]))
    p_out = seg_psd(within_class(simulate(zs)[:, :N_SRC], y[:N_SIM]))
    f_in = np.fft.fftfreq(HI - LO) * F_I                 # source bins on the DAC's time axis
    f_out = np.fft.fftfreq(HI - LO) * FS
    o = np.argsort(f_in)
    T = p_out / np.interp(f_out, f_in[o], p_in[o])
    sim_bands = [bd for bd in bands if bd[1] <= 150]
    out["sim_check_dB"] = rel_db(np.abs(f_out), T, sim_bands)
    out["sim_check_formula_dB"] = rel_db(np.abs(f_out), interp_power(np.abs(f_out)), sim_bands)
    assert max(abs(p - q) for p, q in zip(out["sim_check_dB"], out["sim_check_formula_dB"])) < 0.5, out["sim_check_dB"]

    s_means = [raw[y == c].mean(0) for c in (0, 1)]
    noise_src = seg_psd(within_class(raw, y)).sum()
    for b in "AB":
        zl = cplx(np.load(str(REPLAY).format(b)))
        _, H, _ = CN.residual(src_cal[:CN.N_FIT], zl[:CN.N_FIT])
        ch = rel_db(f, np.abs(H) ** 2, bands)
        a, off, g = fit_warp(s_means, [zl[y == c].mean(0) for c in (0, 1)])
        noise = seg_psd(within_class(zl, y)).sum() / (g ** 2 * noise_src)
        res = {"channel_dB": ch,
               "interp_share": [i / c if c < -1 else None for i, c in zip(out["interp_dB"], ch)],
               "stretch_a": a, "stretch_b": off, "drift_over_fit_samples": (1 / a - 1) * (HI - LO),
               "gain_abs": g, "noise_power_ratio": float(noise), "noise_power_ratio_dB": float(10 * np.log10(noise))}
        out["boards"][b] = res
        print(b, "channel dB", [f"{x:+.1f}" for x in ch], "| interp dB", [f"{x:+.1f}" for x in out["interp_dB"]],
              f"| a {a:.4f} b {off:+.2f} drift {res['drift_over_fit_samples']:.1f} | noise {res['noise_power_ratio_dB']:+.2f} dB")
    p = HERE / "replay_interp_v144.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", p.name)


if __name__ == "__main__":
    main()
