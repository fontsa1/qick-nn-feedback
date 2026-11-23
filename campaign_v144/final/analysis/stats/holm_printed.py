"""Holm over every p-value printed in the draft after text pass 9b; the P193 sentence is recomputed from it, not copied.

Family = stats/t1_holm.json family (a) (every p printed in the draft after pass 6, bounds expanded) plus the tests that
passes 7, 8, 9 and 9b print for the first time, each with its discordant counts from its source file. Exact two-sided McNemar p.
Writes holm_pass9b.json next to this script.

"""
import json
from math import comb
from pathlib import Path

R2 = Path(__file__).resolve().parents[1]
T1 = json.load(open(R2 / "stats/t1_holm.json"))["a_printed"]["tests"]
PA = json.load(open(R2 / "stats/t2346_paired.json"))
T2 = json.load(open(R2 / "protocol/task2_summary.json"))

def mcn(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)

def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj

def d(path, label, para):
    r = PA
    for k in path.split("/"):
        r = r[k]
    return dict(paragraphs=para, printed="pass 7", test=label, b=r["A_only"], c=r["B_only"], source="campaign_v144/final/analysis/stats/t2346_paired.json")

new = [
    d("NN_live-LDA_fir770/all/A/diff", "NN_live vs LDA FIR-770, board A, 99,400", "P178"),
    d("NN_axi_emu-NN_live/all/A/diff", "NN_axi (emulated) vs NN_live, board A, 99,400", "P149"),
    d("NN_axi_emu-NN_live/all/B/diff", "NN_axi (emulated) vs NN_live, board B, 99,400", "P149"),
    d("boxcar-FIR/fresh/A/diff", "boxcar vs FIR, board A, 80,000 unused rows", "P194"),
    d("boxcar-FIR/fresh/B/diff", "boxcar vs FIR, board B, 80,000 unused rows", "P194"),
]
s = T2["mosaic"]["trainrow"]["vs_deployed_selected_models"]
new.append(dict(paragraphs="P189", printed="pass 7", test="map refit on training rows vs deployed map, kept seed, run-1 mix, 99,400",
                b=s["A_only"], c=s["B_only"], source="campaign_v144/final/analysis/protocol/task2_summary.json"))
ARCH = json.load(open(R2 / "arch/arch_sweep2_src_v144.json"))
for a in ("seg_hgb", "bin_gru"):   # pass 8, P178: the two nonlinear models significantly below LDA after replay
    r = ARCH[a]["loop20k_vs_t4"]
    new.append(dict(paragraphs="P178", printed="pass 8", test=f"{a} vs LDA, loop20k", b=r["b"], c=r["c"], source="campaign_v144/final/analysis/arch/arch_sweep2_src_v144.json"))
# pass 9: the pulse-gain arms on the full split (P201) and LDA_live against NN_live (P152)
ARMS = json.load(open(R2.parent / "inloop/arms/arms_full_analysis.json"))
for b in "AB":
    r = ARMS[b]["paired_vs_nominal"]["zero"]
    new.append(dict(paragraphs="P201", printed="pass 9", test=f"zero vs nominal pulse gain, board {b}, 99,400", b=r["A_only"], c=r["B_only"],
                    source="campaign_v144/final/inloop/arms/arms_full_analysis.json"))
r = json.load(open(R2.parents[2] / "firmware_v1.44/variants/lda_gate/lda_csim_score.json"))["sets"]["headline_mosaic"]["NN_live_vs_LDA_fixed"]
new.append(dict(paragraphs="P152", printed="pass 9", test="NN_live vs LDA_live model, stored windows, headline 99,400", b=r["A_only"], c=r["B_only"],
                source="firmware_v1.44/variants/lda_gate/lda_csim_score.json"))
r = json.load(open(R2.parents[2] / "firmware_v1.44/variants/lda_gate/board/live/check_board_lda.json"))["sets"]["headline_mosaic"]["NN_live_vs_LDA_live"]
new.append(dict(paragraphs="P152", printed="pass 9", test="NN_live (v1.44 session) vs LDA_live on the board, headline 99,400", b=r["A_only"], c=r["B_only"],
                source="firmware_v1.44/variants/lda_gate/board/live/check_board_lda.json"))
# pass 9b: NN_live against LDA FIR-770 on the 80,000 unused rows of each board (P194)
for b in "AB":
    t = d(f"NN_live-LDA_fir770/fresh/{b}/diff", f"NN_live vs LDA FIR-770, board {b}, 80,000 unused rows", "P194"); t["printed"] = "pass 9b"; new.append(t)
tests = [dict(t) for t in T1] + new
for t in tests:
    t["p"] = mcn(t["b"], t["c"])
for t, h in zip(tests, holm([t["p"] for t in tests])):
    t["holm"] = h
surv = [t for t in tests if t["holm"] < 0.05]
out = dict(n=len(tests), n_round2=len(T1), n_new=len(new), nominal=sum(t["p"] < 0.05 for t in tests), survivors=len(surv), tests=tests)
(Path(__file__).parent / "holm_pass9b.json").write_text(json.dumps(out, indent=1))
print(f"{len(tests)} tests ({len(T1)} + {len(new)} new), nominal {out['nominal']}, Holm survivors {len(surv)}")
for t in sorted(surv, key=lambda t: t["holm"]):
    print(f"  {t['paragraphs']:<10} {t['test'][:80]:<80} p {t['p']:.3g}  Holm {t['holm']:.3g}")
