"""Writes paper_notes/v144_exempt.tsv: every number in the draft that is correct without coming from a v1.44 measurement, with why.
Written per paragraph, so an exemption cannot quietly cover the same number somewhere else. Numbers not listed stay UNCLASSED in
check_paper_v144.py. Class 'open' means it needs a person: it is listed so that it is visible, and the checker reports it separately.

  python campaign_v144/final/analysis/make_v144_exempt.py
"""
import csv
import json
from pathlib import Path

DESIGN = "design constant or clock, not a measurement"
DATA = "property of the public dataset or source device, measured offline or cited"
OFF = "offline result on raw traces, no hardware involved"
CALC = "arithmetic from design constants"
ROUND = "rounded form of a ledger value"
SIZE = "sample size, row index or training-set size"
TEST = "statistical convention"
L = {
 "P1": {"176": ROUND}, "P3": {"96.01": OFF, "96.00": OFF, "96": "value reported by [16]", "16.3": DESIGN + ": 9 cycles, confirmed by S_NN and RTL sim", "176": ROUND, "1,340": ROUND},
 "P10": {"96": "value reported by [16]", "32.25": "value reported by [16]", "16": "value reported by [16]"}, "P11": {"32.25": "value reported by [16]"}, "P17": {"176": ROUND},
 "P24": {"0.2": DATA, "6.32": DATA, "1.5": DATA, "0.4": DATA, "32": DATA, "2.5": DATA, "770": DATA, "3.25": DATA, "4.50": DATA},
 "P39": {"16.3": DESIGN, "552.96": DESIGN}, "P40": {"1.808": DESIGN, "10": "the 10-90% definition", "90": "the 10-90% definition", "17": CALC + ": moving-sum rise"},
 "P49": {"96.06": "value reported by [35] (LUNA)"}, "P50": {"31": "value reported by [47]", "52": "value reported by [47]"},
 "P60": {"3.0": "PYNQ version (3.0.1) on both boards, recorded in requirements.txt", "0.2": "QICK host software version (0.2.414), as installed", "7864.32": DESIGN, "4423.68": DESIGN, "552.96": DESIGN, "1.808": DESIGN},
 "P61": {"770": DATA, "11,000": DESIGN, "99": DESIGN, "3.25": DATA, "2.5": DATA, "1.808": DESIGN, "1.39": CALC}, "P62": {"500": DESIGN + ": calibration shots"},
 "P67": {"770": DATA, "95": TEST}, "P68": {"20": "qualitative band edge", "60": "qualitative band edge"},
 "P71": {"−56": "phase of the swap session, in the ledger as arg(k)", "−97": "phase of the swap session, in the ledger as arg(k)", "20": "phrst shots per program", "4,000": SIZE},
 "P76": {"900,000": DATA, "0.2": DATA, "1.808": DESIGN, "1.80": CALC, "3.87": OFF}, "P78": {"3.25": DATA, "865": DATA, "0.2": DATA, "3.80": OFF, "3.93": OFF},
 "P79": {"9,999": SIZE, "110,000": SIZE, "299,999": SIZE, "20": "validation split", "10,000": SIZE, "109,999": SIZE, "1,000": SIZE, "1,599": SIZE},
 "P80": {"576": DESIGN, "640": "window length compared"}, "P84": {"+0.32": OFF, "1.4": OFF, "2.0": OFF, "1,540": DATA, "4.0": OFF, "8.2": OFF, "3.80": OFF, "3.93": OFF, "3.86": OFF},
 "P85": {"10,000": SIZE, "50,000": SIZE, "30,000": SIZE, "70": ROUND + ": 0.36 of 0.49"}, "P86": {"+2.73": OFF, "−2.09": OFF, "1.65": OFF, "500": OFF},
 "P88": {"10,000": SIZE, "500": OFF, "770,": DATA, "770": DATA, "95": TEST, "50,000": SIZE, "96.05": OFF},
 "P92": {"770": DESIGN, "576": DESIGN}, "P93": {"±0.2": "seed spread at 10,000 rows, from the retrained networks", "10,000": SIZE, "10": "training hyperparameter: learning rate 10^-3", "32,": "training hyperparameter: batch size"},
 "P94": {"16,6": DESIGN, "32,20": DESIGN, "48,32": DESIGN, "40,8": DESIGN, "32,16": DESIGN, "18,8": DESIGN},
 "P95": {"576": DESIGN, "770": DESIGN, "2.5": DATA, "351": CALC + ": 194 samples at 1.808 ns", "1.87": CALC},
 "P97": {"95": TEST, "3.25": DATA, "576": DESIGN, "0.10": ROUND, "640": "window length compared", "100": "unit of the axis", "32": DATA, "544": "read off Fig. 5(b), ledger"},
 "P99": {"96.00": OFF, "100,": SIZE, "100": SIZE, "500": SIZE, "95": TEST, "95.78": OFF, "95.80": "value reported by [16]", "96.04": "value reported by [16]"},
 "P106": {"770": DESIGN, "1,540": DESIGN, "15.5": CALC + ": 1,540 cycles at 100 MHz plus inference", "15.4": CALC + ": 1,540 cycles at 100 MHz", "16.3": DESIGN, "14": "NN_axi DSP count, ledger table", "95.5": ROUND},
 "P107": {"770": DESIGN, "1,540": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "2": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "32,20": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "48,32": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "40,8": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "18,8": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "32": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "16,384": "NN_axi 1.41 core as built into v1.44: neural_net4_tlast/firmware defines.h, parameters.h, NN_axi.cpp", "2023.1": "tool version", "10": DESIGN + ": HLS clock target", "15.5": CALC, "16.3": DESIGN},
 "P109": {"99.6": CALC, "1,152": DESIGN}, "P111": {"−1,0,": DESIGN}, "P120": {"16.3": DESIGN},
 "P122": {"576": DESIGN, "63": DESIGN + ": bit index and 31 cycles", "16": DESIGN + ": bit index", "15": DESIGN + ": bit index", "552.96": DESIGN, "491.52": DESIGN, "31": DESIGN, "16.3": DESIGN},
 "P124": {"576": DESIGN}, "P127": {"640": "equation layout artefact"}, "P130": {"0.5": DESIGN}, "P131": {"15": DESIGN, "16": DESIGN, "63": DESIGN, "512": DESIGN},
 "P133": {"176": ROUND, "25": CALC + ": 16.3 + 9.0 ns, both stated in Sec. VIII"}, "P135": {"11": DESIGN}, "P142": {"4423.68": DESIGN, "552.96": DESIGN, "16": DESIGN, "100.5": CALC, "11,": DESIGN, "−100": DESIGN, "16.3": DESIGN, "9.0": CALC},
 "P144": {"20": "shots in the capture", "−100": DESIGN, "11": DESIGN, "100": DESIGN}, "P145": {"16.3": DESIGN, "0.10": ROUND}, "P149": {"15.5": CALC, "552.96": DESIGN},
 "P154": {"160": ROUND + ": 337 minus 176", "176": ROUND}, "P155": {"576": DESIGN, "16.3": DESIGN, "63": DESIGN, "29": DESIGN, "16": DESIGN, "15": DESIGN, "491.52": DESIGN, "200": DESIGN, "256": DESIGN, "245.76": "QICK design constant: clk_core in firmware/projects/qick_tprocv2_4x2_standard/bd_2023-1.tcl at commit 779dffa", "204.8": "QICK design constant: clk_core in the same file on QICK main since 2026-09-16 (commit a24cc8e, merged in #432)", "552.96": DESIGN, "0.42": "QICK tProc IP alone, out-of-context place and route at c_clk 5.0 ns; a property of QICK's IP, not of a build of ours"},
 "P156": {"95": TEST}, "P82": {"23": "verify_no_leakage.py re-run 2026-11-06, 23/23: campaign_v144/final/analysis/verify_no_leakage.log"},
 "P162": {"2.03": DESIGN + ": tProc tick", "176": ROUND, "1.4": "v1.44 latency study: campaign_v144/final/latency", "0.6": "v1.44 latency study, same entry", "0.2": "v1.44 latency study, same entry"}, "P166": {"10": "equation number"},
 "P171": {"100": "shots per load", "40": "traces per slack", "17": "traces with decision 1", "−66": "slack value"},
 "P172": {"1039.9": CALC, "575": CALC, "1.216": CALC, "1.22": CALC, "1872": CALC, "176": ROUND, "91": CALC, "2.05": CALC}, "P177": {"1.808": DESIGN, "3.25": DATA},
 "P179": {"16": CALC + ": 16 DAC samples per 491.52 MHz cycle", "491": DESIGN},
 "P181": {"552.96": DESIGN, "100": DESIGN, "0.3": "detectable size at this n"}, "P183": {"576": DESIGN, "500": OFF}, "P184": {"32": DATA, "4.5": "assignment error, rounded from the headline"},
 "P186": {"16.3": DESIGN, "1,340": ROUND, "176": ROUND},
}
OPEN = {
}
# numbers that match a v1.43 ledger value only by coincidence, and numbers in the v1.44 wording
_A = {
 "P40": {"50": "the 50% point, a definition"}, "P50": {"860": "value reported by [43]", "620": "value reported by [43]", "270": "value reported by [43]", "10": "value reported by [43]: 9.93% rounded"},
 "P61": {"50": DESIGN + ": 50 MHz carrier"}, "P71": {"−164": "phase of the swap session, in the ledger as arg(k)", "−143": "phase of the swap session, in the ledger as arg(k)"},
 "P85": {"60": ROUND + ": 0.34 of 0.56"}, "P93": {"50": "training hyperparameter: at most 50 epochs"}, "P104": {"600": SIZE},
 "P106": {"50": DESIGN + ": 5 cycles at 100 MHz"}, "P122": {"44": DESIGN + ": bit index"}, "P131": {"44": DESIGN + ": bit index"}, "P155": {"44": DESIGN + ": bit index"},
 "P144": {"50": DESIGN + ": 50 MHz pulse and the 50% crossing"}, "P149": {"50": DESIGN + ": 5 cycles at 100 MHz"},
 "P156": {"50": "the 50% point, a definition", "0.26": ROUND + ": 0.251% and 0.265%"}, "P168": {"50": "the 50% point, a definition"},
 "P162": {"50": "the 50% point, a definition", "10": "number of loads, ledger row name", "1.2": "v1.44 latency study, per-shot s.d. 1.24-1.48 ns over 14 loads (campaign_v144/final/latency)",
          "1.5": "same", "0.7": "v1.44 latency study, largest sensitivity shift 0.74 ns (campaign_v144/final/latency/cold/B_c2.json)"},
 "P171": {"10": "number of loads, ledger row name"}, "P184": {"4.4": "assignment error, rounded from the headline (100 - 95.60)"},
}
# Appendices A-C (P188-P200)
_CR = "v1.44 calibration repeats, 8 per board on one load: s.d. of arg k and of the probe phase (campaign_v144/final/cal_repeat/cal_repeat_<host>.json)"
_PH = "v1.44 phase across loads, board A (campaign_v144/final/board2/A_phrst_probe_v144.json)"
_B = {
 "P189": {"500": DESIGN + ": calibration shots", "127": _PH + ", ledger 'Phase across loads'", "−121": _PH + ", ledger 'Phase across loads'",
          "125": _PH + ", ledger 'Phase across loads'", "58": _PH + ", ledger 'Phase across loads'", "−34": _PH + ", ledger 'Phase across loads'",
          "0.33": _PH + ": per-shot s.d. per load without phrst, 0.33-0.40 deg", "0.40": _PH + ": per-shot s.d. per load without phrst, 0.33-0.40 deg",
          "32": CALC + ": separation of the two phrst clusters from the ledger means (-1.9 vs -33.5 deg)", "9": _PH + ": per-shot s.d. with phrst, 8.7-9.2 deg"},
 "P190": {"0.87": _CR, "1.00": _CR, "0.05": _CR, "0.10": _CR, "100": DESIGN + ": the 100 MHz mixing image",
          "0.086": ROUND + ": ledger 'Drift, 3 h' s.d.", "0.084": ROUND + ": ledger 'Drift, 3 h' s.d.", "0.26": "ledger 'Drift, 3 h', p of the paired comparison"},
 "P191": {"600": SIZE, "1,000": SIZE, "1,599": SIZE, "11": DESIGN + ": boxcar length M", "−0.25": "boxcar map delay s (box_domain_map.json)",
          "+0.37": "earlier build, offline: domain-map ablation of 2026-10-01 (results/phase0_calibration_ablation.json); said so in the text"},
 "P193": {"9,999": SIZE, "110,000": SIZE, "299,999": SIZE, "10,000": SIZE, "109,999": SIZE, "1,000": SIZE, "1,599": SIZE, "20": "validation split",
          "12": CALC + ": sum of the ledger's DAC-clipped shots, 7 + 5"},
 "P194": {"23": "verify_no_leakage.py re-run 2026-11-06, 23/23: campaign_v144/final/analysis/verify_no_leakage.log", "1,000": SIZE, "1,599,": SIZE, "1,599": SIZE},
 "P195": {"95": TEST, "0.0030": ROUND + ": ledger 'Late-rate 95% upper bound'"},
 "P196": {"576": DESIGN, "640": "window length compared", "770": "window length compared"},
 "P198": {"200": "ledger 'Boxcar vs raw buffer', 200/200 per board", "400": "v1.44 tProc decision test, 400/400 per board (campaign_v144/final/tests/<board>_tproc_decision.json)",
          "0.4": DESIGN + ": fault trigger offset of the binding-fault test (binding_fault_check.py)", "25": "v1.44 binding-fault test counts (campaign_v144/final/tests/<board>_binding_fault.json)"},
 "P199": {"50": "the 50% point, a definition"}, "P200": {"21.5": "ledger 'Phase difference of the boards in that session'"},
}
for _d in (_A, _B):
    for _p, _x in _d.items():
        L.setdefault(_p, {}).update(_x)
