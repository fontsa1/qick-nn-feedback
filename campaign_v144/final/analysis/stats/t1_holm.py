"""Holm multiplicity over explicit test families, on the CURRENT ledger.

Every p is recomputed as an exact two-sided McNemar p from its discordant counts (b, c), as S4 does.
Families:
  (a) printed   every p-value printed in the submitted draft (paragraph numbers below), one test per distinct
                comparison (a value printed twice, e.g. P93 and P194, counts once); a printed bound ("p >= 0.10" in P95,
                "p <= 0.002" in P178, "p >= 0.19" in P201) is expanded into the tests it summarises, with their stored counts.
  (b) S4        s4_multiplicity_v144.py's own logic, verbatim, re-run on the current ledger (its F1-F6 families; note
                that its family() puts the nine S5 "vs NN_live" ledger rows into F2 window length). Also (b') with
                those nine rows moved to their own family F7 "linear vs NN_live, 99,400".
  (c) S4 + P178 (b) plus P178's four augmentation tests (arch_aug_v144.json, vs_lda_clean), as family F8.
  (d) headline  the comparisons the paper's central claims rest on (abstract P7, P14, P139, P149, P184, P201):
                NN_live vs LDA per board for FIR-770 / FIR-576 / boxcar-576 on the 99,400 traces (lda_99400.json);
                boxcar vs FIR 99,400; boards A vs B NN_live 99,400; NN_axi vs NN_live on the same rows, each board;
                in-loop vs gate-idle, each board, 99,400.
Holm within each family; for (b)/(c) also Holm over all members. Writes t1_holm.json, t1_holm.md.

"""
import json, re
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
LEDGER = ROOT / "paper_notes/V144_RESULTS.md"
AN = ROOT / "campaign_v144/final/analysis"

def mcn(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)

def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj

# ---------- ledger tests, parsed exactly as S4 does
def s4_family(sec, key):
    if sec == "Linear baselines":
        return "F2 window length"
    if sec.startswith("Drift"):
        return "F3 drift"
    if sec == "Boxcar vs FIR":
        return "F4 front end"
    return "F1 hardware equivalence"

led = []; sec = None
for ln in LEDGER.read_text(encoding="utf-8").splitlines():
    if ln.startswith("## "):
        sec = ln[3:].strip(); continue
    if not ln.startswith("| ") or "p = " not in ln:
        continue
    key, val = [x.strip() for x in ln.strip("|").split("|")[:2]]
    m = re.search(r"(\d+) vs (\d+)", val)
    if m and "raw / replayed" not in key:
        led.append(dict(family=s4_family(sec, key), section=sec, test=key, b=int(m[1]), c=int(m[2]), ledger_value=val))
L = {(t["section"], t["test"]): t for t in led}
ARCH = json.load(open(AN / "arch/arch_sweep2_src_v144.json"))
AUG = json.load(open(AN / "s2/arch_aug_v144.json"))
ARMS = json.load(open(ROOT / "campaign_v144/final/inloop/arms/arms_analysis.json"))
_R5 = json.load(open(ROOT / "audit_fixes/R5/evaluate_results.json"))   # the three offline seed pairs of Table II
T2 = {"paired_offline_seed_mcnemar": [m for m in _R5["mcnemar"] if m["set"] == "test100k" and m["b"].startswith("ours_")
                                      and m["a"] in _R5["groups"]["exact_lr1e-3"]["test100k"]["runs"]]}
assert len(T2["paired_offline_seed_mcnemar"]) == 3
LDA = json.load(open(ROOT / "campaign_v144/final/analysis/offline/lda_99400.json"))

def lt(sec, test):
    t = L[(sec, test)]; return dict(test=f"{sec}: {test}", b=t["b"], c=t["c"], source="paper_notes/V144_RESULTS.md")

def arch(arm, ev):
    r = ARCH[arm][f"{ev}_vs_t4"]
    return dict(test=f"{arm} vs LDA, {ev}", b=r["b"], c=r["c"], source="campaign_v144/final/analysis/arch/arch_sweep2_src_v144.json")

def aug(arm):
    r = AUG[f"{arm}_aug"]["vs_lda_clean"]
    return dict(test=f"{arm} trained on augmented data vs LDA, board A replay, 16,000", b=r["b"], c=r["c"],
                source="campaign_v144/final/analysis/s2/arch_aug_v144.json")

