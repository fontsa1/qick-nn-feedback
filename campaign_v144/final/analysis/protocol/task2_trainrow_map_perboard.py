"""The P189 training-row domain-map refit, re-scored per board.

campaign_v144/final/analysis/offline/map_trainrows.py fit NN_live's boxcar-path map on the v1.44 replay of 600
never-used TRAINING rows (0528_X_train_0_770[300000:300600], both boards, 1,200 shots), retrained the deployed recipe
for five seeds on each map, and scored the float models on ONE evaluation set: the run-1 "mosaic" (board A rows
0..49,999 + board B rows 50,000..99,999, rows 1000:1600 removed; the 95.60 % headline of V144_RESULTS.md). It saved
predictions on that mosaic only, so per-board numbers (P201: 95.55 % A, 95.62 % B, all 99,400 traces on each board)
cannot be derived from its files.

This script repeats the same training (same code path: build_box_training_set.{cz,ma,fshift,fit},
export_signed_domain_model.{build_model,hw_raw_transform}, same seeds, permutation, validation split and early stop)
and scores every model on:
  board A, all 99,400 headline traces (run 1 rows 0..49,999 + run 2 rows 50,000..99,999),
  board B, all 99,400 headline traces (run 2 rows 0..49,999 + run 1 rows 50,000..99,999),
  the run-1 mosaic (rebuilt from the two boards' predictions), to check reproduction of map_trainrows_s*.json.
Arms:
  deployed     0528_X_train_box_calibrated.npy (map fit on v1.40 replay of test rows 1000:1600, box_domain_map.json)
  trainrow     map fit on the v1.44 replay of training rows 300000:300600, boards A+B pooled (as map_trainrows.py)
  v144testrow  map fit on the v1.44 replay of test rows 1000:1600 (A run 1 + B run 2, pooled 1,200 shots) -- the
               same rows as the deployed map on the deployed build, which separates "rows" from "build"
All three fits use the deployed map's filter prime (the v1.40 calibration offset), as map_trainrows.py does.
Writes task2_results.json, task2_preds_<arm>_s<seed>.npz, task2_models/<arm>_s<seed>.h5 and logs to stdout.

"""
import argparse, glob, json, os, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "analysis_scripts" / "acquisition")); sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
import build_box_training_set as BB  # noqa: E402
from r3_stats import fstats, paired, calmask  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, nargs="+", default=[20260901, 20260902, 20260903, 20260904, 20260905])
ap.add_argument("--arms", nargs="+", default=["deployed", "trainrow", "v144testrow"])
a = ap.parse_args()
t0 = time.time()
W = 576
RANGES = [(0, 10000), (110000, 300000)]
src = np.concatenate([np.arange(l, h) for l, h in RANGES])
dep = json.load(open("box_domain_map.json"))
M = int(dep["m"]); prime = complex(*dep["prime"])
Xtr = np.load("0528_X_train_0_770.npy", mmap_mode="r")
Xte = np.load("test100k_real_X.npy", mmap_mode="r")
ytr = np.load("0528_y_train_0_770.npy")[src].astype("float32")
assert np.array_equal(np.load("0528_X_train_box_calibrated_rows.npy"), src)
RES_P = OUT / "task2_results.json"
res = json.load(open(RES_P)) if RES_P.exists() else {}
res["doc"] = __doc__.split("\n")[0]

def log(*s):
    print(f"[{time.time() - t0:6.0f}s]", *s, flush=True)

def fit_on(files, Xref, rows_lo=None, rows_hi=None):
    rows, box = [], []
    for f in files:
        z = np.load(f)
        r = z["rows"].astype(np.int64); m = np.ones(len(r), bool)
        if rows_lo is not None:
            m = (r >= rows_lo) & (r < rows_hi)
        rows.append(r[m]); box.append(z["box"][m])
    rows = np.concatenate(rows); box = np.concatenate(box)
    e, s, kb, cb = BB.fit(BB.cz(Xref[rows]).mean(0), BB.cz(box).mean(0), M, prime)
    return dict(n_shots=int(len(rows)), rows=[int(rows.min()), int(rows.max())], files=[str(f).replace("\\", "/") for f in files],
                k=[kb.real, kb.imag], c=[cb.real, cb.imag], shift=s, rms=e, abs_k=abs(kb), arg_k_deg=float(np.degrees(np.angle(kb))))

TR = sorted(glob.glob("campaign_v144/final/analysis/offline/trainrows/*_train_300000_300600.npz"))
LV = "campaign_v144/final/live/"
T1000 = [f"{LV}A_run1_1000_2000.npz", f"{LV}B_run2_1000_2000.npz"]
maps = {"deployed": dict(k=dep["k"], c=dep["c"], shift=dep["shift"], rms=dep["fits"][str(M)]["rms"], abs_k=abs(complex(*dep["k"])),
                         arg_k_deg=float(np.degrees(np.angle(complex(*dep["k"])))), source="box_domain_map.json (v1.40 capture "
                         + ", ".join(dep["captures"]) + ", rows " + dep["calib_rows"] + ")"),
        "trainrow": fit_on(TR, Xtr),
        "trainrow_A_only": fit_on([f for f in TR if Path(f).name.startswith("A_")], Xtr),
        "trainrow_B_only": fit_on([f for f in TR if Path(f).name.startswith("B_")], Xtr),
        "v144testrow": fit_on(T1000, Xte, 1000, 1600),
        "v144testrow_A_only": fit_on(T1000[:1], Xte, 1000, 1600),
        "v144testrow_B_only": fit_on(T1000[1:], Xte, 1000, 1600)}