root = Path(__file__).resolve().parents[3]
# Paragraph keys above are those of the draft before its first rewrite. remap_exempt_paras.py moves each
# exemption to the paragraph that now holds it; exemptions whose number left the draft are dropped.
_pm = Path(__file__).resolve().parent / "v144_exempt_pmap.json"
if True:   # required: without the map every key below is wrong
    import json
    _m = json.load(open(_pm, encoding="utf-8"))
    for _t in (L, OPEN):
        _nt = {}
        for _p, _x in _t.items():
            for _n, _why in _x.items():
                if f"{_p}|{_n}" in _m:
                    _nt.setdefault(_m[f"{_p}|{_n}"], {})[_n] = _why
        _t.clear(); _t.update(_nt)
# exemptions for numbers the rewrite added, keyed by the new paragraph numbers
_TP = ROUND + ": ledger 'tProc path', FIR path 447.6 / 450.0 ns"
_F2 = "paper_figures/fig2/fig2_values.json (offline, real training data)"
NEW = {
 "P1": {"00": "IEEE template placeholder", "0000": "IEEE template placeholder"}, "P2": {"10.1109": "IEEE DOI prefix, template"},
 "P7": {"450": _TP}, "P17": {"450": _TP}, "P155": {"450": _TP, "25": CALC + ": boxcar path, (9 + 5) cycles at 552.96 MHz = 25.3 ns",
                                                  "114": CALC + ": 175.9 - 62 ns, ledger 'Loop latency'"},
 "P175": {"25": CALC + ": boxcar path, (9 + 5) cycles at 552.96 MHz = 25.3 ns"},
 "P188": {"100": ROUND + ": ledger 'Loop latency' S_conv of the two load groups, 100-102 ns"},
 "P39": {"16": CALC + ": 10-90% rise of the 11-sample moving sum, 0.8 x 11 x 1.808 ns = 15.9 ns"},
 "P62": {"50": DESIGN + ": 50 MHz carrier", "200": DESIGN + ": tProc core clock"},
 "P77": {"3.86": _F2 + ": model_d.real_jit 3.861", "3.80": _F2 + ": real_d_range 3.797", "3.93": _F2 + ": real_d_range 3.927"},
 "P85": {"1.5": OFF + ": common-mode offset ratio", "1.9": OFF + ": common-mode offset ratio"},
 "P80": {"50,000": SIZE}, "P195": {"5,000": DATA + ": class-block length of the released test file"},
 "P95": {"640": "window length compared", "1,035": CALC + ": 1.87 us / 1.808 ns"},
 "P180": {"1.04": CALC + ": 576 x 1.808 ns", "1,035": CALC + ": 1.87 us / 1.808 ns", "1.87": CALC + ": 576 x 3.25 ns of recorded readout"},
 "P134": {"120": DESIGN + ": QICK readout FIR length"},
 "P145": {"−30": "threshold of the comparison band"},
 "P151": {"0.35": "v1.44 routed bus-skew report, 2.352 ns against 2.00 ns (paper_tables/table3 BUS_SKEW_MISS_NS)", "2.00": DESIGN + ": set_bus_skew constraint"},
 "P184": {"0.35": "v1.44 routed bus-skew report, 2.352 ns against 2.00 ns (paper_tables/table3 BUS_SKEW_MISS_NS)", "2.00": DESIGN + ": set_bus_skew constraint"},
 "P157": {"0.32": "v1.44 routed timing, tProc clock domain slack in the full design"},
 "P166": {"400": SIZE + ": 4 loads x 100 shots"},
 "P181": {"0.018": "earlier build (v1.40L1), offline: campaign_v140L1/arch_aug.json; said so in the text; S2 carries it to v1.44",
          "16,000": "earlier build (v1.40L1), offline: campaign_v140L1/arch_aug.json; said so in the text",
          "95.59": "earlier build (v1.40L1), offline: campaign_v140L1/arch_aug.json; said so in the text",
          "0.2": OFF + ": campaign_v140L1/arch_sweep.json, raw traces"},
 "P182": {"491.52": DESIGN, "+0.002": "scaling_study/FINDINGS.md: out-of-context runs of the classifier kernel (v1.41 RTL, unchanged in v1.44), not an SoC build", "32": "unit count that failed timing"},
 "P186": {"0.2": OFF + ": the raw-trace gain of P181", "0.3": OFF + ": the raw-trace gain of P181",
          "200": CALC + ": 0.2-0.3 points at the T1 = 32 us rate of t/T1 to t/(3 T1)", "300": CALC + ": same"},
 "P202": {"95": TEST},
 "P153": {"49,400": SIZE + ": board A run 1, rows 0-49,999 less the 600 map rows", "50,000": SIZE + ": board B run 1, rows 50,000-99,999"},
}
# NEW's keys are paragraphs of the draft after its first rewrite. Text passes 2 and 3 moved paragraphs; this map puts
# each one on its paragraph of the draft after pass 3, checked by hand against the text, number by number.
NEW_KEYMAP = {"P155": "P153", "P175": "P173", "P188": "P186", "P39": "P202", "P77": "P197", "P85": "P197", "P195": "P193",
              "P95": "P93", "P180": "P178", "P134": "P132", "P145": "P143", "P151": "P149", "P184": "P182", "P157": "P155",
              "P166": "P164", "P181": "P179", "P182": "P180", "P186": "P184", "P202": "P203", "P153": "P151"}
