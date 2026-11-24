"""Holm over every p-value printed in the draft after pass 18 (rule 6: the Appendix B sentence is recomputed, not copied).

Family = holm_pass11.json's 51 tests plus the 8 that pass 18 prints for the first time: S2 on board B's v1.44 replay
(four augmented models vs LDA, and vs the chip's deployed 4-unit network), each with its discordant counts from
campaign_v144/final/analysis/s2/board_B/arch_aug_v144_B.json. Exact two-sided McNemar p. Writes holm_pass18.json.

  PYTHONIOENCODING=utf-8 python campaign_v144/final/analysis/stats/holm_pass18.py
"""
import json
from math import comb
from pathlib import Path


def mcn(b, c):
    """Exact two-sided McNemar p (as holm_pass11.py)."""
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    """Holm step-down adjusted p (as holm_pass11.py)."""
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


HERE = Path(__file__).parent
CV = Path(__file__).resolve().parents[3]
old = json.load(open(HERE / "holm_pass11.json"))["tests"]
assert len(old) == 51
J = json.load(open(CV / "final/analysis/s2/board_B/arch_aug_v144_B.json"))
new = []
for m in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d"):
    r = J[f"{m}_aug"]["vs_lda_clean"]
    new.append(dict(paragraphs="P396", printed="pass 18", test=f"{m} trained on augmented data vs LDA, board B replay, 16,000 shots",
                    b=r["b"], c=r["c"], source="campaign_v144/final/analysis/s2/board_B/arch_aug_v144_B.json"))
    r = J["paired_vs_t4"][f"{m}_aug_vs_t4_clean"]
    new.append(dict(paragraphs="P396", printed="pass 18", test=f"{m} trained on augmented data vs the deployed 4-unit network, board B replay, 16,000 shots",
                    b=r["b"], c=r["c"], source="campaign_v144/final/analysis/s2/board_B/arch_aug_v144_B.json"))
tests = [{k: v for k, v in t.items() if k not in ("p", "holm")} for t in old] + new
for t in tests:
    t["p"] = mcn(t["b"], t["c"])
for t, h in zip(tests, holm([t["p"] for t in tests])):
    t["holm"] = h
surv = sorted([t for t in tests if t["holm"] < 0.05], key=lambda t: t["holm"])
out = dict(n=len(tests), n_before=len(old), n_new=len(new), nominal=sum(t["p"] < 0.05 for t in tests), survivors=len(surv),
           max_surviving_adjusted=max(t["holm"] for t in surv), survivor_tests=[t["test"] for t in surv], tests=tests)
(HERE / "holm_pass18.json").write_text(json.dumps(out, indent=1))
print(f"{len(tests)} tests ({len(old)} + {len(new)} new), nominal {out['nominal']}, Holm survivors {len(surv)}, "
      f"max surviving adjusted {out['max_surviving_adjusted']:.4f}")
for t in surv:
    print(f"  {t['paragraphs']:<10} {t['test'][:95]:<95} p {t['p']:.3g}  Holm {t['holm']:.3g}")
print("new tests:")
for t in new:
    print(f"  {t['test'][:95]:<95} b {t['b']} c {t['c']} p {t['p']:.3g}  Holm {t['holm']:.3g}")
