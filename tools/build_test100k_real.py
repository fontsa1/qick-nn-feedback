"""Builder for data/test100k_real_X.npy / _y.npy from the public dataset arrays alone.

Inputs (public test split of the reference dataset of [16], Zenodo record 14427490): 0528_X_test_0_770.npy, 0528_y_test_0_770.npy.
Recipe (the one that wrote the shipped files; step 1 is tools/make_test_subsets.py's):
  1. test20k_real indices: default_rng(20260902); for class 0 then class 1, rng.choice(where(y == s), 10000,
     replace=False); concatenate; rng.shuffle  (make_test_subsets.build, seed 20260902, n 20000)
  2. the other 80,000 rows: default_rng(20261022).permutation(setdiff1d(arange(100000), i20))
  3. idx = [i20, rest]; X = X_test[idx] as float64 (the source dtype), y = y_test[idx]; np.save both.
Step 1 is re-derived from the seed and checked against data/test20k_real_manifest.json's source_indices (and its
sha256); --use-manifest-20k takes them from the manifest instead. The X file is streamed in 20,000-row blocks so the
1.23 GB array is never held in RAM. With --check it compares the sha256 of every output (whole .npy file bytes and
array bytes) and the source_indices with data/test100k_real_manifest.json and with the shipped files.

      test20k_real_manifest.json, test100k_real_manifest.json> --out <dir> [--check <dir with shipped test100k_real_X.npy>]
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

SEED20, SEED_REST, N20 = 20260902, 20261022, 20000

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()

def subset20k_indices(y, n=N20, seed=SEED20):
    rng = np.random.default_rng(seed)
    idx = np.concatenate([rng.choice(np.where(y == s)[0], size=n // 2, replace=False) for s in (0, 1)])
    rng.shuffle(idx)
    return idx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir", required=True)
    ap.add_argument("--manifest-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", default=None)
    ap.add_argument("--use-manifest-20k", action="store_true")
    a = ap.parse_args()
    src, md, out = Path(a.src_dir), Path(a.manifest_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    Xs = np.load(src / "0528_X_test_0_770.npy", mmap_mode="r")
    ys = np.load(src / "0528_y_test_0_770.npy")
    rep = dict(inputs={f: sha_file(src / f) for f in ("0528_X_test_0_770.npy", "0528_y_test_0_770.npy")})
    man20 = json.load(open(md / "test20k_real_manifest.json"))
    i20_man = np.asarray(man20["source_indices"], dtype=np.int64)
    i20 = subset20k_indices(ys.astype(int))
    rep["i20_from_seed_equals_manifest"] = bool(np.array_equal(i20.astype(np.int64), i20_man))
    rep["i20_manifest_sha256_ok"] = hashlib.sha256(i20_man.tobytes()).hexdigest() == man20["source_indices_sha256"]
    if a.use_manifest_20k or not rep["i20_from_seed_equals_manifest"]:
        i20 = i20_man
    i20 = i20.astype(np.int64)
    rest = np.random.default_rng(SEED_REST).permutation(np.setdiff1d(np.arange(len(ys)), i20))
    idx = np.concatenate([i20, rest])
    assert len(idx) == len(ys) == 100_000 and len(np.unique(idx)) == len(idx)

    # stream X (same header np.save writes for a C-ordered float64 (100000, 1540) array)
    fx = out / "test100k_real_X.npy"
    mm = np.lib.format.open_memmap(fx, mode="w+", dtype=Xs.dtype, shape=(len(idx), Xs.shape[1]))
    ha = hashlib.sha256()
    for i in range(0, len(idx), 20000):
        blk = np.asarray(Xs[idx[i:i + 20000]])
        mm[i:i + len(blk)] = blk; ha.update(np.ascontiguousarray(blk).tobytes())
    mm.flush(); del mm
    y = np.asarray(ys[idx]); np.save(out / "test100k_real_y.npy", y)
    np.save(out / "test100k_real_source_indices.npy", idx)
    rep.update(n=int(len(idx)), sha256_X_array=ha.hexdigest(), sha256_y_array=hashlib.sha256(y.tobytes()).hexdigest(),
               sha256_X_file=sha_file(fx), sha256_y_file=sha_file(out / "test100k_real_y.npy"),
               balance={str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))})
    man = json.load(open(md / "test100k_real_manifest.json"))
    rep["manifest_compare"] = dict(source_indices_equal=bool(np.array_equal(idx, np.asarray(man["source_indices"], np.int64))),
                                   sha256_X_equal=rep["sha256_X_array"] == man["sha256_X"],
                                   sha256_y_equal=rep["sha256_y_array"] == man["sha256_y"])
    if a.check:
        c = Path(a.check)
        rep["shipped_compare"] = {f: dict(shipped=sha_file(c / f), built=sha_file(out / f)) for f in ("test100k_real_X.npy", "test100k_real_y.npy") if (c / f).exists()}
        for v in rep["shipped_compare"].values():
            v["equal"] = v["shipped"] == v["built"]
    ok = rep["manifest_compare"]["source_indices_equal"] and rep["manifest_compare"]["sha256_X_equal"] and rep["manifest_compare"]["sha256_y_equal"] \
        and all(v["equal"] for v in rep.get("shipped_compare", {}).values())
    rep["verdict"] = "REPRODUCED byte for byte" if ok else "MISMATCH"
    json.dump(rep, open(out / "build_test100k_real_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