for _p, _x in NEW.items():
    L.setdefault(NEW_KEYMAP.get(_p, _p), {}).update(_x)
# numbers that pass 3 added or moved, keyed by the live draft after pass 3
_S3 = "campaign_v144/final/analysis/s3/s3_live_window_lda.json"
PASS3 = {
 "P66": {"769": DATA + ": last sample index of a 770-sample trace"},
 "P69": {"±0.9": CALC + ": half-width of the 95% intervals of ledger 'Calibration swap' (0.84-0.89 points)"},
 "P79": {"836": DATA + ": per-sample noise s.d. over 20,000 fit-pool rows, 836.2-837.3 (campaign_v144/final/analysis/stats/t5_estimators.json)"},
 "P83": {"13": "v1.44 leakage audit, 13 checks: campaign_v144/final/analysis/verify_no_leakage_v144.log"},
 "P178": {"320": SIZE + ": window of 320 recorded samples, " + _S3},
 "P179": {"16,000": SIZE + ": shots scored in S2 (ledger 'Replay-channel augmentation')", "576": DESIGN + ": NN_live window", "770": DATA},
 "P180": {"50": DESIGN + ": 50 MHz carrier", "4.8": ROUND + ": ledger 'Readout path', carriers up to 4800 MHz"},
 "P197": {"0.1": OFF + ": phase jitter of the generator, 0.1 rad (audit_fixes/R14)",
          "4.8": OFF + ": d of the three named noise models (audit_fixes/R14)"},
 "P201": {"16,6": DESIGN + ": fixed-point type ap_fixed<16,6>"},
 "P202": {"50": "the 50% point, a definition"},
 "P161": {"50": "subscript of L_50 in its defining equation"}, "P167": {"50": "subscript of L_50 in its defining equation"},
 "P203": {"1.0": DESIGN + ": maximum pulse gain of the pulse-gain arms (campaign_v144/final/inloop/arms/arms_analysis.json, arm_def)"},
}
for _p, _x in PASS3.items():
    L.setdefault(_p, {}).update(_x)
