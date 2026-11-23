"""Leakage audit: re-derives every link between the data files from the raw bytes and checks, in seven sets:
  A  the training and test pools share no row;
  B  the 20,000-row subset is exactly the indexed rows of the test split, with their labels, and none is in the training pool;
  C  the domain maps were fit on test rows 1000:1600; every scored set, read from the v1.44 per-shot files, indexes the
     test split once and is disjoint from those rows; the reported fidelities are those of the sets without them;
  D  every row of both mapped training files (FIR path, NN_axi; boxcar path, NN_live) equals the recorded map applied to
     its raw row, and no row equals, within 1e-3, a test row raw or through the same map;
  E  the synthetic generator's fit pool is disjoint from the training rows and from the whole test split;
  F  the deployed map coefficients equal the label-free fit on their recorded capture, not the per-class fit;
  G  the 100,000-row replay set matches its manifest, starts with the subset, and the v1.44 runs cover every row once.
Every check prints what it tests. A check whose inputs are missing is recorded BLOCKED (download Zenodo record 14427490
into the repository root for the dataset arrays; DATA_MANIFEST.csv lists the rest). Run from the repository root:
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

CHUNK = 20000
TRAIN_RANGES = [(0, 10000), (110000, 300000)]
TRAIN_N = sum(h - l for l, h in TRAIN_RANGES)
GEN_FIT_LO, GEN_FIT_HI = 10000, 110000
CALIB_SLICE = (1000, 1600)
BOX_MAP = "calibration/box_domain_map.json"
T100 = "data/test100k_real"
V144 = "campaign_v144/final/"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "analysis_scripts" / "acquisition"))
import build_box_training_set as BB  # noqa: E402  (cz, ma, fshift, fit: the builder's own map code)

results = []

def record(name, ok, detail="", pass_detail="", tests=""):
    st = "BLOCKED" if ok is None else ("PASS" if ok else "**FAIL**")
    results.append((name, ok, detail, tests))
    shown = pass_detail if ok else detail
    print(f"  [{st}] {name}" + (f"  -- {shown}" if shown else ""), flush=True)
    if tests:
        print(f"           tests: {tests}", flush=True)

def need(*paths):
    miss = [p for p in paths if not Path(p).exists()]
    return miss

def row_hashes(a):
    a = np.ascontiguousarray(a)
    return [hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in a]

def hash_file_rows(path, limit=None):
    A = np.load(path, mmap_mode="r")
    n = A.shape[0] if limit is None else min(limit, A.shape[0])
    out = set()
    for i in range(0, n, CHUNK):
        out.update(row_hashes(np.asarray(A[i:min(i + CHUNK, n)])))
    return out, A.shape

def fstats(pred, y):
    pred = np.asarray(pred).astype(int); y = np.asarray(y).astype(int)
    p10 = np.mean(pred[y == 0] != 0); p01 = np.mean(pred[y == 1] != 1)
    return 100 * (1 - 0.5 * (p10 + p01))

# ----------------------------------------------------------------------------------------------- maps
def fir_map(Xblk, k2, c2):
    z = BB.cz(Xblk); w = k2 * z + c2
    out = np.empty(Xblk.shape, np.float32); out[:, 0::2] = w.real; out[:, 1::2] = w.imag
    return out

def box_map(Xblk, bm):
    kb, cb, s, M, prime = complex(*bm["k"]), complex(*bm["c"]), bm["shift"], int(bm["m"]), complex(*bm["prime"])
    z = kb * BB.fshift(BB.ma(BB.cz(Xblk), M, prime), s) + cb
    out = np.empty(Xblk.shape, np.float32); out[:, 0::2] = z.real; out[:, 1::2] = z.imag
    return out

# ----------------------------------------------------------------------------------------------- D3 search
RNG_W = None

def fingerprints(X):
    """Two scalar fingerprints per row (mean, and mean with random +-1 weights); each moves by at most max|dx|."""
    global RNG_W
    if RNG_W is None or len(RNG_W) != X.shape[1]:
        RNG_W = np.random.default_rng(12345).choice([-1.0, 1.0], X.shape[1])
    X = np.asarray(X, np.float64)
    return X.mean(1), (X @ RNG_W) / X.shape[1]

def near_duplicate_search(train_path, refs, tol, label, train_rows=None):
    """refs: dict name -> float32 array of reference rows (test rows, mapped or raw). Returns list of hits
    (train row, ref name, ref row, max abs diff) for every training-file row within tol of a reference row."""
    T = np.load(train_path, mmap_mode="r")
    n = T.shape[0] if train_rows is None else train_rows
    prep = {}
    for nm, R in refs.items():
        f1, f2 = fingerprints(R); o = np.argsort(f1)
        prep[nm] = (R, f1[o], f2[o], o)
    hits, ncand = [], 0
    for i in range(0, n, CHUNK):
        blk = np.asarray(T[i:min(i + CHUNK, n)], np.float32)
        g1, g2 = fingerprints(blk)
        for nm, (R, f1s, f2s, o) in prep.items():
            lo = np.searchsorted(f1s, g1 - tol, "left"); hi = np.searchsorted(f1s, g1 + tol, "right")
            cnt = hi - lo
            if cnt.sum() == 0:
                continue
            qi = np.repeat(np.arange(len(blk)), cnt)
            ri = np.concatenate([np.arange(l, h) for l, h in zip(lo[cnt > 0], hi[cnt > 0])])
            keep = np.abs(g2[qi] - f2s[ri]) <= tol
            qi, ri = qi[keep], ri[keep]; ncand += len(qi)
            for q, r in zip(qi, ri):
                d = float(np.max(np.abs(blk[q] - R[o[r]])))
                if d <= tol:
                    hits.append((int(i + q), nm, int(o[r]), d))
    print(f"     D3 {label}: {n} training rows searched against " + ", ".join(f"{k} ({len(v)} rows)" for k, v in refs.items())
          + f"; tol {tol:.3g}; {ncand} candidate pairs after fingerprints; {len(hits)} hits", flush=True)
    return hits

def d3_refs(kind, k2=None, c2=None, bm=None):
    Xte = np.load("0528_X_test_0_770.npy", mmap_mode="r")
    mapped = np.empty(Xte.shape, np.float32); raw = np.empty(Xte.shape, np.float32)
    for i in range(0, Xte.shape[0], CHUNK):
        b = np.asarray(Xte[i:i + CHUNK])
        mapped[i:i + len(b)] = fir_map(b, k2, c2) if kind == "fir" else box_map(b, bm)
        raw[i:i + len(b)] = b.astype(np.float32)
    return {"test rows through the same map": mapped, "raw test rows": raw}

def d3_selftest(src_path, out_path, bm, n=CHUNK):
    """Corrupted temp copy: first n rows of the boxcar training file, with row 7 replaced by test row 5 through the
    boxcar map and row 12345 by raw test row 77. D3 must flag both; an exact row-hash comparison across dtypes does not."""
    S = np.load(src_path, mmap_mode="r")
    C = np.lib.format.open_memmap(out_path, mode="w+", dtype=S.dtype, shape=(n, S.shape[1]))
    C[:] = S[:n]
    Xte = np.load("0528_X_test_0_770.npy", mmap_mode="r")
    C[7] = box_map(np.asarray(Xte[5:6]), bm)[0]
    C[12345] = np.asarray(Xte[77], np.float32)
    C.flush(); del C
    return {7: ("test rows through the same map", 5), 12345: ("raw test rows", 77)}

# ----------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d3-selftest", action="store_true", help="run only the D3 failure demonstration")
    ap.add_argument("--tmp", default="build/tmp")
    ap.add_argument("--skip-fir-d", action="store_true")
    a = ap.parse_args()
    print(__doc__)
    print("=" * 74)
    bm = json.load(open(BOX_MAP)) if Path(BOX_MAP).exists() else None

    if a.d3_selftest:
        Path(a.tmp).mkdir(parents=True, exist_ok=True)
        tmp = Path(a.tmp) / "corrupted_box_train_head20000.npy"
        planted = d3_selftest("0528_X_train_box_calibrated.npy", tmp, bm)
        print(f"planted: {planted} in {tmp}")
        refs = d3_refs("box", bm=bm)
        hits = near_duplicate_search(tmp, refs, 1e-3, "corrupted copy (D3)")
        found = {h[0]: (h[1], h[2]) for h in hits}
        record(f"D3 {tmp.name} (deliberately corrupted): no row equals a test row, raw or through the same map", len(hits) == 0,
               f"{len(hits)} hits: {hits}", pass_detail="0 hits", tests="D3 itself, run on the corrupted copy: it must FAIL here")
        record("D3-selftest D3 flags both planted test rows in the corrupted copy (so this run FAILS D3)",
               found == planted, f"hits {hits}, planted {planted}", pass_detail=f"hits {hits}",
               tests="D3 can fail: it finds a mapped test row and a raw test row planted in a training file")
        h_test, _ = hash_file_rows("0528_X_test_0_770.npy")
        h_c, _ = hash_file_rows(tmp)
        record("D3-selftest an exact row-hash comparison across dtypes reports no hit on the same copy (it cannot fail)",
               len(h_c & h_test) == 0, f"{len(h_c & h_test)} hits", pass_detail="0 hits although 2 test rows are planted",
               tests="blake2b of float32 rows against blake2b of float64 rows is disjoint by construction, which is why D3 compares values")
        tmp.unlink()
        print(f"\nD3 self-test: D3 {'FAILS (as it must)' if found == planted else 'MISSED a planted row'}; corrupted copy deleted")
        return 0 if all(ok for _, ok, _, _ in results[1:]) and results[0][1] is False else 1

    # ---------- inputs up front ----------
    INPUTS = {
        "A": ["0528_X_train_0_770.npy", "0528_X_test_0_770.npy"],
        "B": ["data/test20k_real_manifest.json", "0528_y_test_0_770.npy", "data/test20k_real_X.npy", "data/test20k_real_y.npy"],
        "C": ["data/domain_calib_raw_X.npy", BOX_MAP, "campaign_v144/final/analysis/v144_stats.json"],
        "G": [f"{T100}_manifest.json", f"{T100}_X.npy", f"{T100}_y.npy"],
        "D": ["0528_X_train_0_770_loopback_calibrated.npy", "calibration/k2_loopback.npy", "calibration/c2_loopback.npy",
              "0528_X_train_box_calibrated.npy", "0528_X_train_box_calibrated_rows.npy"],
        "E": ["x_synth_v2.npy"],
        "F": ["data/domain_calib_acquired.npy", "data/domain_calib_y.npy"],
    }
    if bm:
        INPUTS["F"] += bm["captures"]
    blocked = {k: need(*v) for k, v in INPUTS.items()}
    print("inputs:", {k: ("ok" if not v else f"MISSING {v}") for k, v in blocked.items()})
    for k, v in blocked.items():
        if v:
            record(f"{k}* (all checks of set {k})", None, f"missing inputs {v}")

    if not blocked["A"]:
        print("\nA. train pool vs held-out test pool (raw row bytes, every row)")
        h_test, sh_test = hash_file_rows("0528_X_test_0_770.npy")
        h_train, sh_train = hash_file_rows("0528_X_train_0_770.npy")
        print(f"     train {sh_train} unique rows {len(h_train)}; test {sh_test} unique rows {len(h_test)}")
        record("A1 train pool and test pool are disjoint", len(h_train & h_test) == 0, f"{len(h_train & h_test)} shared",
               tests="the paper's audit set (A), exact byte equality of rows")

    if not blocked["B"] and not blocked["A"]:
        print("\nB. test20k_real_X provenance")
        man = json.load(open("data/test20k_real_manifest.json"))
        idx = np.asarray(man["source_indices"], np.int64)
        rec = hashlib.sha256(idx.tobytes()).hexdigest()
        record("B1 manifest index checksum is self-consistent", rec == man["source_indices_sha256"], rec[:16],
               tests="the paper's audit set (B) the recorded index list is the one the manifest hashed")
        Xs = np.load("0528_X_test_0_770.npy", mmap_mode="r"); ys = np.load("0528_y_test_0_770.npy")
        X20 = np.load("data/test20k_real_X.npy", mmap_mode="r"); y20 = np.load("data/test20k_real_y.npy")
        record("B2 test20k row count matches manifest", X20.shape[0] == man["n"] == len(idx) == len(np.unique(idx)))
        xs_ok = all(np.array_equal(np.asarray(X20[i:i + CHUNK]), np.asarray(Xs[idx[i:i + CHUNK]])) for i in range(0, len(idx), CHUNK))
        record("B3 test20k X rows are exactly 0528_X_test[source_indices], all 20,000 rows", xs_ok,
               tests="the paper's audit set (B) 'exactly the indexed rows'")
        record("B4 test20k labels equal 0528_y_test[source_indices], all rows", bool(np.array_equal(y20.astype(int), ys[idx].astype(int))),
               tests="the paper's audit set (B) 'with their labels'")
        h20 = set(row_hashes(np.asarray(X20)))
        record("B5 no test20k shot appears in the train pool", len(h20 & h_train) == 0, f"{len(h20 & h_train)} shared",
               tests="the paper's audit set (B) 'none of them is in the training pool'")

    lo, hi = CALIB_SLICE
    if not blocked["C"] and blocked["B"]:
        record("C* (all checks of set C)", None, f"depends on set B's inputs {blocked['B']}")
    if not blocked["C"] and not blocked["B"]:
        print("\nC. map-fit rows vs the v1.44 scored sets")
        dc_raw = np.load("data/domain_calib_raw_X.npy", mmap_mode="r")
        record(f"C1 domain_calib_raw_X (the FIR map's fit input) is test20k_real_X[{lo}:{hi}]",
               bool(np.array_equal(np.asarray(dc_raw), np.asarray(X20[lo:hi]))), tests="the paper's audit set (C) the (k2, c2) fit rows")
        record(f"C2 box_domain_map.json records calib_rows {lo}:{hi}", bm.get("calib_rows") == f"{lo}:{hi}", repr(bm.get("calib_rows")),
               tests="the paper's audit set (C) the boxcar map's fit rows, as recorded (F2 refits it from the capture)")
        y100 = np.load(f"{T100}_y.npy").astype(int)
        sets, lines, ok = {}, [], True
        import glob
        for b in "AB":
            for nm, pat, key in ((f"NN_axi v1.44 board {b}", f"{V144}axi/{b}_axi_*.npz", "idx"),
                                 (f"NN_live v1.44 run 1 board {b}", f"{V144}live/{b}_run1_*.npz", "rows"),
                                 (f"NN_live v1.44 run 2 board {b}", f"{V144}live/{b}_run2_*.npz", "rows"),
                                 (f"in-loop v1.44 board {b}", f"{V144}inloop/{b}_inloop_0_100000.npz", "rows")):
                fs = sorted(glob.glob(pat))
                if not fs:
                    lines.append(f"{nm}: no files {pat}"); ok = False; continue
                R, Y = [], []
                for f in fs:
                    z = np.load(f, allow_pickle=True)
                    n = int(z["n_done"]) if "n_done" in z.files else len(z[key])
                    R.append(np.asarray(z[key][:n], np.int64)); Y.append(np.asarray(z["y"][:n]).astype(int))
                r, y = np.concatenate(R), np.concatenate(Y)
                good = len(np.unique(r)) == len(r) and r.min() >= 0 and r.max() < len(y100) and np.array_equal(y100[r], y)
                ok &= good; sets[nm] = r
                lines.append(f"{nm}: {len(fs)} files, {len(r)} rows [{r.min()}..{r.max()}], each once {len(np.unique(r)) == len(r)}, "
                             f"labels == test split {np.array_equal(y100[r], y)}, map-fit rows inside {int(((r >= lo) & (r < hi)).sum())}")
        for s in lines:
            print("     " + s)
        record("C3 every v1.44 per-shot file indexes test rows once with the test split's labels", ok, "; ".join(lines),
               tests="the paper's audit set (C) 'every scored set, read from the per-shot result files themselves'")
        X100 = np.load(f"{T100}_X.npy", mmap_mode="r")
        h_fit = set(row_hashes(np.asarray(dc_raw))) | set(row_hashes(np.asarray(X100[lo:hi])))
        h_head = set()
        for i in range(0, X100.shape[0], CHUNK):
            keep = [k for k in range(i, min(i + CHUNK, X100.shape[0])) if not lo <= k < hi]
            h_head.update(row_hashes(np.asarray(X100[keep])))
        record("C4 no row outside 1000:1600 has the content of a map-fit row", len(h_head & h_fit) == 0, f"{len(h_head & h_fit)} shared",
               tests="the paper's audit set (C) disjointness by content, so a duplicate trace elsewhere in the split would be caught")
        # C5: the reported numbers are the masked sets
        st = json.load(open("campaign_v144/final/analysis/v144_stats.json"))
        def live(b, run):
            fs = sorted(glob.glob(f"{V144}live/{b}_run{run}_*.npz")); R, Y, D = [], [], []
            for f in fs:
                z = np.load(f); R.append(z["rows"]); Y.append(z["y"]); D.append(z["live_rec"][:, 7] & 1)
            r = np.concatenate(R); o = np.argsort(r)
            return r[o], np.concatenate(Y)[o].astype(int), np.concatenate(D)[o].astype(int)
        L = {(b, r): live(b, r) for b in "AB" for r in (1, 2)}
        def join(p, q):
            r = np.concatenate([p[0], q[0]]); o = np.argsort(r)
            return r[o], np.concatenate([p[1], q[1]])[o], np.concatenate([p[2], q[2]])[o]
        A_, B_, H_ = join(L[("A", 1)], L[("A", 2)]), join(L[("B", 2)], L[("B", 1)]), join(L[("A", 1)], L[("B", 1)])
        cm = lambda r: ~((r >= lo) & (r < hi))
        mine = {"live/headline": fstats(H_[2][cm(H_[0])], H_[1][cm(H_[0])]), "live/A_all": fstats(A_[2][cm(A_[0])], A_[1][cm(A_[0])]),
                "live/B_all": fstats(B_[2][cm(B_[0])], B_[1][cm(B_[0])])}
        nmask = {k: int(cm(v[0]).sum()) for k, v in (("live/headline", H_), ("live/A_all", A_), ("live/B_all", B_))}
        for b in "AB":
            fs = sorted(glob.glob(f"{V144}axi/{b}_axi_*.npz")); I, P, Y = [], [], []
            for f in fs:
                z = np.load(f, allow_pickle=True); I.append(z["idx"]); P.append(z["probs"]); Y.append(z["y"])
            r = np.concatenate(I); o = np.argsort(r); r, p, y = r[o], np.concatenate(P)[o], np.concatenate(Y)[o].astype(int)
            mine[f"axi/{b}/subset19400"] = fstats((p[cm(r)] > 0.5).astype(int), y[cm(r)]); nmask[f"axi/{b}/subset19400"] = int(cm(r).sum())
            r_in = sets[f"in-loop v1.44 board {b}"]
            mine[f"inloop rows inside 1000:1600, board {b}"] = int(((r_in >= lo) & (r_in < hi)).sum())
        ledg = {"live/headline": st["live"]["headline"]["fid"], "live/A_all": st["live"]["A_all"]["fid"], "live/B_all": st["live"]["B_all"]["fid"],
                "axi/A/subset19400": st["axi"]["A"]["subset19400"]["fid"], "axi/B/subset19400": st["axi"]["B"]["subset19400"]["fid"]}
        diffs = {k: (round(mine[k], 4), round(v, 4), nmask[k]) for k, v in ledg.items()}
        print("     re-derived (masked) vs v144_stats.json, n:", diffs)
        print("     in-loop:", {k: v for k, v in mine.items() if k.startswith("inloop")})
        okc5 = all(abs(mine[k] - v) < 1e-9 for k, v in ledg.items()) and all(mine[f"inloop rows inside 1000:1600, board {b}"] == 0 for b in "AB")
        record("C5 the v1.44 headline numbers (95.60, 95.55, 95.62, NN_axi 95.55/95.45) are the fidelities of the per-shot sets with rows 1000:1600 removed; the in-loop runs never replay those rows",
               okc5, str(diffs), pass_detail="all equal to 1e-9; in-loop rows inside the slice: 0 and 0",
               tests="the paper's audit set (C)/(G) that the scored sets that carry the reported numbers exclude the map rows")

        print("\nG. test100k_real (the full split replayed for NN_live)")
        man = json.load(open(f"{T100}_manifest.json")); idx100 = np.asarray(man["source_indices"], np.int64)
        hx = hashlib.sha256()
        for i in range(0, X100.shape[0], CHUNK):
            hx.update(np.ascontiguousarray(X100[i:i + CHUNK]).tobytes())
        record("G1 test100k_real_X / _y match the manifest sha256", hx.hexdigest() == man["sha256_X"] and
               hashlib.sha256(np.ascontiguousarray(np.load(f"{T100}_y.npy")).tobytes()).hexdigest() == man["sha256_y"],
               tests="the paper's audit set (G) 'matches its manifest'")
        rows_ok = all(np.array_equal(np.asarray(X100[i:i + CHUNK]), np.asarray(Xs[idx100[i:i + CHUNK]])) for i in range(0, len(idx100), CHUNK))
        record("G2 test100k_real is 0528_X_test[source_indices], every row and label, indices unique",
               rows_ok and len(np.unique(idx100)) == 100000 and np.array_equal(y100, ys[idx100].astype(int)), tests="the paper's audit set (G)")
        record("G3 its rows 0..19,999 are test20k_real in the same order", bool(np.array_equal(np.asarray(X100[:20000]), np.asarray(X20))),
               tests="the paper's audit set (G) 'its first 20,000 rows are the subset'")
        h100 = set()
        for i in range(0, X100.shape[0], CHUNK):
            h100.update(row_hashes(np.asarray(X100[i:i + CHUNK])))
        record("G4 no test100k_real shot is in the train pool", len(h100 & h_train) == 0, f"{len(h100 & h_train)} shared")
        cover = all(np.array_equal(np.sort(np.concatenate([sets[f"NN_live v1.44 run 1 board {b}"], sets[f"NN_live v1.44 run 2 board {b}"]])),
                                   np.arange(100000)) for b in "AB")
        record("G5 v1.44: each board's NN_live runs 1 + 2 cover every test100k row exactly once; headline set (rows 1000:1600 removed) "
               "shares no content with the map-fit rows (C4)", cover and len(h_head & h_fit) == 0,
               tests="the paper's audit set (G) 'the NN_live headline set shares no row with the map rows', on the v1.44 runs")

    if not blocked["D"] and not blocked["A"]:
        print("\nD. the mapped training files the deployed models consume")
        k2 = complex(np.load("calibration/k2_loopback.npy")); c2 = complex(np.load("calibration/c2_loopback.npy"))
        Xraw = np.load("0528_X_train_0_770.npy", mmap_mode="r")
        Xcal = np.load("0528_X_train_0_770_loopback_calibrated.npy", mmap_mode="r")
        record("D1 FIR-path file has the train pool's row count and width", Xcal.shape == Xraw.shape, f"{Xcal.shape} vs {Xraw.shape}")
        tol_rel = 4 * np.finfo(np.float32).eps
        if not a.skip_fir_d:
            worst, nexact, nbad = 0.0, 0, 0
            for i in range(0, Xcal.shape[0], CHUNK):
                ref = fir_map(np.asarray(Xraw[i:i + CHUNK]), k2, c2); got = np.asarray(Xcal[i:i + CHUNK])
                d = np.abs(got - ref).max(1); scale = np.abs(ref).max(1)
                worst = max(worst, float(d.max())); nexact += int((d == 0).sum()); nbad += int((d > tol_rel * scale + 1e-6).sum())
            record("D2 FIR-path file (NN_axi): every one of 900,000 rows == k2*raw_row + c2 (recorded k2, c2), to float32 rounding",
                   nbad == 0, f"{nbad} rows off; worst {worst:.3g}",
                   pass_detail=f"worst abs deviation {worst:.3g}; {nexact} of {Xcal.shape[0]} rows bit-identical to the recomputation",
                   tests="the paper's audit set (D) 'each mapped training row equals the map applied to its raw row' for the FIR path")
        Xb = np.load("0528_X_train_box_calibrated.npy", mmap_mode="r"); rb = np.load("0528_X_train_box_calibrated_rows.npy")
        src = np.concatenate([np.arange(l, h) for l, h in TRAIN_RANGES])
        record("D1b boxcar-path file (NN_live) has 200,000 rows whose recorded source rows are 0:10000 + 110000:300000 of the train pool",
               Xb.shape == (TRAIN_N, Xraw.shape[1]) and np.array_equal(rb, src), f"{Xb.shape}, rows equal {np.array_equal(rb, src)}",
               tests="the paper's audit set (D) for the file NN_live trains on")
        worst, nexact, nbad = 0.0, 0, 0
        for i in range(0, len(src), CHUNK):
            ref = box_map(np.asarray(Xraw[src[i:i + CHUNK]]), bm); got = np.asarray(Xb[i:i + CHUNK])
            d = np.abs(got - ref).max(1); scale = np.abs(ref).max(1)
            worst = max(worst, float(d.max())); nexact += int((d == 0).sum()); nbad += int((d > tol_rel * scale + 1e-6).sum())
        record("D2b boxcar-path file (NN_live): every one of 200,000 rows == kb*MA_M(raw)[n-s] + cb with box_domain_map.json's coefficients",
               nbad == 0, f"{nbad} rows off; worst {worst:.3g}",
               pass_detail=f"worst abs deviation {worst:.3g}; {nexact} of {len(src)} rows bit-identical to the recomputation",
               tests="the paper's audit set (D) for NN_live's map")
        print("     D3: mapping the 100,000 test rows through each map and searching each training file for them")
        for kind, path, nrows in (("box", "0528_X_train_box_calibrated.npy", None), ("fir", "0528_X_train_0_770_loopback_calibrated.npy", None)):
            if kind == "fir" and a.skip_fir_d:
                continue
            refs = d3_refs(kind, k2, c2, bm)
            hits = near_duplicate_search(path, refs, 1e-3, path, nrows)
            record(f"D3 {path}: no row equals (max abs diff <= 1e-3) a test row, raw or through the same map", len(hits) == 0,
                   f"{len(hits)} hits: {hits[:5]}", pass_detail="0 hits",
                   tests="the paper's audit set (D) 'none equals a test row', in the training file's own dtype and domain; can fail (see --d3-selftest)")
            del refs

    if not blocked["E"] and not blocked["A"] and not blocked["B"]:
        print("\nE. synthetic generator fit pool (0528_X_train_0_770[10000:110000])")
        Atr = np.load("0528_X_train_0_770.npy", mmap_mode="r")
        h_tr, h_fitp = set(), set()
        for l, h in TRAIN_RANGES:
            for i in range(l, h, CHUNK):
                h_tr.update(row_hashes(np.asarray(Atr[i:min(i + CHUNK, h)])))
        for i in range(GEN_FIT_LO, GEN_FIT_HI, CHUNK):
            h_fitp.update(row_hashes(np.asarray(Atr[i:min(i + CHUNK, GEN_FIT_HI)])))
        record(f"E1 generator fit pool vs the {TRAIN_N:,} training rows", len(h_fitp & h_tr) == 0, tests="the paper's audit set (E)")
        record("E2 generator fit pool vs the 20k test subset", len(h_fitp & h20) == 0, tests="the paper's audit set (E)")
        record("E2b generator fit pool vs all 100k test rows", len(h_fitp & h_test) == 0, tests="the paper's audit set (E), the full split (new)")
        record("E4 fit pool = gap between the training ranges", (GEN_FIT_LO, GEN_FIT_HI) == (TRAIN_RANGES[0][1], TRAIN_RANGES[1][0]),
               tests="constants only: the generator script's actual slice is not read")
        record("E3 x_synth_v2.npy exists", Path("x_synth_v2.npy").exists(), tests="file existence only")

    if not blocked["F"] and not blocked["C"]:
        print("\nF. label use in the map fits")
        dc_acq = np.load("data/domain_calib_acquired.npy"); z_acq = BB.cz(dc_acq); z_raw = BB.cz(np.asarray(dc_raw))
        sol, *_ = np.linalg.lstsq(np.vstack([z_raw.mean(0), np.ones(z_raw.shape[1])]).T, z_acq.mean(0), rcond=None)
        yy = np.load("data/domain_calib_y.npy").astype(int)
        Ast = np.concatenate([z_raw[yy == 0].mean(0), z_raw[yy == 1].mean(0)]); Bst = np.concatenate([z_acq[yy == 0].mean(0), z_acq[yy == 1].mean(0)])
        sol2, *_ = np.linalg.lstsq(np.vstack([Ast, np.ones_like(Ast)]).T, Bst, rcond=None)
        k2 = complex(np.load("calibration/k2_loopback.npy")); c2 = complex(np.load("calibration/c2_loopback.npy"))
        d_free = abs(k2 - sol[0]) + abs(c2 - sol[1]) / abs(sol[1]); d_lab = abs(k2 - sol2[0]) + abs(c2 - sol2[1]) / abs(sol2[1])
        record("F1 FIR-path (k2, c2) equals the label-free fit, not the per-class one", d_free < 1e-6 and d_lab > 1e-3,
               f"distance free {d_free:.2e}, per-class {d_lab:.2e}", pass_detail=f"distance label-free {d_free:.1e}, per-class {d_lab:.2e}",
               tests="the paper's audit set (F) for NN_axi's map")
        caps = []
        for f in bm["captures"]:
            c = dict(np.load(f))
            if "rows" not in c:
                n = int(c["done"]); c["rows"] = int(c["start"]) + np.arange(n); c["box"] = c["box"][:n]
            caps.append(c)
        rows = np.concatenate([c["rows"] for c in caps]); box = np.concatenate([c["box"] for c in caps])
        sel = (rows >= lo) & (rows < hi)
        zr, za = BB.cz(np.asarray(X20)[rows[sel]]), BB.cz(box[sel])
        M, prime = int(bm["m"]), complex(*bm["prime"])
        e, s, kb, cb = BB.fit(zr.mean(0), za.mean(0), M, prime)
        ylab = np.asarray(y20)[rows[sel]].astype(int)
        # per-class variant: stack the two class-mean trajectories (uses the test file's labels)
        f0 = BB.ma(np.stack([zr[ylab == 0].mean(0), zr[ylab == 1].mean(0)]), M, prime)
        best = None
        for sh in np.arange(-12, 12.01, 0.25):
            g = BB.fshift(f0, sh)[:, 8:760].ravel(); tgt = np.stack([za[ylab == 0].mean(0), za[ylab == 1].mean(0)])[:, 8:760].ravel()
            A_ = np.vstack([g, np.ones_like(g)]).T; so, *_ = np.linalg.lstsq(A_, tgt, rcond=None)
            r_ = float(np.sqrt(np.mean(np.abs(tgt - A_ @ so) ** 2)))
            if best is None or r_ < best[0]:
                best = (r_, sh, complex(so[0]), complex(so[1]))
        same = abs(kb - complex(*bm["k"])) < 1e-9 and abs(cb - complex(*bm["c"])) < 1e-6 and s == bm["shift"]
        dpc = abs(best[2] - complex(*bm["k"])) + abs(best[3] - complex(*bm["c"])) / abs(complex(*bm["c"]))
        record("F2 boxcar-path map (NN_live) equals the label-free refit from its recorded capture (rows 1000:1600), not the per-class fit",
               same and dpc > 1e-3, f"refit k {kb:.6f} c {cb:.4f} s {s}; per-class k {best[2]:.6f} c {best[3]:.4f} s {best[1]}",
               pass_detail=f"{int(sel.sum())} shots; label-free refit identical (k {kb:.5f}, s {s:+.2f}); per-class fit k {best[2]:.5f} c {best[3]:.3f} s {best[1]:+.2f} differs (distance {dpc:.3f})",
               tests="P189/the paper's audit set (F) 'the deployed map coefficients equal the label-free fit, not the per-class one', for NN_live")

    print("\n" + "=" * 74)
    n_fail = sum(1 for _, ok, _, _ in results if ok is False); n_blk = sum(1 for _, ok, _, _ in results if ok is None)
    for name, ok, _, _ in results:
        print(f"  {'BLOCKED' if ok is None else ('PASS ' if ok else 'FAIL ')} {name}")
    print("=" * 74)
    n_sets = sum(1 for name, *_ in results if "* (all checks of set" in name)
    print(f"VERDICT: {len(results) - n_fail - n_blk}/{len(results)} checks passed, {n_fail} failed, {n_blk} blocked"
          + (f" ({n_sets} of the 7 sets blocked whole; the full audit has 29 checks)" if n_sets else ""))
    return 0 if n_fail == 0 and n_blk == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
