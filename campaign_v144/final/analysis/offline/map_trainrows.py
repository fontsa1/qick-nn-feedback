"""Does the headline depend on fitting the boxcar domain map to 600 test-split rows?

The deployed map (box_domain_map.json, build_box_training_set.py) is fit, label-free, on the mean trajectory of the
boxcar-path replay of test20k_real_X[1000:1600]. Here the same fit is made on the replay of 600 never-used TRAINING rows
(0528_X_train_0_770[300000:300600], replayed on the same build by queue.sh step trainrows), with the same code (fit, ma,
fshift imported from build_box_training_set.py). Then the deployed training recipe (export_signed_domain_model.py:
build_model, hw_raw_transform, rows 0:10000 + 110000:300000, window 576, validation_split 0.2, early stopping) is trained
twice with ONE seed (20260904, the deployed one): once on the deployed map's training set, once on the training-row map's.
Both float models are scored on the boxcar streams NN_live classified for the 99,400-shot headline (the v1.44 captures),
paired shot by shot (exact McNemar). The deployed model file is scored the same way as a reference.

"""
import argparse, glob, json, os, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "analysis_scripts" / "acquisition")); sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
import build_box_training_set as BB  # noqa: E402
from r3_stats import fstats, paired  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--capture", nargs="+", required=True)
ap.add_argument("--seed", type=int, default=20260904)
ap.add_argument("--rows", default="0:10000,110000:300000")
a = ap.parse_args()
t0 = time.time()
dep = json.load(open(ROOT / "box_domain_map.json"))
M = int(dep["m"]); prime = complex(*dep["prime"])

# ---- fit on the training-row replay
caps = [np.load(ROOT / f) for f in a.capture]
rows = np.concatenate([c["rows"] for c in caps]); box = np.concatenate([c["box"] for c in caps])
Xtr = np.load(ROOT / "0528_X_train_0_770.npy", mmap_mode="r")
zr = BB.cz(Xtr[rows]); za = BB.cz(box)
e, s, kb, cb = BB.fit(zr.mean(0), za.mean(0), M, prime)
kd, cd, sd = complex(*dep["k"]), complex(*dep["c"]), float(dep["shift"])
res = dict(note=__doc__.split("\n")[0], capture=a.capture, n_fit_rows=int(len(rows)), rows_fit=[int(rows.min()), int(rows.max())],
           deployed_map=dict(k=[kd.real, kd.imag], c=[cd.real, cd.imag], shift=sd, rms=dep["fits"][str(M)]["rms"]),
           trainrow_map=dict(k=[kb.real, kb.imag], c=[cb.real, cb.imag], shift=s, rms=e),
           k_ratio=abs(kb / kd), k_phase_deg=float(np.degrees(np.angle(kb / kd))), c_diff=abs(cb - cd))
print(f"deployed map: |k| {abs(kd):.5f} arg {np.degrees(np.angle(kd)):+.2f} c {cd:.3f} s {sd:+.2f}", flush=True)
print(f"train-row map: |k| {abs(kb):.5f} arg {np.degrees(np.angle(kb)):+.2f} c {cb:.3f} s {s:+.2f} (rms {e:.2f})", flush=True)
print(f"  |k| ratio {res['k_ratio']:.4f}, phase {res['k_phase_deg']:+.2f} deg, |c diff| {res['c_diff']:.3f} ({time.time()-t0:.0f}s)", flush=True)

# ---- the two training pools (row order = --rows order, as the deployed set)
ranges = [tuple(int(v) for v in r.split(":")) for r in a.rows.split(",")]
src = np.concatenate([np.arange(l, h) for l, h in ranges])
ytr = np.load(ROOT / "0528_y_train_0_770.npy")[src].astype("float32")
Xdep = np.load(ROOT / "0528_X_train_box_calibrated.npy", mmap_mode="r")
assert np.array_equal(np.load(ROOT / "0528_X_train_box_calibrated_rows.npy"), src), "deployed training set rows differ"
os.environ["KERAS_BACKEND"] = "tensorflow"; os.environ["TF_USE_LEGACY_KERAS"] = "1"
import export_signed_domain_model as EX  # noqa: E402  (build_model, hw_raw_transform; imports TF)
import tensorflow as tf  # noqa: E402
W = 576

