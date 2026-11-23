"""every .npz under campaign_v143/ and campaign_v144/ (outside the NN_live captures) that holds NN_axi
probabilities ('probs') or the NN_axi input buffer ('dec_iq'), with its test-row range. Writes t4_find_axi.json."""
import glob, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
found = []
for camp in ("campaign_v144", "campaign_v143"):
    for f in sorted(glob.glob(str(ROOT / camp / "**/*.npz"), recursive=True)):
        p = Path(f).as_posix()
        if "/live/" in p or "/analysis/stats/" in p:
            continue
        try:
            z = np.load(f, allow_pickle=True); ks = z.files
        except Exception:
            continue
        if "probs" in ks or "dec_iq" in ks:
            r = z["idx"] if "idx" in ks else (z["rows"] if "rows" in ks else None)
            ds = str(z["dataset"]) if "dataset" in ks else ""
            found.append(dict(file=str(Path(f).relative_to(ROOT)), n=int(len(z["probs"])) if "probs" in ks else None,
                              row_min=int(r.min()) if r is not None else None, row_max=int(r.max()) if r is not None else None,
                              dataset=ds))
beyond = [d for d in found if d["row_max"] is not None and d["row_max"] >= 20000]
(OUT / "t4_find_axi.json").write_text(json.dumps(dict(found=found, beyond_row_19999=beyond), indent=1))
print(len(found), "files with NN_axi outputs;", len(beyond), "reach rows >= 20,000")
for d in beyond:
    print(d)
from collections import Counter
print(Counter((Path(d["file"]).parent.as_posix(), d["row_min"] is not None and d["row_max"]) for d in found).most_common(40))
