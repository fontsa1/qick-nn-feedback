"""Readers for the v1.44 routed Vivado reports copied into paper_tables/table3/data/ (2026-11-06, from
the build's report folder; build of 2026-11-04, Vivado 2023.1, xczu48dr-ffvg1517-2-e)."""
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
HIER = DATA / "v1.44_routed_util_hier.rpt"
FLAT = DATA / "v1.44_routed_utilization.rpt"
TIMING = DATA / "v1.44_routed_timing.rpt"
COLS = ["lut", "logic_lut", "lutram", "srl", "ff", "ramb36", "ramb18", "uram", "dsp"]


def blocks():
    """Top-level block-design instances (children of OG_build_i) -> resource dict."""
    out = {}
    for line in HIER.read_text(encoding="utf-8", errors="ignore").splitlines():
        f = line.split("|")
        if len(f) < 13 or not f[1].startswith("     ") or f[1].startswith("      "):
            continue  # depth 5 = direct children of OG_build_i
        name = f[1].strip()
        try:
            out[name] = dict(zip(COLS, (int(x) for x in f[3:12])))
        except ValueError:
            continue
    return out


def totals():
    """Whole-design totals and device capacities from the flat report."""
    t = FLAT.read_text(encoding="utf-8", errors="ignore")
    head = re.search(r"\| Device\s*:\s*(\S+)", t).group(1)

    def row(label):
        m = re.search(r"\|\s*" + re.escape(label) + r"\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", t)
        return dict(used=float(m.group(1)), avail=float(m.group(2)), pct=float(m.group(3)))

    return dict(device=head, lut=row("CLB LUTs"), ff=row("CLB Registers"), bram=row("Block RAM Tile"), dsp=row("DSPs"))


def timing():
    """Design-wide WNS/TNS/failing endpoints, worst hold, and the ADC fabric clock row."""
    t = TIMING.read_text(encoding="utf-8", errors="ignore")
    i = t.index("Design Timing Summary")
    nums = re.findall(r"-?\d+\.\d+|\d+", t[i:i + 2000].split("------\n", 2)[-1])[:12]
    wns, tns, nfail, ntot, whs, ths, nhold = (float(nums[0]), float(nums[1]), int(nums[2]), int(nums[3]),
                                              float(nums[4]), float(nums[5]), int(nums[6]))
    m = re.search(r"clk_out1_\w*?clk_adc0_x2_0\s+\{[^}]*\}\s+([\d.]+)\s+([\d.]+)", t)
    return dict(wns=wns, tns=tns, setup_failing=nfail, setup_endpoints=ntot, whs=whs, hold_failing=nhold,
                adc_x2_period_ns=float(m.group(1)), adc_x2_mhz=float(m.group(2)))


if __name__ == "__main__":
    b = blocks()
    for k in ("NN_live_0", "NN_axi_0", "boxcar_tap_0", "dac_gate_0", "live_gate_0", "live_res_cdc_0", "trig_sync_0"):
        print(k, b[k])
    print(totals())
    print(timing())