def arm(board, a):
    r = ARMS[board]["paired_vs_nominal"][a]
    return dict(test=f"pulse-gain arm {a} vs nominal, board {board}, 15,000", b=r["A_only"], c=r["B_only"],
                source="campaign_v144/final/inloop/arms/arms_analysis.json")

def seed(i):
    r = T2["paired_offline_seed_mcnemar"][i]
    return dict(test=f"retrain of [16] vs our variant, {r['a']} vs {r['b']}, 100,000 offline", b=r["a_only_correct"],
                c=r["b_only_correct"], source="audit_fixes/R5/evaluate_results.json")

def ldat(st, mk):
    r = LDA["sets"][st][f"NN_live_vs_{mk}"]
    return dict(test=f"NN_live vs LDA {mk}, {st}", b=r["A_only"], c=r["B_only"], source="campaign_v144/final/analysis/offline/lda_99400.json")

LB = "Linear baselines"
printed = [  # (paragraphs, printed text, test)
    ("P93, P194", "p = 0.008", lt(LB, "LDA, 576 vs 640 samples, board A")),
    ("P93, P194", "p = 0.19", lt(LB, "LDA, 576 vs 640 samples, board B")),
    ("P194", "p = 0.31", lt(LB, "LDA, 770 vs 640 samples, board A")),
    ("P194", "p = 0.76", lt(LB, "LDA, 770 vs 640 samples, board B")),
    *[("P95", "p >= 0.10 (bound)", seed(i)) for i in range(3)],
    ("P139", "p = 0.58", lt("Boxcar vs FIR", "Boxcar vs FIR, 19,400")),
    ("P139, P193", "p = 0.0007", lt("Boxcar vs FIR", "Boxcar vs FIR, 99,400")),
    ("P149", "p = 0.07", lt("NN_axi", "Board A, vs NN_live run on the same rows")),
    ("P178", "p = 0.84", arch("cnn1d", "loop20k")),
    *[("P178", "p <= 0.002 (bound)", aug(a)) for a in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d")],
    ("P178", "p = 0.20", lt(LB, "LDA, window 576, run 1, 99,400 rows, vs NN_live on the same shots")),
    ("P178", "p = 0.09", lt(LB, "LDA, window 770, run 1, 99,400 rows, vs NN_live on the same shots")),
    ("P201", "p = 0.052", lt("NN_live", "Boards A vs B, identical 99,400 traces")),
    ("P201", "p = 0.31", lt("In the loop", "Boards A vs B")),
    ("P201", "p = 0.24", lt("NN_axi", "Boards A vs B")),
    ("P201", "p = 0.02", lt("In the loop", "Board B, vs its gate-idle run")),
    ("P201", "p = 0.53", lt("In the loop", "Board A, vs its gate-idle run")),
    ("P201", "p = 0.90", lt("In the loop", "Board A, vs gate-idle, 19,400 subset")),
    ("P201", "p = 0.33", lt("In the loop", "Board B, vs gate-idle, 19,400 subset")),
    *[("P201", "p >= 0.19 (bound)", arm(b, a)) for b in "AB" for a in ("zero", "max", "gateoff")],
]
fam_a = []
for para, txt, t in printed:
    fam_a.append(dict(paragraphs=para, printed=txt, **t))

# ---------- (b) S4 verbatim on the current ledger
s4 = [dict(family=t["family"], test=f"{t['section']}: {t['test']}", b=t["b"], c=t["c"], source="paper_notes/V144_RESULTS.md") for t in led]
for a in ("seg_hgb", "seg_mlp", "bin_mlp", "cnn1d", "bin_gru"):
    for ev, fam in (("loop20k", "F5 networks after replay"), ("src20k", "F6 networks on raw traces")):
        s4.append(dict(family=fam, **arch(a, ev)))
s4b = [dict(t, family="F7 linear vs NN_live, 99,400" if "vs NN_live on the same shots" in t["test"] else t["family"]) for t in s4]
s4c = s4b + [dict(family="F8 augmentation vs LDA (P178)", **aug(a)) for a in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d")]

# ---------- (d) headline claims
fam_d = [*[dict(claim="P7/P14/P178/P184: at the level of linear discrimination", **ldat(st, mk))
           for st in ("A_full", "B_full") for mk in ("fir770", "fir576", "box576")],
         dict(claim="P139: boxcar costs no fidelity", **lt("Boxcar vs FIR", "Boxcar vs FIR, 99,400")),
         dict(claim="P201: boards differ by < 0.14 points", **lt("NN_live", "Boards A vs B, identical 99,400 traces")),
         dict(claim="P149: shorter window costs little (NN_axi vs NN_live)", **lt("NN_axi", "Board A, vs NN_live run on the same rows")),
         dict(claim="P149: shorter window costs little (NN_axi vs NN_live)", **lt("NN_axi", "Board B, vs NN_live run on the same rows")),
         dict(claim="P201: the loop does not change fidelity", **lt("In the loop", "Board A, vs its gate-idle run")),
         dict(claim="P201: the loop does not change fidelity", **lt("In the loop", "Board B, vs its gate-idle run"))]

def run(tests, by_family):
    for t in tests:
        t["p"] = mcn(t["b"], t["c"])
    if by_family:
        for f in sorted({t["family"] for t in tests}):
            idx = [i for i, t in enumerate(tests) if t["family"] == f]
            for i, h in zip(idx, holm([tests[i]["p"] for i in idx])):
                tests[i]["holm_family"] = h; tests[i]["family_size"] = len(idx)
    for t, h in zip(tests, holm([t["p"] for t in tests])):
        t["holm_all"] = h
    s = dict(n=len(tests), nominal=sum(t["p"] < .05 for t in tests), holm_all=sum(t["holm_all"] < .05 for t in tests))
    if by_family:
        s["holm_family"] = sum(t["holm_family"] < .05 for t in tests)
    s["survivors_holm_all"] = [t["test"] for t in tests if t["holm_all"] < .05]
    if by_family:
        s["survivors_holm_family"] = [t["test"] for t in tests if t["holm_family"] < .05]
    return s

res = {}
fam_a2 = [dict(t) for t in fam_a if t["printed"] not in ("p >= 0.10 (bound)", "p >= 0.19 (bound)")]
for name, tests, byf in (("a_printed", fam_a, False), ("a2_printed_bounds_not_expanded", fam_a2, False), ("b_S4_verbatim", s4, True), ("b2_S4_F7_split", s4b, True),
                         ("c_S4_plus_P178", s4c, True), ("d_headline", fam_d, False)):
    res[name] = dict(summary=run(tests, byf), tests=tests)
    print(name, json.dumps({k: v for k, v in res[name]["summary"].items() if not k.startswith("surv")}))
    for t in tests:
        if t["p"] < .05:
            print(f"   {t['test']}: {t['b']} vs {t['c']}, p {t['p']:.3g}, Holm-all {t['holm_all']:.3g}"
                  + (f", Holm-family {t['holm_family']:.3g}" if byf else ""))
(OUT / "t1_holm.json").write_text(json.dumps(res, indent=1))

def f(p):
    return f"{p:.2g}" if p < 0.01 else f"{p:.3f}"

md = ["# Holm over explicit families (generated by t1_holm.py)", ""]
for name, r in res.items():
    s = r["summary"]; byf = "holm_family" in s
    md += [f"## {name}: {s['n']} tests, nominal p < 0.05: {s['nominal']}, Holm over the family: {s['holm_all']}"
           + (f", Holm within sub-families: {s['holm_family']}" if byf else ""), ""]
    cols = ["Paragraph", "Printed"] if name.startswith("a") else (["Claim"] if name == "d_headline" else ["Sub-family"])
    md += ["| " + " | ".join(cols + ["Test", "b vs c", "exact p", "Holm (all)"] + (["Holm (sub-family)"] if byf else [])) + " |",
           "|" + "---|" * (len(cols) + 4 + byf)]
    for t in r["tests"]:
        c0 = [t["paragraphs"], t["printed"]] if name.startswith("a") else ([t["claim"]] if name == "d_headline" else [t["family"]])
        md.append("| " + " | ".join(c0 + [t["test"], f"{t['b']} vs {t['c']}", f(t["p"]), f(t["holm_all"])]
                                    + ([f(t["holm_family"])] if byf else [])) + " |")
    md.append("")
(OUT / "t1_holm.md").write_text("\n".join(md), encoding="utf-8")
