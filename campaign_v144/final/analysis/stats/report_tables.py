"""Formats the markdown tables of REPORT.md from t2346_paired.json (tasks 2, 3, 4, 6). Writes report_tables.md."""
import json
from pathlib import Path
OUT = Path(__file__).resolve().parent
R = json.load(open(OUT / "t2346_paired.json"))
f3 = lambda x: f"{x:+.3f}"
ci = lambda c: f"[{c[0]:+.3f}, {c[1]:+.3f}]"
pp = lambda p: f"{p:.2g}" if p < 0.01 else f"{p:.2f}"
md = []


def table(label, subsets=("all",), title=""):
    md.extend([f"### {title or label}", "",
               "| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |",
               "|---|---|---|---|---|---|---|---|---|---|---|"])
    for sn in subsets:
        for nm in ("A", "B", "mosaic", "pooled_AB"):
            o = R[label][sn][nm]
            if nm == "pooled_AB":
                md.append(f"| {sn} | both boards pooled (row-clustered) | | | {f3(o['dF'])} | {ci(o['ci95_boot'])} | {ci(o['ci95_normal_cluster'])} | "
                          f"{o['A_only']} vs {o['B_only']} ({o['n_shots']:,} shots) | sign-flip {pp(o['p_signflip'])} (naive summed McNemar {pp(o['p_exact_naive_summed'])}) | "
                          f"{o['margin95']:.3f} | {o['margin90_TOST']:.3f} |")
            else:
                d = o["diff"]
                md.append(f"| {sn} | {'board ' + nm if nm != 'mosaic' else 'run-1 mosaic'} | {o['fid_a']['fid']:.3f} | {o['fid_b']['fid']:.3f} | {f3(d['dF'])} | "
                          f"{ci(d['ci95_boot'])} | {ci(d['ci95_normal'])} | {d['A_only']} vs {d['B_only']} | {pp(d['p_exact'])} | {d['margin95']:.3f} | {d['margin90_TOST']:.3f} |")
    md.append("")


for mk in ("fir770", "fir576", "box576"):
    table(f"NN_live-LDA_{mk}", ("all",), f"NN_live - LDA ({mk}), 99,400 rows")
for mk in ("fir770", "fir576", "box576"):
    table(f"NN_live-LDA_{mk}", ("fresh", "dev"), f"NN_live - LDA ({mk}), fresh 80,000 vs development 19,400")
table("boxcar-FIR", ("all", "fresh", "dev"), "boxcar NN_live - FIR-path network (emulated), all / fresh / dev")
table("NN_axi_emu-NN_live", ("all", "fresh", "dev"), "NN_axi (EMULATED on the live session's FIR buffer) - NN_live")
table("NN_axi_emu-LDA_fir770", ("all", "fresh", "dev"), "NN_axi (emulated) - LDA fir770")
md += ["### Fidelity by row subset (NN_live chip; NN_axi emulated)", "", "| Rows | Set | NN_live | 95% CI | NN_axi emulated | 95% CI |", "|---|---|---|---|---|---|"]
for sn in ("all", "fresh", "dev"):
    for nm in ("A", "B", "mosaic", "pooled_AB"):
        a = R["fidelity"][sn][nm]["nn"]; x = R["fidelity"][sn][nm]["axi770"]
        md.append(f"| {sn} | {nm} | {a['fid']:.3f} | [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}] | {x['fid']:.3f} | [{x['ci95'][0]:.2f}, {x['ci95'][1]:.2f}] |")
md.append("")
md += ["### board B - board A, same rows", "", "| Classifier | Rows | B - A | 95% CI normal | 95% CI bootstrap | B-only vs A-only | exact p |", "|---|---|---|---|---|---|---|"]
for lab in ("NN_live", "NN_axi emulated on live FIR", "NN_axi on chip"):
    for sn, d in R["B_minus_A"][lab].items():
        md.append(f"| {lab} | {sn} | {f3(d['dF'])} | {ci(d['ci95_normal'])} | {ci(d['ci95_boot'])} | {d['A_only']} vs {d['B_only']} | {pp(d['p_exact'])} |")
md.append(f"\nBoards' NN_live decisions agree on {100 * R['B_minus_A']['agreement_NN_live_all']:.2f}% of the 99,400 traces.\n")
c = R["checks"]["axi_chip_vs_emulated_on_live_fir_rows0_19999"]
md += ["### on-chip NN_axi (its own session) vs NN_axi emulated on the NN_live session's FIR buffer, rows 0-19,999 minus map rows", "",
       "| Board | decisions agree | on-chip NN_axi | emulated (live FIR) | chip - emulated | 95% CI | b vs c | exact p |", "|---|---|---|---|---|---|---|---|"]
for b in "AB":
    d = c[b]["chip_minus_emu"]
    md.append(f"| {b} | {100 * c[b]['agree']:.2f}% | {c[b]['chip_axi']['fid']:.3f} | {c[b]['emu_axi_live_fir']['fid']:.3f} | {f3(d['dF'])} | {ci(d['ci95_boot'])} | {d['A_only']} vs {d['B_only']} | {pp(d['p_exact'])} |")
md.append(f"\nBoxcar emulator equals the chip's NN_live decision on {R['checks']['box_emu_eq_chip']} of 100,000 shots per board.\n")
(OUT / "report_tables.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
