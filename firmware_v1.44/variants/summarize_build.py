import os
"""Summary of one R2 rebuild against v1.44: timing per clock (setup/hold), bus skew, utilization by block and totals,
the build's own sign-off lines, bitstream/hwh sha256 and the hwh TIMESTAMP (the banner the board scripts check).
Read-only on the build folders (v1.44's reports are read from $V144_BUILD_DIR, tag v1.43).

  python firmware_v1.44/variants/summarize_build.py <build dir> <tag> <out.json> [--md out.md]
"""
import argparse, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF_DIR, REF_TAG = Path(os.environ.get("V144_BUILD_DIR", "v144_build")), "v1.43"
COLS = ["lut", "logic_lut", "lutram", "srl", "ff", "ramb36", "ramb18", "uram", "dsp"]
T3 = json.loads((ROOT / "paper_tables/table3/table3_values.json").read_text())
LOOP = ["boxcar_tap_0", "dac_gate_0", "live_gate_0", "live_res_cdc_0", "live_res_cdc_1", "trig_sync_0"]


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def timing(rpt):
    t = Path(rpt).read_text(errors="ignore")
    i = t.index("Design Timing Summary")
    nums = re.findall(r"-?\d+\.\d+|\d+", t[i:i + 2000].split("------\n", 2)[-1])[:12]
    design = dict(wns=float(nums[0]), tns=float(nums[1]), setup_failing=int(nums[2]), setup_endpoints=int(nums[3]),
                  whs=float(nums[4]), ths=float(nums[5]), hold_failing=int(nums[6]), hold_endpoints=int(nums[7]))
    j = t.index("Intra Clock Table"); k = t.index("Inter Clock Table")
    clocks = {}
    for line in t[j:k].splitlines():
        f = line.split()
        if len(f) >= 13 and re.match(r"-?\d+\.\d+", f[1]):
            clocks[f[0]] = dict(wns=float(f[1]), tns=float(f[2]), setup_failing=int(f[3]), setup_endpoints=int(f[4]),
                                whs=float(f[5]), ths=float(f[6]), hold_failing=int(f[7]), hold_endpoints=int(f[8]))
    per = {}
    m = re.search(r"Clock Summary.*?\n-+\n\n(.*?)\n\n", t, re.S)
    if m:
        for line in m.group(1).splitlines():
            g = re.match(r"\s*(\S+)\s+\{[^}]*\}\s+([\d.]+)\s+([\d.]+)", line)
            if g:
                per[g.group(1)] = dict(period_ns=float(g.group(2)), mhz=float(g.group(3)))
    for c in clocks:
        if c in per:
            clocks[c].update(per[c])
    return design, clocks


def bus_skew(rpt):
    t = Path(rpt).read_text(errors="ignore")
    s = t.split("1. Bus Skew Report Summary\n---")[1].split("2. Bus Skew Report Per Constraint\n---")[0]
    out = []
    for m in re.finditer(r"^(\d+)\s+(\d+)\s+\[get_cells(.*?)(Slow|Fast)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)", s, re.S | re.M):
        blk = re.search(r"d_1_i/([A-Za-z0-9_]+)/", m.group(3))
        out.append(dict(id=int(m.group(1)), block=blk.group(1) if blk else None, corner=m.group(4),
                        requirement=float(m.group(5)), actual=float(m.group(6)), slack=float(m.group(7))))
    return out


def blocks(rpt):
    out = {}
    for line in Path(rpt).read_text(errors="ignore").splitlines():
        f = line.split("|")
        if len(f) < 13 or not f[1].startswith("     ") or f[1].startswith("      "):
            continue
        try:
            out[f[1].strip()] = dict(zip(COLS, (int(x) for x in f[3:12])))
        except ValueError:
            pass
    return out


def totals(rpt):
    t = Path(rpt).read_text(errors="ignore")
    def row(label):
        m = re.search(r"\|\s*" + re.escape(label) + r"\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", t)
        return dict(used=float(m.group(1)), avail=float(m.group(2)), pct=float(m.group(3)))
    return dict(lut=row("CLB LUTs"), ff=row("CLB Registers"), bram=row("Block RAM Tile"), dsp=row("DSPs"))


def loglines(log):
    keys = ("CORE_CLK_TIMING", "ADC0X2_WNS", "DAC2_CLK_TIMING", "BUSSKEW_ROUTED", "BLANK_TIMING", "TAP_TIMING", "BOXCAR_TIMING",
            "LIVE_REC_TIMING", "tProc core clock", "NN_live_0 VLNV", "BUILD_COMPLETE", "REPORTS_COMPLETE", "ADC0X2_FAIL_SPLIT")
    out = []
    p = Path(log)
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            if line.startswith(keys):
                out.append(line.strip())
    return out


def hwh_stamp(p):
    p = Path(p)
    if not p.exists():
        return None
    m = re.search(r'TIMESTAMP="([^"]+)"', p.read_text(errors="ignore")[:200000])
    return m.group(1) if m else None


