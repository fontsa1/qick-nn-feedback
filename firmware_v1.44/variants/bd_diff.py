"""Block-design diff of a rebuilt d_1.bd against firmware_v1.44/d_1.bd (cells, VLNVs, every CONFIG
parameter, interface/port connectivity, address map). Read-only on both files.

"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "to_publish/firmware_v1.44/d_1.bd"

def flat_components(comps, prefix=""):
    out = {}
    for name, c in (comps or {}).items():
        path = f"{prefix}/{name}"
        out[path] = dict(vlnv=c.get("vlnv", c.get("reference_info", {}).get("ref_name", "")),
                         params={k: (v.get("value") if isinstance(v, dict) else v) for k, v in (c.get("parameters") or {}).items()})
        if "components" in c:
            out.update(flat_components(c["components"], path))
    return out

def nets(design, key, prefix=""):
    out = {}
    for name, n in (design.get(key) or {}).items():
        out[f"{prefix}/{name}"] = tuple(sorted(n.get("ports") if key == "nets" else n.get("interface_ports", [])))
    for cname, c in (design.get("components") or {}).items():
        if "components" in c:
            out.update(nets(c, key, f"{prefix}/{cname}"))
    return out

def by_endpoints(d):
    return {v: k for k, v in d.items()}

def addr(design):
    out = {}
    def walk(o, path):
        if isinstance(o, dict):
            if "address_block" in o or ("offset" in o and "range" in o):
                out[path] = (o.get("offset"), o.get("range"))
            for k, v in o.items():
                walk(v, f"{path}/{k}")
    walk(design.get("components", {}), "")
    walk(design.get("addressing", {}), "addressing")
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("new"); ap.add_argument("--out")
    a = ap.parse_args()
    R = json.loads(REF.read_text())["design"]; N = json.loads(Path(a.new).read_text())["design"]
    lines = [f"# BD diff: {a.new} vs {REF.relative_to(ROOT)}", ""]
    rc, nc = flat_components(R["components"]), flat_components(N["components"])
    only_r, only_n = sorted(set(rc) - set(nc)), sorted(set(nc) - set(rc))
    lines += [f"cells: {len(rc)} (v1.44) vs {len(nc)} (new); only in v1.44: {only_r or 'none'}; only in new: {only_n or 'none'}", ""]
    lines.append("## Cell VLNV / parameter differences")
    nd = 0
    for c in sorted(set(rc) & set(nc)):
        if rc[c]["vlnv"] != nc[c]["vlnv"]:
            lines.append(f"- {c}: VLNV {rc[c]['vlnv']} -> {nc[c]['vlnv']}"); nd += 1
        pr, pn = rc[c]["params"], nc[c]["params"]
        for k in sorted(set(pr) | set(pn)):
            if pr.get(k) != pn.get(k):
                lines.append(f"- {c}: {k}: {pr.get(k)!r} -> {pn.get(k)!r}"); nd += 1
    if nd == 0:
        lines.append("- none")
    for key, title in (("nets", "Port nets"), ("interface_nets", "Interface nets")):
        r, n = by_endpoints(nets(R, key)), by_endpoints(nets(N, key))
        miss, extra = sorted(set(r) - set(n)), sorted(set(n) - set(r))
        lines += ["", f"## {title} (compared by their endpoint sets; net names ignored)",
                  f"{len(r)} vs {len(n)}; endpoint sets only in v1.44: {len(miss)}; only in new: {len(extra)}"]
        for e in miss:
            lines.append(f"- only v1.44: {r[e]}: {', '.join(e)}")
        for e in extra:
            lines.append(f"- only new: {n[e]}: {', '.join(e)}")
    ra, na = addr(R), addr(N)
    diffs = [k for k in sorted(set(ra) | set(na)) if ra.get(k) != na.get(k)]
    lines += ["", "## Address map entries", f"{len(ra)} vs {len(na)}; differing: {len(diffs)}"]
    for k in diffs[:200]:
        lines.append(f"- {k}: {ra.get(k)} -> {na.get(k)}")
    txt = "\n".join(lines) + "\n"
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)

if __name__ == "__main__":
    main()
