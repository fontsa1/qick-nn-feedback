"""Table III recheck: recompute every Table III resource number from the utilization
reports regenerated here from the v1.44 routed checkpoint (reports/v144_utilization.rpt, reports/v144_util_hier_d3.rpt)
and compare with the paper's numbers, computed from the routed reports (vivado_reports.table3_reference()).
Read-only on the repo; writes only next to this script.

"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REP = ROOT / "firmware_v1.44" / "reports"
sys.path.insert(0, str(ROOT / "firmware_v1.44" / "reports"))
import vivado_reports as R  # noqa: E402
ref = R.table3_reference()

R.FLAT = REP / "v144_utilization.rpt"
R.HIER = REP / "v144_util_hier_d3.rpt"
blk, tot = R.blocks(), R.totals()

LOOP = ["boxcar_tap_0", "dac_gate_0", "live_gate_0", "live_res_cdc_0", "live_res_cdc_1", "trig_sync_0"]
rows, bad = [], 0

def cmp(name, new, old):
    global bad
    ok = (new == old) if not isinstance(new, float) else abs(new - old) < 1e-6
    bad += 0 if ok else 1
    rows.append((name, new, old, "ok" if ok else "DIFFERENT"))

for k in ("lut", "ff", "dsp", "ramb36", "ramb18"):
    cmp(f"NN_live.{k}", blk["NN_live_0"][k], ref["nn_live"][k])
    cmp(f"NN_axi.{k}", blk["NN_axi_0"][k], ref["nn_axi"][k])
    cmp(f"loop_logic.{k}", sum(blk[b][k] for b in LOOP), ref["loop_logic"][k])
    for b in LOOP:
        cmp(f"{b}.{k}", blk[b][k], ref["loop_blocks"][b][k])
for k in ("lut", "ff", "bram", "dsp"):
    for f in ("used", "avail", "pct"):
        cmp(f"total.{k}.{f}", tot[k][f], ref["totals"][k][f])
cmp("device", tot["device"], ref["totals"]["device"])

# printed Table III cells
L = ref["totals"]["lut"]["avail"]
printed = {
    "NN_live LUT 1,343 / 0.3% / FF 1,221 / DSP 4 / BRAM 0.5": (blk["NN_live_0"]["lut"], round(100 * blk["NN_live_0"]["lut"] / L, 1),
                                                               blk["NN_live_0"]["ff"], blk["NN_live_0"]["dsp"],
                                                               blk["NN_live_0"]["ramb36"] + 0.5 * blk["NN_live_0"]["ramb18"]),
    "Loop logic LUT 1,960 / 0.5% / FF 4,347": (sum(blk[b]["lut"] for b in LOOP), round(100 * sum(blk[b]["lut"] for b in LOOP) / L, 1),
                                               sum(blk[b]["ff"] for b in LOOP)),
    "NN_axi LUT 160,861 / 37.8% / FF 148,120 / DSP 14 / BRAM 0.5": (blk["NN_axi_0"]["lut"], round(100 * blk["NN_axi_0"]["lut"] / L, 1),
                                                                    blk["NN_axi_0"]["ff"], blk["NN_axi_0"]["dsp"],
                                                                    blk["NN_axi_0"]["ramb36"] + 0.5 * blk["NN_axi_0"]["ramb18"]),
    "Whole design LUT 252,806 / 59.4% / FF 285,071 / DSP 542 / BRAM 500": (tot["lut"]["used"], tot["lut"]["pct"], tot["ff"]["used"],
                                                                           tot["dsp"]["used"], tot["bram"]["used"]),
}
out = HERE / "table3_recheck.txt"
with out.open("w", encoding="utf-8") as f:
    f.write(f"sources: {R.FLAT.relative_to(ROOT)}, {R.HIER.relative_to(ROOT)}\n")
    f.write("reference: firmware_v1.44/reports/v1.44_routed_*.rpt (vivado_reports.table3_reference)\n\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")
    f.write(f"\n{len(rows)} values compared, {bad} different\n\nprinted cells recomputed:\n")
    for k, v in printed.items():
        f.write(f"  {k}: {v}\n")
print(out.read_text())
