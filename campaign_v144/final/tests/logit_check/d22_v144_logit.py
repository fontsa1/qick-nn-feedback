"""On the deployed build, NN_live's on-chip logit (record word 5) against the exact integer reference computed from
the same shot's raw window words (record CAP words) and the deployed weights: first-layer sums, scaled sums K*acc + b4
(nn_live_ref.py), relu on the 2^-16 grid, ternary output sum + b6 + b10, floor to the logit's 2^-10 grid, saturate.
  """
import glob, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "campaign_v144/final/tests/logit_check"))
import nn_live_ref as R  # noqa: E402
W = R.W
rd = lambda n: [float(x) for x in (W / n).read_text().replace("\n", ",").split(",") if x.strip()]
w6 = np.array(rd("w6.txt")).astype(np.int64); c = int(round((rd("b6.txt")[0] + rd("b10.txt")[0]) * 65536))
def logit_raw(sw):
    st = (np.maximum(sw, 0) * w6).sum(1) + c
    return np.clip(np.floor(st / 64.0).astype(np.int64), -32768, 32767)
files = sys.argv[1:] or sorted(glob.glob(str(ROOT / "campaign_v144/final/live/*_run[12]_*.npz")))
tot = dict(shots=0, logit_mismatch=0, decision_mismatch=0, files=len(files))
for f in files:
    z = np.load(f); rec = z["live_rec"].astype(np.int64)
    lg = rec[:, 5] & 0xFFFF; lg = np.where(lg >= 32768, lg - 65536, lg)
    mine = logit_raw(R.scaled_words(R.acc(z["live_words"])))
    tot["shots"] += len(lg); tot["logit_mismatch"] += int((mine != lg).sum())
    tot["decision_mismatch"] += int(((mine >= 16).astype(int) != (rec[:, 7] & 1)).sum())
print("SUMMARY", json.dumps(tot))
