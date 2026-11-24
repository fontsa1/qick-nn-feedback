"""R5 chain runner: runs every training job sequentially (one 4-thread TF process at a time), skipping
jobs whose runs/<tag>/result.json already exists (resumable). Per-job logs in logs/<tag>.log.

  python audit_fixes/R5/run_all.py      (launched detached; see PROGRESS.md)
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = sys.executable

JOBS = [
    ("exact_s32_lr0.001", ["train_exact.py", "--seed", "32"]),
    ("ours_s20260901", ["reproduce_ours.py", "--seed", "20260901"]),
    ("ours_s20260902", ["reproduce_ours.py", "--seed", "20260902"]),
    ("ours_s20260903", ["reproduce_ours.py", "--seed", "20260903"]),
    ("exact_s33_lr0.001", ["train_exact.py", "--seed", "33"]),
    ("exact_s34_lr0.001", ["train_exact.py", "--seed", "34"]),
    ("exact_s32_lr0.0001", ["train_exact.py", "--seed", "32", "--lr", "1e-4"]),
]

for tag, cmd in JOBS:
    if (HERE / "runs" / tag / "result.json").exists():
        print(f"{time.strftime('%H:%M:%S')} skip {tag} (done)", flush=True)
        continue
    print(f"{time.strftime('%H:%M:%S')} start {tag}", flush=True)
    with open(HERE / "logs" / f"{tag}.log", "w") as f:
        rc = subprocess.call([PY, str(HERE / cmd[0])] + cmd[1:], stdout=f, stderr=subprocess.STDOUT, cwd=str(ROOT))
    print(f"{time.strftime('%H:%M:%S')} end {tag} rc={rc}", flush=True)
print(f"{time.strftime('%H:%M:%S')} ALL DONE", flush=True)
