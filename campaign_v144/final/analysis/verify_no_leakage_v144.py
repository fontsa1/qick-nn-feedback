"""The leakage audit's scored-set checks (C, G) and map checks (F) on the v1.44 files. tools/verify_no_leakage.py's
checks C and G read the v1.40/v1.41 per-shot files and its checks D/F the FIR-path map (k2, c2); this adds what the
v1.44 numbers rest on. Run it after tools/verify_no_leakage.py, whose checks A, B and E do not depend on the build.

  C44  every v1.44 per-shot file of the NN_axi sessions and NN_live runs 1 and 2 indexes test rows that exist,
       with labels equal to the test split's, each row once per file set; the scored rows' content shares nothing
       with the domain-map fit slice except the slice itself, and every headline set leaves rows 1000:1600 out
  G44  each board's two NN_live runs together cover every row of test100k_real exactly once
  F44  NN_live's map (calibration/box_domain_map.json, the boxcar path) is fit on rows 1000:1600 only and without
       labels: the fitting code reads no label file, and refitting it from its recorded capture with the same code
       gives the recorded coefficients

Inputs (DATA_MANIFEST.csv lists the ones not shipped): the v1.44 per-shot files campaign_v144/final/{axi,live}/*.npz,
data/test100k_real_{X,y}.npy, data/test20k_real_X.npy, and the map's capture campaign_v140L1/box_part2000.partial.npz.
Run it from the repository root; the log beside this script is its output.

"""
import glob
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).resolve().parents[3]))
os.chdir(ROOT)
for d in ("tools", "analysis_scripts/acquisition", "audit_fixes/R3_R2"):
    sys.path.insert(0, str(ROOT / d))
import verify_no_leakage as V          # noqa: E402  (record, row_hashes, constants)
import build_box_training_set as BB    # noqa: E402
from r3_stats import calmask           # noqa: E402  (the headline mask every v1.44 analysis uses)

def data(name):
    """data/<name>, or <name> in the root (where an older checkout keeps the arrays)."""
    return f"data/{name}" if Path(f"data/{name}").exists() else name

D = "campaign_v144/final/"
lo, hi = V.CALIB_SLICE
y100 = np.load(data("test100k_real_y.npy")).astype(int)
X100 = np.load(data("test100k_real_X.npy"), mmap_mode="r")
N100 = len(y100)
print("v1.44 supplement to tools/verify_no_leakage.py")

def per_shot(pattern, key):
    rows, ys = [], []
    for f in sorted(glob.glob(pattern)):
        z = np.load(f, allow_pickle=True)
        rows.append(np.asarray(z[key]).astype(np.int64)); ys.append(np.asarray(z["y"]).astype(int))
    if not rows:
        return None, None
    return np.concatenate(rows), np.concatenate(ys)

print("\nC44. v1.44 per-shot files index the test split with matching labels")
SETS = {}
for b in "AB":
    SETS[f"NN_axi session, board {b}"] = (f"{D}axi/{b}_axi_*.npz", "idx", 20000)
    for r in "12":
        SETS[f"NN_live run {r}, board {b}"] = (f"{D}live/{b}_run{r}_*.npz", "rows", N100)
for name, (pat, key, n_exp) in SETS.items():
    r, y = per_shot(pat, key)
    if r is None:
        V.record(f"C44 {name}: files present", False, f"no files match {pat} (see DATA_MANIFEST.csv)")
        continue
    ok = (len(np.unique(r)) == len(r) and r.min() >= 0 and r.max() < N100 and np.array_equal(y100[r], y))
    V.record(f"C44 {name}: {len(r):,} rows, each once, labels equal to the test split", ok,
             f"unique {len(np.unique(r))} of {len(r)}, range [{r.min()}, {r.max()}], label mismatches {(y100[r] != y).sum()}")
    SETS[name] = (pat, key, n_exp, r)