res["maps"] = maps
for k, v in maps.items():
    log(f"map {k:20s} |k| {v['abs_k']:.5f} arg {v['arg_k_deg']:+.3f} c {complex(*v['c']):.3f} s {v['shift']:+.2f} rms {v['rms']:.3f}")
old = json.load(open("campaign_v144/final/analysis/offline/map_trainrows_s20260901.json"))["trainrow_map"]
log("trainrow fit equals map_trainrows.py's:", np.allclose(maps["trainrow"]["k"], old["k"]) and np.allclose(maps["trainrow"]["c"], old["c"]) and maps["trainrow"]["shift"] == old["shift"])

os.environ["KERAS_BACKEND"] = "tensorflow"; os.environ["TF_USE_LEGACY_KERAS"] = "1"
import export_signed_domain_model as EX  # noqa: E402
import tensorflow as tf  # noqa: E402

# ---- evaluation sets: each board's 100k boxcar streams (what NN_live classified), rows 1000:1600 removed, row order
def board_set(b):
    X, y, r, dec = [], [], [], []
    for f in sorted(glob.glob(f"{LV}{b}_run[12]_*.npz")):
        z = np.load(f); m = calmask(z["rows"])
        X.append(z["box"][m, :2 * W]); y.append(z["y"][m]); r.append(z["rows"][m]); dec.append(z["live_rec"][m, 7] & 1)
    r = np.concatenate(r); o = np.argsort(r)
    return (EX.hw_raw_transform(np.concatenate(X)[o].astype(np.float32), 1), np.concatenate(y)[o].astype(int), r[o],
            np.concatenate(dec)[o].astype(int))

EV = {b: board_set(b) for b in "AB"}
assert np.array_equal(EV["A"][2], EV["B"][2]) and np.array_equal(EV["A"][1], EV["B"][1]) and len(EV["A"][1]) == 99400
yev, rev = EV["A"][1], EV["A"][2]
mos = rev < 50000                                   # mosaic: board A for rows < 50,000, board B above (run 1 on each)
res["eval"] = {b: dict(n=int(len(EV[b][1])), NN_live_chip=fstats(EV[b][3], yev)) for b in "AB"}
chip_mos = np.where(mos, EV["A"][3], EV["B"][3])
res["eval"]["mosaic"] = dict(n=int(len(yev)), NN_live_chip=fstats(chip_mos, yev))
res["eval"]["chip_A_vs_B"] = paired(EV["A"][3], EV["B"][3], yev)
log("chip:", {k: round(v["NN_live_chip"]["fid"], 3) for k, v in res["eval"].items() if "NN_live_chip" in v})

def pool(arm):
    if arm == "deployed":
        Xd = np.load("0528_X_train_box_calibrated.npy", mmap_mode="r")
        out = np.empty((len(src), 2 * W), np.float32)
        for i in range(0, len(src), 20000):
            out[i:i + 20000] = EX.hw_raw_transform(np.asarray(Xd[i:i + 20000, :2 * W], np.float32), 1)
        return out
    mp = maps[arm]; kb, cb, s = complex(*mp["k"]), complex(*mp["c"]), mp["shift"]
    out = np.empty((len(src), 2 * W), np.float32); k = 0
    for l, h in RANGES:
        for b in range(l, h, 20000):
            e_ = min(h, b + 20000)
            z = kb * BB.fshift(BB.ma(BB.cz(Xtr[b:e_]), M, prime), s) + cb
            blk = np.empty((e_ - b, 1540), np.float32); blk[:, 0::2] = z.real; blk[:, 1::2] = z.imag
            out[k:k + e_ - b] = EX.hw_raw_transform(blk, 1)[:, :2 * W]; k += e_ - b
    return out

(OUT / "task2_models").mkdir(exist_ok=True)
res.setdefault("runs", {})
for arm in a.arms:
    X = pool(arm); log(f"pool {arm} built {X.shape}")
    for seed in a.seeds:
        key = f"{arm}_s{seed}"
        if key in res["runs"] and (OUT / f"task2_preds_{key}.npz").exists():
            log("skip", key); continue
        tf.keras.utils.set_random_seed(seed)
        perm = np.random.default_rng(seed).permutation(len(ytr))
        m = EX.build_model(X.shape[1])
        es = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
        h = m.fit(X[perm], ytr[perm], validation_split=0.2, epochs=50, batch_size=32, verbose=0, callbacks=[es])
        pA = (m.predict(EV["A"][0], batch_size=4096, verbose=0)[:, 0] > 0.5).astype(int)
        pB = (m.predict(EV["B"][0], batch_size=4096, verbose=0)[:, 0] > 0.5).astype(int)
        pM = np.where(mos, pA, pB)
        m.save(OUT / "task2_models" / f"{key}.h5")
        res["runs"][key] = dict(arm=arm, seed=seed, val_loss=float(min(h.history["val_loss"])), epochs=len(h.history["val_loss"]),
                                A=fstats(pA, yev), B=fstats(pB, yev), mosaic=fstats(pM, yev))
        np.savez(OUT / f"task2_preds_{key}.npz", rows=rev, y=yev, A=pA, B=pB, mosaic=pM)
        log(f"{key}: val_loss {res['runs'][key]['val_loss']:.5f} ({res['runs'][key]['epochs']} ep)  A {res['runs'][key]['A']['fid']:.3f}"
            f"  B {res['runs'][key]['B']['fid']:.3f}  mosaic {res['runs'][key]['mosaic']['fid']:.3f}")
        tf.keras.backend.clear_session()
        RES_P.write_text(json.dumps(res, indent=1, default=float))
    del X
RES_P.write_text(json.dumps(res, indent=1, default=float))
log("DONE")