# Pass 5 deleted P20, P41 and P182 of the pass-3 numbering and split P153 into P153 + P153b.
# paper_notes/pass5_renumbering.json keeps the pass-3 labels in the new order (it equals the live draft after
# pass 5, paragraph for paragraph), so a paragraph's new number is its line number there. An exemption on the split
# P153 goes to the half that holds its number; one on a deleted paragraph is dropped.
_P5J = json.load(open(root / "paper_notes/pass5_renumbering.json", encoding="utf-8"))   # frozen from that file
_P5N = {lab: f"P{i + 1}" for i, lab in enumerate(_P5J["order"])}
_P5T = {"P153": _P5J["P153"]}
PASS5_DROPPED = []
for _t in (L, OPEN):
    _nt = {}
    for _p, _x in _t.items():
        for _n, _why in _x.items():
            _lab = _p
            if _p == "P153" and _n.replace(",", "") not in _P5T["P153"].replace(",", ""):
                _lab = "P153b"
            if _lab not in _P5N:
                PASS5_DROPPED.append(f"{_p} {_n}")
                continue
            _nt.setdefault(_P5N[_lab], {})[_n] = _why
    _t.clear(); _t.update(_nt)
# numbers that pass 6 added, keyed by the draft after pass 5
PASS6 = {
 "P194": {"500": OFF + ": matched-filter fidelity peaks near 500 samples, real data, 5 seeds (audit_fixes/R8_R1/out/fig3_truncation_curves.npz)"},
}
for _p, _x in PASS6.items():
    L.setdefault(_p, {}).update(_x)
