"""Table III: implementation — routed resources (v1.44) and inference latency,
IEEE TQE table style.

Resources are read from the v1.44 routed reports copied into paper_tables/table3/data/
(v141_reports.py); the reference's increment from paper_tables/literature_values.json.
Latencies are HLS schedules at the routed clocks (cycle counts below, with their source).

Writes table3_implementation.tex, table3_standalone.tex, table3_values.json and table3_preview.png.

Run from the repo root:  python paper_tables/table3/make_table3_implementation.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
__import__("sys").path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import figout  # noqa: E402  (where outputs go: build/ by default, --out DIR, --in-place, --check)
OUT = figout.setup(__file__)
sys.path.insert(0, str(ROOT / "paper_tables"))
sys.path.insert(0, str(HERE))
from tablekit import LIT, latex_table, standalone, preview, write_details  # noqa: E402
import v141_reports as rep  # noqa: E402

ADC_MHZ = 552.96        # readout fabric clock (RFSoC 4x2 ADC tile / 8); routed report rounds the period to 1.809 ns
NN_LIVE_CYCLES = 9      # last sample -> logit + decision (RTL simulation: audit_fixes/RB_prep/hls/rtl_sim/xsim_v15c.txt)
NN_AXI_MHZ = 100.0
NN_AXI_CYCLES = 5       # inference after the window is loaded (Sec. 9.1); ingest 1543 cycles = 15.4 us via host DMA
NN_AXI_E2E_US = 15.5
import csv  # noqa: E402
EP = []   # v1.44: no failing endpoint (asserted below), so there is no endpoint classification to read
EP_N = {}
for _r in EP:
    EP_N[_r["block"]] = EP_N.get(_r["block"], 0) + int(_r["n"])
NN_LIVE_FAILING = EP_N.get("NN_live_0", 0)    # by endpoint block, from the v1.44 endpoint classification
CDC_FAILING = EP_N.get("live_res_cdc_1", 0) + EP_N.get("live_res_cdc_0", 0)

blk = rep.blocks(); tot = rep.totals(); tim = rep.timing()
assert tim["setup_failing"] == 0, "v1.44 has failing endpoints: restore the endpoint classification"
assert abs(1e3 / ADC_MHZ - tim["adc_x2_period_ns"]) < 0.001
LOOP = ["boxcar_tap_0", "dac_gate_0", "live_gate_0", "live_res_cdc_0", "live_res_cdc_1", "trig_sync_0"]
INSTR = ["seg_stamp_0", "axi_bram_ctrl_live_bram", "axi_bram_ctrl_seg_bram", "axi_bram_ctrl_gate_bram"]
loop = {c: sum(blk[b][c] for b in LOOP) for c in ("lut", "ff", "dsp", "ramb36", "ramb18")}
ref = LIT["reference"]
LUT_DEV, FF_DEV = tot["lut"]["avail"], tot["ff"]["avail"]


def n(v):
    return f"{int(round(v)):,}"


def bram(b):
    t = b["ramb36"] + 0.5 * b["ramb18"]
    return "0" if t == 0 else (f"{t:g}")


def pct(v, dev):
    return f"{100 * v / dev:.1f}"


live, axi = blk["NN_live_0"], blk["NN_axi_0"]
BODY = [
    ("section", r"Streaming path, this work"),
    [r"\quad \nnlive{}\textsuperscript{a}", n(live["lut"]), pct(live["lut"], LUT_DEV), n(live["ff"]),
     str(live["dsp"]), bram(live), f"{NN_LIVE_CYCLES * 1e3 / ADC_MHZ:.1f}"],
    [r"\quad Loop logic\textsuperscript{b}", n(loop["lut"]), pct(loop["lut"], LUT_DEV), n(loop["ff"]),
     str(loop["dsp"]), bram(loop), "---"],
    [r"\quad Real-time path, total", n(live["lut"] + loop["lut"]), pct(live["lut"] + loop["lut"], LUT_DEV),
     n(live["ff"] + loop["ff"]), str(live["dsp"] + loop["dsp"]), bram({c: live[c] + loop[c] for c in ("ramb36", "ramb18")}), "---"],
    ("section", r"Buffered path, this work"),
    [r"\quad \nnaxi{}\textsuperscript{c}", n(axi["lut"]), pct(axi["lut"], LUT_DEV), n(axi["ff"]),
     str(axi["dsp"]), bram(axi), f"{NN_AXI_CYCLES * 1e3 / NN_AXI_MHZ:.0f}"],
    ("section", r"For scale"),
    [r"\quad NN of \cite{" + ref["cite"] + r"}\textsuperscript{d}",
     n(ref["nn_lut"]), f"{ref['nn_lut_pct']:.1f}", n(ref["nn_ff"]), str(ref["nn_dsp"]), str(ref["nn_bram"]),
     f"{ref['latency_ns']}"],
    [r"\quad Whole design\textsuperscript{e}", n(tot["lut"]["used"]), f"{tot['lut']['pct']:.1f}",
     n(tot["ff"]["used"]), n(tot["dsp"]["used"]), f"{tot['bram']['used']:g}", "---"],
]
HEADER = [["", "", "LUT", "", "", "", "Latency"],
          ["Block", "LUT", "(\\%)", "FF", "DSP", "BRAM", "(ns)"]]
MET = tim["setup_failing"] == 0 and tim["wns"] >= 0
# v1.44 routed bus-skew report: set_bus_skew 2.00 ns on live_res_cdc_1's data against its toggle, 2.352 ns achieved
# (data/v1.44_routed_bus_skew.rpt, "Slack (VIOLATED): -0.352ns"). v141_reports.py does not parse that report, so the value is kept here.
BUS_SKEW_MISS_NS = 0.352
T_LONG = (rf"Setup and hold met: WNS ${tim['wns']:.3f}$\,ns, 0 of {tim['setup_endpoints']:,} endpoints fail. One bus-skew "
          rf"constraint on the result crossing into the DAC domain misses by {BUS_SKEW_MISS_NS:.2f}\,ns." if MET else
          rf"Setup timing is not met in the {ADC_MHZ:.2f}\,MHz domain: WNS ${tim['wns']:.3f}$\,ns, {tim['setup_failing']} of "
          rf"{tim['setup_endpoints']:,} endpoints fail: {NN_LIVE_FAILING} in \nnlive{{}}, {CDC_FAILING} in its clock crossing; hold met.")
T_SHORT = (rf"Setup and hold met at sign-off; one bus-skew constraint misses by {BUS_SKEW_MISS_NS:.2f}\,ns." if MET else
           rf"Setup timing is not met in the {ADC_MHZ:.2f}\,MHz domain (WNS ${tim['wns']:.3f}$\,ns); {NN_LIVE_FAILING} failing paths end in \nnlive{{}}.")
DETAILS = [  # long form, written to table3_details.md for the repository
    ("a", rf"{ADC_MHZ:.2f}\,MHz. Latency: last sample of the window to logit and decision, {NN_LIVE_CYCLES} cycles. "
          rf"Measured from the last sample at the readout output the same interval is 18.1\,ns (10 cycles), one "
          rf"cycle more because of the window gate's output register. Excludes the 8-RAMB36 record and capture "
          rf"buffer used only for verification."),
    ("b", r"Boxcar tap, window gate, DAC gate, trigger synchronizer and result clock-domain crossings: everything between "
          r"the readout and the conditional pulse except \nnlive{}; readout and DAC clock domains."),
    ("c", rf"{NN_AXI_MHZ:.0f}\,MHz. Latency: inference after the window is loaded, {NN_AXI_CYCLES} cycles; loading "
          rf"the window by host DMA takes the end-to-end time to about {NN_AXI_E2E_US}\,$\mu$s."),
    ("d", rf"ZCU216 (XCZU49DR), {1e3 / ref['clock_ns']:.1f}\,MHz: the NN's increment over QICK, as reported; latency "
          rf"from the end of the window to the result stored in BRAM, {ref['latency_cycles']} cycles. Different "
          rf"device and window; their increment includes their 128-kB prediction buffer, so the BRAM columns are "
          rf"not comparable."),
    ("e", rf"v1.44, {tot['device'].split('-')[0].upper()}, routed. " + T_LONG),
    ("", r"Routed utilization, Vivado 2023.1. BRAM in 36-kb tiles (an 18-kb block counts 0.5). LUT (\%) of each "
         r"block's own device; the XCZU48DR and the ZCU216's XCZU49DR have the same LUT, FF, BRAM and DSP "
         r"capacity (425,280 LUT), so the two percentages are on the same scale."),
]
NOTES = [  # printed under the table
    ("a", rf"Last window sample to decision, {NN_LIVE_CYCLES} cycles at {ADC_MHZ:.2f}\,MHz. Excludes a buffer used only for verification."),
    ("b", r"Boxcar tap, window gate, DAC gate, trigger synchronizer and clock-domain crossings."),
    ("c", rf"Inference after the window is loaded, at {NN_AXI_MHZ:.0f}\,MHz (C-synthesis estimate); about {NN_AXI_E2E_US}\,$\mu$s end to end. "
          r"BRAM: the core alone; its 16,384-entry result buffer is a separate block."),
    ("d", r"Increment over QICK on a ZCU216, as reported. BRAM includes their prediction buffer, so it is not comparable."),
    ("e", T_SHORT),
    ("", r"BRAM in 36-kb tiles. Both devices have the same capacity, so LUT percentages share a scale."),
]
GEN = "paper_tables/table3/make_table3_implementation.py"
TEX = latex_table(number=3, generator=GEN, label="tab:implementation", title="Implementation Resources and Classifier Latency (Routed)", colspec="@{}lcccccc@{}", header=HEADER,
                  body=BODY, notes=NOTES, tabcolsep=3)
OUT.path("table3_implementation.tex").write_text(TEX, encoding="utf-8")
OUT.path("table3_standalone.tex").write_text(standalone(3, "table3_implementation.tex"), encoding="utf-8")
vals = dict(nn_live=live, loop_logic=loop, loop_blocks={b: blk[b] for b in LOOP},
            instrumentation={b: blk[b] for b in INSTR}, nn_axi=axi, totals=tot, timing=tim,
            nn_live_latency_ns=NN_LIVE_CYCLES * 1e3 / ADC_MHZ, nn_axi_latency_ns=NN_AXI_CYCLES * 1e3 / NN_AXI_MHZ)
OUT.path("table3_values.json").write_text(json.dumps(vals, indent=1), encoding="utf-8")
write_details(OUT.path("table3_details.md"), 3, DETAILS)
preview(OUT.path("table3_preview.png"), number=3, header=HEADER, body=BODY, notes=NOTES, colsep_pt=3,
        aligns=["left"] + ["center"] * 6)
print(TEX)
OUT.finish()
