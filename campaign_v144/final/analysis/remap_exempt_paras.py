"""Moves the paragraph keys of make_v144_exempt.py's exemptions onto a new draft after paragraphs were added, removed or
reordered. An exemption (P_old, number) goes to the paragraph of the new dump that contains the number and reads most
like P_old did; if no new paragraph contains the number, it is dropped and listed.

Arguments: the old and the new text dump of the draft (P<n>|<text> lines). Writes v144_exempt_pmap.json:
{"P_old|number": "P_new"}; make_v144_exempt.py applies it.

"""
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv_ = sys.argv
NUM = re.compile(r"(?<![\w.])[-−+±]?\d[\d,]*(?:\.\d+)?(?![\w])")

def load(p):
    d = {}
    for ln in open(p, encoding="utf-8"):
        m = re.match(r"P(\d+)\|(.*)", ln.rstrip("\n"))
        if m:
            d[f"P{m[1]}"] = m[2]
    return d

def nums(t):
    return {m[0].lstrip("-−+±").replace(",", "").rstrip(".") for m in NUM.finditer(re.sub(r"\[\d{1,2}\]", " ", t))}

old, new = load(sys.argv[1]), load(sys.argv[2])
newnums = {p: nums(t) for p, t in new.items()}
# load the exemption tables without writing the tsv
src = (HERE / "make_v144_exempt.py").read_text(encoding="utf-8")
src = src.split("root = Path(__file__)")[0]
ns = {}
exec(compile(src, "make_v144_exempt.py", "exec"), ns)
pmap, dropped = {}, []
for p, tab in ns["L"].items():
    for n in tab:
        key = n.lstrip("-−+±").replace(",", "").rstrip(".")
        cands = [q for q in new if key in newnums[q]]
        if not cands:
            dropped.append(f"{p} {n}")
            continue
        ot = old.get(p, "")
        best = max(cands, key=lambda q: difflib.SequenceMatcher(None, ot, new[q], autojunk=False).ratio())
        pmap[f"{p}|{n}"] = best
json.dump(pmap, open(HERE / "v144_exempt_pmap.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"mapped {len(pmap)}, dropped {len(dropped)} (number no longer in the draft):")
for x in dropped:
    print("  ", x)
