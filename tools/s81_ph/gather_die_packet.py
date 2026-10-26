#!/usr/bin/env python3
"""Export the real wires-only gather as explicit die children and connections.

This is an import candidate, not die adoption or physical qualification. The
original wrapper is elaborated again and compared pin-for-pin with the stored
flatten plan. No geometry-derived connections or replacement logic are emitted.
"""
import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

import gather_flatten_plan as gfp

ROOT = Path(__file__).resolve().parents[2]
PLAN = f"{gfp.CAND}/gather_flatten_plan.json"
ELAB_SOURCES = [
    "rtl/dsrom_sys/s81_ph/ot_s81ph_root_leaf.sv",
    "rtl/dsrom_sys/s81_ph/dsfd_gth_ctl.sv",
    "rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv",
    "rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gth_lane.sv",
    "rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gth_res.sv",
    "rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gth_strip.sv",
    "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv",
    "rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar(port, index, width):
    return f"{port}[{index}]" if width > 1 else port


def actual_graph(mod):
    """Graph independent of Yosys's incidental bit numbers."""
    graph = {}
    for p, v in mod["ports"].items():
        for i, b in enumerate(v["bits"]):
            graph.setdefault(b, set()).add("PORT/" + scalar(p, i, len(v["bits"])))
    for name, cell in mod["cells"].items():
        for p, bits in cell["connections"].items():
            for i, b in enumerate(bits):
                if isinstance(b, str):
                    raise ValueError(f"constant on {name}/{p}[{i}]")
                graph.setdefault(b, set()).add(name + "/" + scalar(p, i, len(bits)))
    return {frozenset(ends) for ends in graph.values()}


def planned_graph(plan):
    # Several former parent ports may alias one net. Join by actual child pin,
    # rather than accidentally creating distinct nets for each alias.
    groups = []
    for p, v in plan["die_ports"].items():
        groups.append({"PORT/" + p, *(c["pin"] for c in v["child_pins"])})
    groups.extend({n["driver"], *(s["pin"] for s in n["sinks"])} for n in plan["nets"])
    by_pin = {}
    for group in groups:
        merged = set(group)
        for pin in group:
            merged.update(by_pin.get(pin, ()))
        for pin in merged:
            by_pin[pin] = merged
    return {frozenset(g) for g in by_pin.values()}


def build(plan, mod, *, root=ROOT, prefix="sp_gather", origin=(0.0, 0.0)):
    if plan.get("verdict") != "FLATTEN_PLAN OK" or plan.get("errors"):
        raise ValueError("flatten plan is not clean")
    for key in ("rtl", "layout", "strip_plan", "slot"):
        if digest(root / plan["sources"][key]) != plan["sources"][key + "_sha256"]:
            raise ValueError(f"stale plan source: {key}")
    cells = {k.replace("\\", ""): v for k, v in mod["cells"].items()}
    if set(cells) != set(plan["children"]):
        raise ValueError("plan children differ from current elaborated RTL")
    if actual_graph(mod) != planned_graph(plan):
        raise ValueError("plan connectivity differs from current elaborated RTL")
    names = {n: prefix + "__" + n.replace(".", "__") for n in cells}
    if len(set(names.values())) != len(names):
        raise ValueError("flattened instance name collision")
    bit_names = {}
    for p, v in mod["ports"].items():
        for i, b in enumerate(v["bits"]):
            bit_names.setdefault(b, scalar(p, i, len(v["bits"])))
    for c in cells.values():
        for bits in c["connections"].values():
            for b in bits:
                bit_names.setdefault(b, f"{prefix}__n{b}")
    views, instances, geometry = {}, {}, {}
    for inst, c in sorted(plan["children"].items()):
        if c["master"] != cells[inst]["type"]:
            raise ValueError(f"master mismatch: {inst}")
        view = root / c["view"]
        lef = view / (c["master"] + ".lef")
        if digest(lef) != c["lef_sha256"]:
            raise ValueError(f"stale LEF: {inst}")
        if c["orient"] != "R0":
            raise ValueError("this packet requires measured R0 children")
        if c["master"] not in views:
            geometry[c["master"]] = gfp.lef_pins(lef)
            files = ["abstract.json", "insertion.json", c["master"] + ".lef"]
            files += [c["master"] + "_" + corner + ".lib" for corner in ("tt", "ff", "ss")]
            hashes = {f: digest(view / f) for f in files}
            ab = json.loads((view / "abstract.json").read_text())
            route = ab.get("orfs_dir", "")
            match = re.search(r"/closure-loop/([^/]+)/", route)
            if not match:
                raise ValueError(f"no closure job identity: {c['master']}")
            insertion = json.loads((view / "insertion.json").read_text())
            for corner in ("tt", "ff", "ss"):
                b = insertion[corner]["boundary"]
                if not b["n"] or b["mean"] is None:
                    raise ValueError(f"missing measured {corner} insertion: {c['master']}")
            views[c["master"]] = dict(view=c["view"], sha256=hashes, closure_job=match[1],
                                      insertion=insertion)
        size, pins = geometry[c["master"]]
        instances[names[inst]] = dict(
            original_instance=inst, master=c["master"], view=c["view"],
            at_um=[round(origin[i] + c["at_um"][i], 3) for i in range(2)], orient=c["orient"],
            outline_um=size,
            pins={p: dict(layer=v[0], local_xy_um=v[1:],
                          die_xy_um=[round(origin[i] + c["at_um"][i] + v[i+1], 3) for i in range(2)])
                  for p, v in pins.items()},
            clock_entry=c["clock_entry"], clock_pin=c["clock_pin"].split("/", 1)[1],
            connections={p: [bit_names[b] for b in bits] for p, bits in cells[inst]["connections"].items()},
            port_directions=cells[inst]["port_directions"])
    ports = {p: dict(direction=v["direction"], width=len(v["bits"]),
                     bits=[bit_names[b] for b in v["bits"]]) for p, v in mod["ports"].items()}
    return dict(schema="opentallas.s81.gather_die_packet.v1", adopted=False, physical_qualified=False,
                note="Current source connectivity and closed child views only; die homes, seam cuts, clocks and timing remain required.",
                parent_master="dsfd_sp_gather_c", parent_instance=prefix, origin_um=list(origin),
                plan_sha256=None, elaboration_sources={p: digest(root / p) for p in ELAB_SOURCES},
                counts=dict(instances=len(instances), masters=len(views), ports=len(ports),
                            external_bits=sum(p["width"] for p in ports.values())),
                ports=ports, instances=instances, views=views)


def verilog(packet):
    """Structural wrapper for exact graph comparison; parent has no logic/view."""
    ports = packet["ports"]
    lines = ["// Generated exact child connectivity; physical import remains a candidate.",
             "module dsfd_sp_gather_flatten_candidate(" + ", ".join(ports) + ");"]
    for name, p in ports.items():
        lines.append(f"  {p['direction']} wire [{p['width']-1}:0] {name};")
    internal = sorted({b for c in packet["instances"].values() for bs in c["connections"].values()
                       for b in bs if b.startswith(packet["parent_instance"] + "__n")})
    lines.extend("  wire " + n + ";" for n in internal)
    # Scalar one-bit parent ports are rendered without [0] in connection lists.
    for p, v in ports.items():
        for i, bit in enumerate(v["bits"]):
            lhs = f"{p}[{i}]"
            rhs = bit if "[" in bit or bit in internal else bit + "[0]"
            if rhs != lhs:
                lines.append(f"  assign {lhs if v['direction']=='output' else rhs} = {rhs if v['direction']=='output' else lhs};")
    for name, c in packet["instances"].items():
        conns = []
        for p, bits in c["connections"].items():
            bits = [b + "[0]" if b in ports and ports[b]["width"] == 1 else b for b in bits]
            conns.append("." + p + "({" + ", ".join(reversed(bits)) + "})")
        lines.append("  " + c["master"] + " " + name + "(" + ", ".join(conns) + ");")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default=PLAN)
    parser.add_argument("--out", required=True)
    parser.add_argument("--verilog")
    parser.add_argument("--prefix", default="sp_gather")
    parser.add_argument("--origin", default="0,0", help="actual candidate slot lower-left X,Y")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        mod = gfp.elaborate(tmp)
    plan_path = ROOT / args.plan
    packet = build(json.loads(plan_path.read_text()), mod, prefix=args.prefix,
                   origin=tuple(map(float, args.origin.split(","))))
    packet["plan_sha256"] = digest(plan_path)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2) + "\n")
    if args.verilog:
        Path(args.verilog).write_text(verilog(packet))
    print("GATHER_DIE_PACKET PASS", json.dumps(packet["counts"]), "candidate, not adopted")


if __name__ == "__main__":
    main()