def one(d, tag, log):
    d = Path(d)
    r = dict(dir=str(d), tag=tag)
    tr = d / f"{tag}_routed_timing.rpt"
    if tr.exists():
        r["design_timing"], r["clocks"] = timing(tr)
    if (d / f"{tag}_routed_bus_skew.rpt").exists():
        r["bus_skew"] = bus_skew(d / f"{tag}_routed_bus_skew.rpt")
    if (d / f"{tag}_routed_util_hier.rpt").exists():
        b = blocks(d / f"{tag}_routed_util_hier.rpt")
        r["blocks"] = {k: b[k] for k in ["NN_live_0", "NN_axi_0"] + LOOP + ["seg_stamp_0", "qick_processor_0"] if k in b}
        r["loop_logic"] = {c: sum(b[x][c] for x in LOOP) for c in ("lut", "ff", "dsp", "ramb36", "ramb18")}
    if (d / f"{tag}_routed_utilization.rpt").exists():
        r["totals"] = totals(d / f"{tag}_routed_utilization.rpt")
    bit, hwh = d / f"OG_build_{tag}.bit", d / f"OG_build_{tag}.hwh"
    r.update(bit=str(bit), bit_sha256=sha(bit), hwh=str(hwh), hwh_sha256=sha(hwh), hwh_timestamp=hwh_stamp(hwh),
             log_lines=loglines(log))
    return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("tag"); ap.add_argument("out")
    ap.add_argument("--log"); ap.add_argument("--md")
    a = ap.parse_args()
    new = one(a.dir, a.tag, a.log or Path(a.dir) / "build.log")
    ref = one(REF_DIR, REF_TAG, REF_DIR / "build_nnqick.log")
    res = dict(new=new, v144=ref, table3=dict(nn_live=T3["nn_live"], loop_logic=T3["loop_logic"], totals=T3["totals"], timing=T3["timing"]))
    Path(a.out).write_text(json.dumps(res, indent=1))
    if a.md:
        L = [f"# {a.tag} vs v1.44", "", f"bit `{new['bit']}` sha256 `{new['bit_sha256']}`", f"hwh `{new['hwh']}` sha256 `{new['hwh_sha256']}`",
             f"hwh TIMESTAMP (banner): `{new['hwh_timestamp']}` (v1.44: `{ref['hwh_timestamp']}`)", "", "## Timing (routed)", "",
             "| clock | period ns | WNS | TNS | fail | WHS | THS | v1.44 WNS | v1.44 WHS |", "|---|---|---|---|---|---|---|---|---|"]
        for c, v in new.get("clocks", {}).items():
            rv = ref.get("clocks", {}).get(c, {})
            L.append(f"| {c} | {v.get('period_ns', '')} | {v['wns']:.3f} | {v['tns']:.3f} | {v['setup_failing']} | {v['whs']:.3f} | {v['ths']:.3f} | "
                     f"{rv.get('wns', float('nan')):.3f} | {rv.get('whs', float('nan')):.3f} |")
        dt = new.get("design_timing", {})
        L += ["", f"Design: WNS {dt.get('wns')} TNS {dt.get('tns')} failing {dt.get('setup_failing')}/{dt.get('setup_endpoints')}; "
                  f"WHS {dt.get('whs')} THS {dt.get('ths')} failing {dt.get('hold_failing')}"
                  f" (v1.44: WNS {ref['design_timing']['wns']} WHS {ref['design_timing']['whs']})", "", "## Bus skew", ""]
        for b in new.get("bus_skew", []):
            L.append(f"- id {b['id']} {b['block']} {b['corner']}: requirement {b['requirement']} actual {b['actual']} slack {b['slack']}")
        L.append("- v1.44: " + "; ".join(f"{b['block']} {b['corner']} slack {b['slack']}" for b in ref.get("bus_skew", [])))
        L += ["", "## Utilization (routed)", "", "| block | LUT | FF | DSP | RAMB36 | RAMB18 | v1.44 LUT | v1.44 FF | v1.44 DSP |", "|---|---|---|---|---|---|---|---|---|"]
        for k, v in new.get("blocks", {}).items():
            rv = ref["blocks"].get(k, {})
            L.append(f"| {k} | {v['lut']} | {v['ff']} | {v['dsp']} | {v['ramb36']} | {v['ramb18']} | {rv.get('lut')} | {rv.get('ff')} | {rv.get('dsp')} |")
        ll, rl = new.get("loop_logic", {}), ref.get("loop_logic", {})
        L.append(f"| loop logic (Table III b) | {ll.get('lut')} | {ll.get('ff')} | {ll.get('dsp')} | {ll.get('ramb36')} | {ll.get('ramb18')} | {rl.get('lut')} | {rl.get('ff')} | {rl.get('dsp')} |")
        t, rt = new.get("totals", {}), T3["totals"]
        if t:
            L += ["", f"Whole design: LUT {t['lut']['used']:.0f} ({t['lut']['pct']}%), FF {t['ff']['used']:.0f}, BRAM {t['bram']['used']:g}, "
                      f"DSP {t['dsp']['used']:.0f}; Table III (v1.44): LUT {rt['lut']['used']:.0f}, FF {rt['ff']['used']:.0f}, "
                      f"BRAM {rt['bram']['used']:g}, DSP {rt['dsp']['used']:.0f}"]
        L += ["", "## Build sign-off lines", ""] + [f"    {x}" for x in new["log_lines"]]
        Path(a.md).write_text("\n".join(L) + "\n")
    print(json.dumps({k: new.get(k) for k in ("bit_sha256", "hwh_timestamp", "design_timing")}, indent=1))


if __name__ == "__main__":
    main()