# numbers that pass 8 added, keyed by the numbering of the draft after pass 6 (unchanged by passes 7 and 8)
PASS8 = {
 "P156": {"0.0030": CALC + ": exact zero-event one-sided 95% bound 1 - 0.05^(1/99,400)", "2.03": DESIGN + ": one DAC-fabric cycle at 491.52 MHz"},
 "P197": {"2023.1": "tool version"},
}
PASS9 = {
 "P152": {"200": DESIGN + ": tProc core clock of v1.44 (clk_core, 5.001 ns in the routed timing report)",
          "245.76": DESIGN + ": QICK's stock tProc core clock, used by variant build tproc245",
          "576": DESIGN + ": NN_live's window length, shared by the LDA core"},
 "P185": {"1,035": CALC + ": 576 samples x 3.25 / 1.808 ns, as in P177"},
}
PASS9B = {
 "P68": {"500": DESIGN + ": carrier frequency of the converter sweep", "1,500": DESIGN + ": carrier frequency of the converter sweep",
         "0.5": ROUND + ": 0.49-0.53 ns, edge s.d. at the 500 and 1,500 MHz carriers"},
 "P127": {"16,6": DESIGN + ": logit type ap_fixed<16,6>, as in P199"},
 "P147": {"3.98": CALC + ": 2 x 2.035 ns (DAC clock) - 0.035 - 0.051 ns clock uncertainty (firmware_v1.44/reports/v144_worst_setup_per_group.rpt)"},
 "P103": {"2,048": DESIGN + ": NN_axi's result buffer, 2,048 32-bit words (8 KB) in the block design (NN_axi.h)"},
 "P175": {"63": DESIGN + ": live_res_cdc word layout", "60": DESIGN + ": live_res_cdc word layout", "32": DESIGN + ": live_res_cdc word layout",
          "31": DESIGN + ": live_res_cdc word layout"},
 "P154": {"32": DESIGN + ": two 256-bit words of 16 samples"},
 "P172": {"16.3": CALC + ": 9 cycles at 552.96 MHz, as in P121"},
 "P178": {"96.00": OFF + ": Table II, our variant on the 100,000 raw test traces"},
}
PASS10 = {
 "P124": {"640": DESIGN + ": Eq. (6) flattened to text, where the threshold 1/64 runs into the case value 0"},
}
PASS11 = {
 "P56": {"96.00": OFF + ": Table II, our variant on the 100,000 raw test traces (as in P178)"},
 "P89": {"20260904": DESIGN + ": the deployed training seed, recorded by the export (results/last_export_seed_w576_box.txt)"},
 "P201": {"0.1": ROUND + ": the session differences just listed, 0.06-0.12 points (ledger rows: board B in-loop vs gate-idle, board A nominal arm vs run 2, same LDA in a later session)"},
}
for _p, _x in PASS11.items():
    L.setdefault(_p, {}).update(_x)
for _p, _x in PASS10.items():
    L.setdefault(_p, {}).update(_x)
for _p, _x in PASS9B.items():
    L.setdefault(_p, {}).update(_x)
for _p, _x in PASS9.items():
    L.setdefault(_p, {}).update(_x)
for _p, _x in PASS8.items():
    L.setdefault(_p, {}).update(_x)
with open(root / "paper_notes" / "v144_exempt.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    f.write("# paragraph\tnumber\tclass\treason. Generated by campaign_v144/final/analysis/make_v144_exempt.py; edit that, not this.\n")
    for table, cls in ((L, "ok"), (OPEN, "open")):
        for p in sorted(table, key=lambda x: int(x[1:])):
            for n, why in table[p].items():
                w.writerow([p, n, cls, why])
print("exempt written; dropped with pass 5 (paragraph deleted):", ", ".join(PASS5_DROPPED) or "none")
