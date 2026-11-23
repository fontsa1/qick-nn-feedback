"""Paired-comparison helpers for the revision2 statistics (balanced fidelity F = 1 - (P(1|0) + P(0|1))/2, in points).

paired_cmp(okA, okB, y)    A - B on the same shots: discordant counts, exact McNemar p (two-sided binomial), the paper's
                           normal interval (paired variance within each class, as r3_stats.paired), and a class-stratified
                           paired bootstrap (percentile) interval. Because F depends only on per-class discordant counts,
                           resampling the n_c rows of class c is a multinomial draw over (A-only, B-only, concordant):
                           exactly equivalent to resampling rows, and fast.
paired_cmp_cluster(...)    the same for two boards pooled (each row scored twice): the row is the resampling unit
                           (per-row value v = sum over boards of okA - okB, in {-2..2}); p from a stratified sign-flip
                           randomisation test on v (H0: A and B exchangeable within each row), 200,000 draws.
margin(ci)                 smallest symmetric equivalence margin the interval supports: max(|lo|, |hi|).
"""
import numpy as np
from math import comb, sqrt

Z95, Z90 = 1.959964, 1.644854
RNG = np.random.default_rng(20261116)
NB = 20000


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    # exact two-sided binomial; log-space sum for large n
    from scipy.stats import binomtest
    return float(binomtest(k, n, 0.5).pvalue)


def fid(pred, y):
    pred = np.asarray(pred).astype(int); y = np.asarray(y).astype(int)
    return 100 * (1 - 0.5 * (np.mean(pred[y == 0] != 0) + np.mean(pred[y == 1] != 1)))


def fid_ci(pred, y):
    pred = np.asarray(pred).astype(int); y = np.asarray(y).astype(int)
    p10 = np.mean(pred[y == 0] != 0); p01 = np.mean(pred[y == 1] != 1)
    F = 1 - 0.5 * (p10 + p01); se = 0.5 * sqrt(p10 * (1 - p10) / (y == 0).sum() + p01 * (1 - p01) / (y == 1).sum())
    return dict(fid=100 * F, ci95=[100 * (F - Z95 * se), 100 * (F + Z95 * se)], n=int(len(y)))


def paired_cmp(okA, okB, y, nb=NB):
    okA = np.asarray(okA, bool); okB = np.asarray(okB, bool); y = np.asarray(y).astype(int)
    b = int((okA & ~okB).sum()); c = int((okB & ~okA).sum())
    d, var = 0.0, 0.0; boot = np.zeros(nb)
    for cl in (0, 1):
        m = y == cl; n = int(m.sum())
        bc = int((okA[m] & ~okB[m]).sum()); cc = int((okB[m] & ~okA[m]).sum())
        x = okA[m].astype(int) - okB[m].astype(int)
        d += 0.5 * x.mean(); var += 0.25 * x.var() / n
        draws = RNG.multinomial(n, [bc / n, cc / n, 1 - (bc + cc) / n], size=nb)
        boot += 0.5 * (draws[:, 0] - draws[:, 1]) / n
    se = sqrt(var)
    r = dict(n=int(len(y)), A_only=b, B_only=c, p_exact=mcnemar_exact(b, c), dF=100 * d,
             ci95_normal=[100 * (d - Z95 * se), 100 * (d + Z95 * se)], ci90_normal=[100 * (d - Z90 * se), 100 * (d + Z90 * se)],
             ci95_boot=list(100 * np.percentile(boot, [2.5, 97.5])), ci90_boot=list(100 * np.percentile(boot, [5, 95])))
    r["margin95"] = margin(r["ci95_boot"]); r["margin90_TOST"] = margin(r["ci90_boot"])
    r["margin95_normal"] = margin(r["ci95_normal"])
    return r


def paired_cmp_cluster(okA_list, okB_list, y, nb=NB, nperm=200000):
    """okA_list / okB_list: per-board boolean arrays aligned on the same rows (same y)."""
    y = np.asarray(y).astype(int); K = len(okA_list)
    v = sum(np.asarray(a, int) - np.asarray(b, int) for a, b in zip(okA_list, okB_list))  # per row, in [-K, K]
    b = int(sum((np.asarray(a, bool) & ~np.asarray(bb, bool)).sum() for a, bb in zip(okA_list, okB_list)))
    c = int(sum((np.asarray(bb, bool) & ~np.asarray(a, bool)).sum() for a, bb in zip(okA_list, okB_list)))
    d, var = 0.0, 0.0; boot = np.zeros(nb); perm = np.zeros(nperm)
    vals = np.arange(-K, K + 1)
    for cl in (0, 1):
        vc = v[y == cl]; n = len(vc)
        d += 0.5 * vc.mean() / K; var += 0.25 * (vc / K).var() / n
        cnt = np.array([(vc == t).sum() for t in vals])
        draws = RNG.multinomial(n, cnt / n, size=nb)
        boot += 0.5 * (draws @ vals) / n / K
        # sign-flip: each nonzero |v| row flips sign with prob 1/2
        for a in range(1, K + 1):
            m_a = int((np.abs(vc) == a).sum())
            if m_a:
                pos = RNG.binomial(m_a, 0.5, size=nperm)
                perm += 0.5 * a * (2 * pos - m_a) / n / K
    se = sqrt(var)
    p_perm = float((np.sum(np.abs(perm) >= abs(d) - 1e-15) + 1) / (nperm + 1))
    r = dict(n_rows=int(len(y)), n_shots=int(K * len(y)), A_only=b, B_only=c, dF=100 * d,
             p_signflip=p_perm, p_exact_naive_summed=mcnemar_exact(b, c),
             ci95_normal_cluster=[100 * (d - Z95 * se), 100 * (d + Z95 * se)],
             ci95_boot=list(100 * np.percentile(boot, [2.5, 97.5])), ci90_boot=list(100 * np.percentile(boot, [5, 95])))
    r["margin95"] = margin(r["ci95_boot"]); r["margin90_TOST"] = margin(r["ci90_boot"])
    return r


def margin(ci):
    return float(max(abs(ci[0]), abs(ci[1])))


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()