def pool_trainrow_map():
    out = np.empty((len(src), 2 * W), np.float32); k = 0
    for l, h in ranges:
        for b in range(l, h, 20000):
            e_ = min(h, b + 20000)
            z = kb * BB.fshift(BB.ma(BB.cz(Xtr[b:e_]), M, prime), s) + cb
            blk = np.empty((e_ - b, 1540), np.float32); blk[:, 0::2] = z.real; blk[:, 1::2] = z.imag
            out[k:k + e_ - b] = EX.hw_raw_transform(blk, 1)[:, :2 * W]; k += e_ - b
    return out

def train(X, y):
    tf.keras.utils.set_random_seed(a.seed)
    perm = np.random.default_rng(a.seed).permutation(len(y))
    m = EX.build_model(X.shape[1])
    es = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    h = m.fit(X[perm], y[perm], validation_split=0.2, epochs=50, batch_size=32, verbose=0, callbacks=[es])
    return m, float(min(h.history["val_loss"])), len(h.history["val_loss"])

# ---- evaluation set: the headline mosaic's boxcar streams (what NN_live classified)
bx, ry, rr, dec = [], [], [], []
for b, cond in (("A", lambda r: r < 50000), ("B", lambda r: r >= 50000)):
    for f in sorted(glob.glob(str(ROOT / f"campaign_v144/final/live/{b}_run1_*.npz"))):
        z = np.load(f); m = cond(z["rows"]) & ~((z["rows"] >= 1000) & (z["rows"] < 1600))
        bx.append(z["box"][m, :2 * W]); ry.append(z["y"][m]); rr.append(z["rows"][m]); dec.append(z["live_rec"][m, 7] & 1)
Xev = EX.hw_raw_transform(np.concatenate(bx).astype(np.float32), 1); yev = np.concatenate(ry).astype(int)
dec = np.concatenate(dec).astype(int)
print(f"evaluation set {len(yev)} shots; NN_live on chip {fstats(dec, yev)['fid']:.3f} ({time.time()-t0:.0f}s)", flush=True)
res["eval_n"] = int(len(yev)); res["NN_live_chip"] = fstats(dec, yev)
preds = {}
dm = sorted(glob.glob(str(ROOT / "models" / "*w576*box*.h5")) + glob.glob(str(ROOT / "*w576*box*.h5")))
if dm:
    from qkeras.utils import _add_supported_quantized_objects
    co = {}; _add_supported_quantized_objects(co)
    md = tf.keras.models.load_model(dm[0], custom_objects=co, compile=False)
    preds["deployed_file"] = (md.predict(Xev, batch_size=4096, verbose=0)[:, 0] > 0.5).astype(int)
    res["deployed_file"] = dict(path=str(Path(dm[0]).relative_to(ROOT)), **fstats(preds["deployed_file"], yev))
    print(f"deployed model file {dm[0]}: {res['deployed_file']['fid']:.3f}", flush=True)

for nm, getX in (("deployed_map", lambda: EX.hw_raw_transform(np.asarray(Xdep, np.float32), 1)[:, :2 * W]), ("trainrow_map", pool_trainrow_map)):
    X = getX()
    m, vl, ep = train(X, ytr); del X
    preds[nm] = (m.predict(Xev, batch_size=4096, verbose=0)[:, 0] > 0.5).astype(int)
    res[nm + "_model"] = dict(seed=a.seed, val_loss=vl, epochs=ep, **fstats(preds[nm], yev))
    print(f"{nm}: val_loss {vl:.5f} ({ep} epochs) -> headline shots {res[nm + '_model']['fid']:.3f} ({time.time()-t0:.0f}s)", flush=True)
    tf.keras.backend.clear_session()
    (OUT / f"map_trainrows_s{a.seed}.json").write_text(json.dumps(res, indent=1, default=float))
res["trainrow_vs_deployed_map"] = paired(preds["trainrow_map"], preds["deployed_map"], yev)
if "deployed_file" in preds:
    res["deployed_map_retrain_vs_file"] = paired(preds["deployed_map"], preds["deployed_file"], yev)
(OUT / f"map_trainrows_s{a.seed}.json").write_text(json.dumps(res, indent=1, default=float))
np.savez(OUT / f"map_trainrows_preds_s{a.seed}.npz", y=yev, nn_live=dec, **preds)
print("trainrow vs deployed map:", res["trainrow_vs_deployed_map"], f"({time.time()-t0:.0f}s)")
