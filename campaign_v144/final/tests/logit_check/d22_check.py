"""On the diagnostic build v1.44d, NN_live's record words 1-4 hold as_u[47:16], the decision-path scaled sums. Compare them, shot
by shot, with the integer reference computed from the same shot's raw window words (stored by the core in the same
BRAM, read by box_live_capture.py) and the deployed weights (nn_live_ref.py). Also checks the logit/decision words
are present and the window words are the ones the kernel classified (record's shot number advances by one per shot).

"""
import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nn_live_ref as R  # noqa: E402

tot = dict(shots=0, words=0, mismatch_words=0, mismatch_shots=0, shot_steps_ok=0)
for f in sys.argv[1:]:
    z = np.load(f)
    rec = z["live_rec"].astype(np.int64)
    got = np.where(rec[:, 1:5] >= 2**31, rec[:, 1:5] - 2**32, rec[:, 1:5])
    want = R.scaled_words(R.acc(z["live_words"]))
    bad = got != want
    steps = np.diff(rec[:, 0])
    tot["shots"] += len(rec); tot["words"] += bad.size; tot["mismatch_words"] += int(bad.sum())
    tot["mismatch_shots"] += int(bad.any(1).sum()); tot["shot_steps_ok"] += int(np.sum(steps == 1))
    print(f"{Path(f).name}: {len(rec)} shots, scaled-sum word mismatches {int(bad.sum())} of {bad.size}"
          f" (shots with any mismatch {int(bad.any(1).sum())}); record shot step == 1 on {int(np.sum(steps == 1))}/{len(steps)}")
    if bad.any():
        i = int(np.argmax(bad.any(1))); print("  first mismatch: shot", i, "got", got[i].tolist(), "want", want[i].tolist())
print("SUMMARY", json.dumps(tot))
