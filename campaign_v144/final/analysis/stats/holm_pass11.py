"""Holm over every p-value printed in the draft after text pass 11; P193's sentence and P201's adjusted p
are recomputed from it, not copied.

Family = holm_pass9b.json's 44 tests (every p printed after pass 9b, all still printed after
pass 10) plus the 7 tests pass 11 prints for the first time, each with its discordant counts from its source file.
Exact two-sided McNemar p. Writes holm_pass11.json (with the P193 sentence and P201's adjusted-p clause) next to this
script.

  PYTHONIOENCODING=utf-8 python campaign_v144/final/analysis/stats/holm_pass11.py
"""
import json
from math import comb
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[4]
CV = ROOT / "campaign_v144"
old = json.load(open(HERE / "holm_pass9b.json"))["tests"]


def mcn(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


new = []
r = json.load(open(CV / "final/analysis/offline/lda_box_vs_fir.json"))["headline_mosaic"]["box576-fir576"]
new.append(dict(paragraphs="P139", printed="pass 11", test="LDA boxcar-576 vs LDA FIR-576, headline 99,400", b=r["a_only"], c=r["b_only"],
                source="campaign_v144/final/analysis/offline/lda_box_vs_fir.json"))
r = json.load(open(CV / "final/analysis/s5_linear_99400_v144.json"))["headline"]["LDA_ridge0.01"]["vs_NN_live"]
new.append(dict(paragraphs="P178", printed="pass 11", test="LDA fixed ridge 1e-2, 770 samples, vs NN_live, headline 99,400", b=r["A_only"], c=r["B_only"],
                source="campaign_v144/final/analysis/s5_linear_99400_v144.json"))
P = json.load(open(CV / "final/analysis/s2/arch_aug_v144.json"))["paired_vs_t4"]
for m in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d"):
    r = P[f"{m}_aug_vs_t4_clean"]
    new.append(dict(paragraphs="P178", printed="pass 11", test=f"{m} trained on augmented data vs the deployed 4-unit network, board A replay, 16,000 shots",
                    b=r["b"], c=r["c"], source="campaign_v144/final/analysis/s2/arch_aug_v144.json"))
r = json.load(open(CV / "final/inloop/arms/arms_full_analysis.json"))["A"]["final_run2"]["paired"]["nominal"]
new.append(dict(paragraphs="P201", printed="pass 11", test="nominal-gain arm vs gate-idle run 2, board A, 50,000 rows", b=r["A_only"], c=r["B_only"],
                source="campaign_v144/final/inloop/arms/arms_full_analysis.json"))

tests = [dict(t) for t in old] + new
for t in tests:
    t["p"] = mcn(t["b"], t["c"])
for t, h in zip(tests, holm([t["p"] for t in tests])):
    t["holm"] = h
surv = [t for t in tests if t["holm"] < 0.05]
mh = max(t["holm"] for t in surv)
adj = {t["test"]: t["holm"] for t in tests}
words = {9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen"}
out = dict(n=len(tests), n_before=len(old), n_new=len(new), nominal=sum(t["p"] < 0.05 for t in tests), survivors=len(surv),
           max_surviving_adjusted=mh, survivor_tests=[t["test"] for t in sorted(surv, key=lambda t: t["holm"])], tests=tests)
a1, a2 = adj["In the loop: Board B, vs its gate-idle run"], adj["zero vs nominal pulse gain, board A, 99,400"]
out["adj_p201"] = dict(boardB_inloop=a1, boardA_zero=a2)
# the survivors, grouped as P193 names them; the assert keeps the sentence tied to the recount
groups = [("boxcar vs FIR", 3), ("LDA boxcar-576 vs LDA FIR-576", 1), ("trained on augmented data vs LDA", 3),
          ("trained on augmented data vs the deployed", 3), ("vs LDA, loop20k", 2), ("NN_axi (emulated) vs NN_live, board A", 1),
          ("NN_live vs LDA FIR-770, board A", 2), ("NN_live vs LDA_live model", 1), ("map refit", 1)]
for g, k in groups:
    assert sum(g.lower() in s.lower() for s in out["survivor_tests"]) == k, (g, k)
assert sum(k for _, k in groups) == len(surv)
out["p193_sentence"] = (
    f"under a Holm correction across the {len(tests)} tests whose p-values are given here, {words[len(surv)]} stay below 0.05 "
    f"(adjusted p ≤ {-(-mh * 1000 // 1) / 1000:.3f}): the boxcar-versus-FIR differences on the full split and on the 80,000 unused rows "
    "of each board and the boxcar path's cost to LDA, the gains of three augmented models over LDA and over the deployed network and "
    "the losses of two nonlinear models to LDA after replay, NN_axi's and LDA's margins over NN_live on board A (LDA's also on the "
    "80,000 unused rows), NN_live's margin over the LDA core of Sec. IX, and the map refit for the deployed seed. Comparisons that were "
    "run but are not reported, such as the architecture sweeps listed below, are outside this family.")
(HERE / "holm_pass11.json").write_text(json.dumps(out, indent=1))
print(f"{len(tests)} tests ({len(old)} + {len(new)} new), nominal {out['nominal']}, Holm survivors {len(surv)}, max surviving adjusted {mh:.4f}")
print(f"P201 adjusted: board B in-loop {a1:.3f}, board A zero gain {a2:.3f}")
for t in sorted(surv, key=lambda t: t["holm"]):
    print(f"  {t['paragraphs']:<10} {t['test'][:90]:<90} p {t['p']:.3g}  Holm {t['holm']:.3g}")
print("new tests:")
for t in new:
    print(f"  {t['paragraphs']:<6} {t['test'][:90]:<90} p {t['p']:.3g}  Holm {t['holm']:.3g}")
