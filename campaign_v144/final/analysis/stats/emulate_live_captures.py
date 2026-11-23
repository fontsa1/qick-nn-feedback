"""Bit-accurate (hls4ml fixed-point) emulation of three networks on every stored NN_live capture, both boards, every run.

  box576  model_signed_domain_seed20260901_w576_box.h5 on the 'box' stream (the deployed NN_live; checked against the
          chip's decision live_rec[:, 7] & 1 shot by shot)
  fir576  model_signed_domain_seed20260901_w576.h5 on the 'fir' stream, first 576 samples (the FIR-path network of
          box_vs_fir_v144.py; reproduces its board-A json)
  axi770  model_v140_200k_seed20260904.h5 on the 'fir' stream, all 770 samples (the NN_axi network of
          analyze_axi_emu_v144.py; EMULATED NN_axi on the live session's FIR buffer, not an on-chip NN_axi decision)

Same preprocessing as box_vs_fir_v144.py / analyze_axi_emu_v144.py (T.hw_raw_transform). Copied method, outputs
redirected: the hls4ml build directories go to _emu_build/ beside this script (not %TEMP%), results to
emu_live_preds.npz beside it. Read-only on all inputs.

"""
import glob, os, re, sys, time
from pathlib import Path
os.environ.update(KERAS_BACKEND="tensorflow", TF_USE_LEGACY_KERAS="1", TF_CPP_MIN_LOG_LEVEL="3")
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; os.chdir(ROOT)
OUT = Path(__file__).resolve().parent
sys.path[:0] = ["analysis_scripts/analysis", "analysis_scripts/acquisition", "audit_fixes/R3_R2", "."]
from qkeras.utils import load_qmodel  # noqa: E402
import fixed_point_emulator as F, task33_three_way_comparison as T  # noqa: E402

MODELS = {"box576": ("model_signed_domain_seed20260901_w576_box.h5", "box", 1152),
          "fir576": ("model_signed_domain_seed20260901_w576.h5", "fir", 1152),
          "axi770": ("model_v140_200k_seed20260904.h5", "fir", 1540)}
t0 = time.time()
emu = {k: F.fixed_point_model(load_qmodel(m, compile=False), OUT / "_emu_build" / Path(m).stem) for k, (m, _, _) in MODELS.items()}
print(f"emulators built ({time.time()-t0:.0f}s)", flush=True)
res = {}
for f in sorted(glob.glob("campaign_v144/final/live/*_run*_*.npz"), key=lambda f: (Path(f).name[:6], int(re.findall(r"_(\d+)_\d+\.npz", f)[0]))):
    b, r = re.findall(r"([AB])_run(\d)_", Path(f).name)[0]
    z = np.load(f)
    d = res.setdefault(f"{b}{r}", {"rows": [], "y": [], "chip": [], **{k: [] for k in MODELS}})
    d["rows"].append(z["rows"]); d["y"].append(z["y"]); d["chip"].append(z["live_rec"][:, 7] & 1)
    for k, (_, stream, nin) in MODELS.items():
        x = np.ascontiguousarray(T.hw_raw_transform(z[stream].astype(np.float64))[:, :nin], dtype=np.float32)
        d[k].append(np.asarray(emu[k].predict(x)).reshape(-1))
    print(Path(f).name, f"({time.time()-t0:.0f}s)", flush=True)
sav = {}
for br, d in res.items():
    for k, v in d.items():
        sav[f"{br}_{k}"] = np.concatenate(v)
    print(br, "n", len(sav[f"{br}_rows"]), "box emu == chip:", int(((sav[f"{br}_box576"] > .5).astype(int) == sav[f"{br}_chip"]).sum()), flush=True)
np.savez(OUT / "emu_live_preds.npz", **sav)
print(f"done ({time.time()-t0:.0f}s)")