for b in "AB":                                   # each run is half the split; a board's two runs cover it once
    parts = [SETS[f"NN_live run {k}, board {b}"] for k in "12"]
    if any(len(p) < 4 for p in parts):
        V.record(f"G44 NN_live runs 1 + 2, board {b}: every test row exactly once", False, "per-shot files missing")
        continue
    r = np.concatenate([p[3] for p in parts])
    V.record(f"G44 NN_live runs 1 + 2, board {b}: every test row exactly once", len(r) == N100 and len(np.unique(r)) == N100,
             f"{len(r)} rows, {len(np.unique(r))} unique")
m = calmask(np.arange(N100))
V.record(f"C44 the headline mask (r3_stats.calmask) drops exactly rows {lo}:{hi}",
         int((~m).sum()) == hi - lo and not m[lo:hi].any() and m[:lo].all() and m[hi:].all(), f"{int((~m).sum())} rows dropped")
h_slice = set(V.row_hashes(np.asarray(X100[lo:hi])))
h_rest = set()
for i in range(0, N100, V.CHUNK):
    j = min(i + V.CHUNK, N100)
    keep = [k for k in range(i, j) if not lo <= k < hi]
    h_rest.update(V.row_hashes(np.asarray(X100[keep])))
V.record("C44 no headline row has the content of a map-fit row", len(h_rest & h_slice) == 0, f"{len(h_rest & h_slice)} shared")

print("\nF44. NN_live's map (calibration/box_domain_map.json): rows and labels")
mp = "calibration/box_domain_map.json" if Path("calibration/box_domain_map.json").exists() else "box_domain_map.json"
bm = json.load(open(mp))
V.record(f"F44 {mp} records calib_rows {lo}:{hi}", bm.get("calib_rows") == f"{lo}:{hi}", repr(bm.get("calib_rows")))
src = Path(BB.__file__).read_text(encoding="utf-8")
fit_src = src[src.index("def main"):src.index("meta = dict")]
label_reads = re.findall(r"np\.load\([^)]*_y[^)]*\)|\[\s*['\"]y['\"]\s*\]", fit_src)
V.record("F44 the map's fitting code reads no label (no *_y file, no ['y'] field)", not label_reads, f"found {label_reads}")
caps = []
for f in bm["captures"]:                         # as build_box_training_set.main() reads them
    if not Path(f).exists():
        V.record(f"F44 the map's capture {f} is present", False, "not shipped; see DATA_MANIFEST.csv")
        break
    c = dict(np.load(f))
    if "rows" not in c:
        n = int(c["done"]); c["rows"] = int(c["start"]) + np.arange(n); c["box"] = c["box"][:n]
    caps.append(c)
if len(caps) == len(bm["captures"]):
    rows = np.concatenate([c["rows"] for c in caps]); box = np.concatenate([c["box"] for c in caps])
    sel = (rows >= lo) & (rows < hi)
    Xref = np.load(data("test20k_real_X.npy"), mmap_mode="r")
    zr, za = BB.cz(Xref[rows[sel]]), BB.cz(box[sel])
    e, s, kb, cb = BB.fit(zr.mean(0), za.mean(0), bm["m"], complex(*bm["prime"]))
    same = abs(kb - complex(*bm["k"])) < 1e-9 and abs(cb - complex(*bm["c"])) < 1e-6 and abs(s - bm["shift"]) < 1e-9
    V.record(f"F44 refitting from {bm['captures'][0]} (rows {lo}:{hi}, class-pooled means) gives the recorded map", same,
             f"refit k {kb:.6f} c {cb:.4f} s {s}; recorded k {complex(*bm['k']):.6f} c {complex(*bm['c']):.4f} s {bm['shift']}",
             pass_detail=f"{int(sel.sum())} shots, k {kb:.5f}, shift {s:+.2f}")

n_ok = sum(1 for _, ok, _ in V.results if ok)
print(f"\n{n_ok} of {len(V.results)} v1.44 checks pass")
sys.exit(0 if n_ok == len(V.results) else 1)
