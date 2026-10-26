"""Shared slice-to-core implementation (METHODOLOGY 12.2a1/12.7/12.8).

No per-die recipes: compile the slice's pushdown cells/ports, optional structured
core tree, and named bay cells into one OpenROAD hook. Coordinates and sink sets
come from the plan; the hook never selects a measured delay or a nearest leaf.
The result is CORE-owned ODB logic, exported in its final netlist/LEF. The ft
ports are exclusively buffer feedthroughs; core clk/rst remain separate ports.
"""
import argparse
import json
import math
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUFFER = re.compile(r"BUFx(?:2|3|4|5|6|8|10|12|16|20|24)(?:f)?_ASAP7_75t_R\Z")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


class InfraError(ValueError):
    pass


def word(value):
    value = str(value)
    if any(c in value for c in "{}\\\n\r"):
        raise InfraError(f"unsupported Tcl name {value!r}")
    return "{" + value + "}"


def xy(value, where, outline=None):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(
            not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in value):
        raise InfraError(f"{where}: finite [x, y] required")
    if outline and any(v < 0 or v > hi for v, hi in zip(value, outline)):
        raise InfraError(f"{where}: point outside core outline")
    return list(value)


def buffer(cell, where):
    if not BUFFER.fullmatch(str(cell)):
        raise InfraError(f"{where}: only a polarity-preserving ASAP7 RVT BUF is allowed, got {cell!r}")
    return cell


def compile_slice(sl):
    """Compile physical identities before a build; returns cells, FT ports/arcs, tree and bay assignments."""
    outline = sl["outline_um"]
    cells, ports, arcs, bays = [], [], [], []
    seen_cells, seen_ports = set(), set()

    def add_cell(c, rect=None):
        c = dict(c)
        n = c.get("name")
        if not isinstance(n, str) or not IDENT.fullmatch(n) or n in seen_cells:
            raise InfraError(f"duplicate/invalid planned cell {n!r}")
        seen_cells.add(n)
        buffer(c.get("master", c.get("cell")), n)
        c["master"] = c.get("master", c.get("cell"))
        c["xy_um"] = xy(c.get("xy_um"), n, outline)
        if rect:
            x, y = c["xy_um"]
            if not (rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]):
                raise InfraError(f"{n}: planned cell is outside its island")
        c["rect_um"] = rect or [0, 0, *outline]
        cells.append(c)
        return n

    for island in sl.get("pushdown", {}).get("islands", []):
        name = island["name"]
        rect = island["rect_um"]
        plist = island.get("ft_ports", island.get("ports", []))
        pmap = {}
        for p in plist:
            p = dict(p)
            n = p["name"]
            if not IDENT.fullmatch(n) or n in seen_ports:
                raise InfraError(f"duplicate/invalid feedthrough port {n!r}")
            seen_ports.add(n)
            direction = p.get("dir", p.get("direction"))
            direction = {"in": "INPUT", "out": "OUTPUT", "input": "INPUT", "output": "OUTPUT"}.get(direction, direction)
            if direction not in ("INPUT", "OUTPUT"):
                raise InfraError(f"{n}: input or output required")
            p.update(direction=direction, xy_um=xy(p.get("xy_um"), n, outline))
            if p.get("layer", "M5") != "M5":
                raise InfraError(f"{n}: clock/reset feedthrough stack must terminate on M5")
            ports.append(p)
            pmap[n] = p
        explicit = island.get("cells")
        if explicit:
            for c in explicit:
                n = add_cell(c, rect)
                pins = c.get("pins", {})
                if set(pins) != {"A", "Y"}:
                    raise InfraError(f"{n}: pins must declare A and Y feedthrough ports")
                arcs.append(dict(cell=n, source=pins["A"], sink=pins["Y"]))
        else:
            driver = island["driver"]
            count = driver.get("parallel", 1)
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise InfraError(f"{name}: parallel must be a positive integer")
            cx, cy = xy(island["centre_um"], name, outline)
            for kind, master, yy, nbuf in (("ck", driver["cell"], cy + .54, count),
                                           ("rst", "BUFx4_ASAP7_75t_R", cy - .54, 1)):
                ip = [p for p in plist if p["name"].endswith(f"_{kind}_i")]
                op = [p for p in plist if p["name"].endswith(f"_{kind}_o")]
                if len(ip) != 1 or len(op) != 1:
                    raise InfraError(f"{name}: exactly one {kind} input/output feedthrough pair required")
                for k in range(nbuf):
                    n = add_cell(dict(name=f"mp_{name}_{kind}{k}", master=master,
                                      xy_um=[cx + (k - (nbuf - 1) / 2) * 1.08, yy]), rect)
                    arcs.append(dict(cell=n, source=ip[0]["name"], sink=op[0]["name"]))
    for a in arcs:
        if a["source"] not in seen_ports or a["sink"] not in seen_ports:
            raise InfraError(f"{a['cell']}: feedthrough arc references an undeclared port")
        pin = next(p for p in ports if p["name"] == a["source"])
        pout = next(p for p in ports if p["name"] == a["sink"])
        if pin["direction"] != "INPUT" or pout["direction"] != "OUTPUT":
            raise InfraError(f"{a['cell']}: feedthrough directions reversed")
    if seen_ports != {a[k] for a in arcs for k in ("source", "sink")}:
        raise InfraError("every feedthrough port must have a declared buffer arc")

    tree = sl.get("core_tree")
    if tree:
        tree = dict(tree)
        cp = tree.get("clock_port")
        if not isinstance(cp, str) or cp in seen_ports:
            raise InfraError("core_tree.clock_port must be a separate core clock input")
        depth, nn = {"port:" + cp: 0}, set()
        for c in tree.get("nodes", []):
            c = dict(c)
            par = c.get("parent")
            if par not in depth:
                raise InfraError(f"{c.get('name')}: parent must precede child; missing parent/cycle")
            n = add_cell(c, c.get("island_rect_um"))
            nn.add(n)
            depth[n] = depth[par] + 1
        leaves = tree.get("leaves", [])
        used, counts, levels = set(), [], set()
        if not leaves:
            raise InfraError("core_tree requires explicitly assigned sink leaves")
        for leaf in leaves:
            n = leaf["node"]
            if n not in nn:
                raise InfraError(f"unknown leaf driver {n}")
            levels.add(depth[n])
            sinks = leaf.get("sinks", [])
            if not sinks:
                raise InfraError(f"{n}: empty leaf")
            for s in sinks:
                word(s)
                if s in used:
                    raise InfraError(f"clock sink assigned twice: {s}")
                used.add(s)
            counts.append(len(sinks))
        if len(levels) != 1:
            raise InfraError(f"core tree leaves have unequal stage counts: {sorted(levels)}")
        if tree.get("equal_load", True) and max(counts) - min(counts) > 1:
            raise InfraError(f"core tree leaf sink counts are unequal: {min(counts)}..{max(counts)}")
        tree["depth"] = next(iter(levels))
    for b in sl.get("bays", []):
        assignments = b.get("cells", [])
        if b.get("bits", 0) and not assignments:
            raise InfraError(f"bay {b['name']}: bits require explicit cell assignments; metadata alone is not a built bay")
        for c in assignments:
            xy(c.get("xy_um"), f"bay {b['name']}/{c.get('name')}", outline)
            bays.append(dict(c, bay=b["name"], rect_um=b["rect_um"]))
    entry = next((i["clock_pin"] for i in sl.get("islands", []) if i.get("clock_pin")), None)
    clock_port = sl.get("core_clock_port") or ((tree or {}).get("clock_port"))
    if entry and not clock_port:
        raise InfraError("clock entry requires explicit core_clock_port (or core_tree.clock_port); port names are never guessed")
    if entry and entry.get("layer") != "M5":
        raise InfraError("core clock entry must terminate on M5")
    if entry:
        xy(entry.get("xy_um"), "clock entry", outline)
    pin_shapes = [(p["name"], p["xy_um"]) for p in ports]
    if entry:
        pin_shapes.append((clock_port, entry["xy_um"]))
    for k, (name, loc) in enumerate(pin_shapes):
        for other, q in pin_shapes[:k]:
            if abs(loc[0] - q[0]) < .032 - 1e-9 and abs(loc[1] - q[1]) < .192 - 1e-9:
                raise InfraError(f"M5 planned pin shapes overlap: {name}, {other}; revise the slice")
    return dict(module=sl["module"], outline_um=outline, cells=cells, ports=ports, arcs=arcs,
                core_tree=tree, core_clock_port=clock_port, clock_entry=entry,
                bays=bays, entry_pins=sl.get("entry_pins", []))


def emit_tcl(sl):
    plan = compile_slice(sl)
    lines = ["# Shared core infrastructure: plan-defined identities only; no measured adjustments.",
             "source /work/native_pg_binding.tcl", "source /work/core_infra_impl.tcl", "ot_ci_begin"]
    if plan["clock_entry"]:
        x, y = plan["clock_entry"]["xy_um"]
        lines.append(f"ot_ci_clock_entry {word(plan['core_clock_port'])} {x:g} {y:g}")
    for p in plan["ports"]:
        x, y = p["xy_um"]
        lines.append(f"ot_ci_port {word(p['name'])} {p['direction']} {x:g} {y:g}")
    for c in plan["cells"]:
        x, y = c["xy_um"]
        r = " ".join(f"{v:g}" for v in c["rect_um"])
        lines.append(f"ot_ci_cell {word(c['name'])} {c['master']} {x:g} {y:g} {{{r}}}")
    for a in plan["arcs"]:
        lines.append(f"ot_ci_arc {word(a['cell'])} {word(a['source'])} {word(a['sink'])}")
    if plan["core_tree"]:
        t = plan["core_tree"]
        lines.append(f"ot_ci_tree_begin {word(t['clock_port'])}")
        for c in t["nodes"]:
            lines.append(f"ot_ci_tree_node {word(c['name'])} {word(c['parent'])}")
        for leaf in t["leaves"]:
            for s in leaf["sinks"]:
                lines.append(f"ot_ci_tree_sink {word(leaf['node'])} {word(s)}")
        lines.append("ot_ci_tree_finish")
    for b in plan["bays"]:
        x, y = b["xy_um"]
        r = " ".join(f"{v:g}" for v in b["rect_um"])
        lines.append(f"ot_ci_bay_cell {word(b['name'])} {x:g} {y:g} {{{r}}}")
    for p in plan["entry_pins"]:
        if not p.get("pin"):
            raise InfraError(f"entry {p.get('name')}: an actual core pin binding is required")
        if p.get("layer") != "M7":
            raise InfraError(f"entry {p['name']}: die signal on-ramp must be M7")
        x, y = p["xy_um"]
        lines.append(f"ot_ci_entry {word(p['pin'])} {x:g} {y:g}")
    lines += ["ot_ci_finish", ""]
    return "\n".join(lines)



def verilog_name(name):
    return name if IDENT.fullmatch(name) else "\\" + name + " "


def emit_wrapper(sl, logic_module, interface):
    """Synthesis/LEC source wrapper. The caller names its existing logic master
    separately; interface is the original {port: {direction, width}} manifest.
    Core data ports and cycle behavior pass unchanged. Every FT pin is isolated.
    This is deliberately an API, not a Verilog regex rewriter.
    """
    p = compile_slice(sl)
    if not IDENT.fullmatch(sl["module"]) or not IDENT.fullmatch(logic_module) or logic_module == sl["module"]:
        raise InfraError("wrapper and original logic master must be distinct Verilog identifiers")
    allports = []
    for name, port in interface.items():
        if name in {x["name"] for x in p["ports"]}:
            raise InfraError(f"core logic already uses dedicated feedthrough port {name}")
        direction, width = port["direction"], port.get("width", 1)
        if direction not in ("input", "output", "inout") or not isinstance(width, int) or width < 1:
            raise InfraError(f"invalid original interface {name}")
        word(name)
        sign = " signed" if port.get("signed", False) else ""
        offset = port.get("offset", 0)
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise InfraError(f"invalid packed range offset for {name}")
        left, right = ((offset, offset + width - 1) if port.get("upto", False) else (offset + width - 1, offset))
        packed = f" [{left}:{right}]" if width > 1 or offset else ""
        allports.append(f"{direction} wire{sign}{packed} {verilog_name(name)}")
    for port in p["ports"]:
        allports.append(f"{port['direction'].lower()} wire {port['name']}")
    lines = [f"module {sl['module']}(" + ",\n  ".join(allports) + ");"]
    links = ", ".join(f".{verilog_name(n)}({verilog_name(n)})" for n in interface)
    lines.append(f"  {logic_module} u_logic ({links});")
    cells = {c["name"]: c for c in p["cells"]}
    for a in p["arcs"]:
        c = cells[a["cell"]]
        lines.append(f"  (* keep = 1, dont_touch = 1 *) {c['master']} {c['name']} "
                     f"(.A({a['source']}), .Y({a['sink']}));")
    lines.append("endmodule\n")
    return "\n".join(lines)


def install(kd, sl):
    """Called by every kit's master_slice hook. No slice/pushdown means no change."""
    if sl.get("kind") != "core" or not sl.get("pushdown"):
        return False
    kd = Path(kd)
    script = emit_tcl(sl)  # refuse incomplete plan BEFORE writing kit files
    wrapper = None
    if sl.get("logic_module") is not None or sl.get("logic_ports") is not None:
        if not sl.get("logic_module") or not sl.get("logic_ports"):
            raise InfraError("logic_module and logic_ports must be supplied together")
        wrapper = emit_wrapper(sl, sl["logic_module"], sl["logic_ports"])
    (kd / "master_core_infra.tcl").write_text(script)
    if wrapper is not None:
        (kd / "master_core_wrapper.v").write_text(wrapper)
    (kd / "core_infra_plan.json").write_text(json.dumps(compile_slice(sl), indent=2) + "\n")
    shutil.copyfile(HERE / "core_infra.tcl", kd / "core_infra_impl.tcl")
    root = HERE.parents[1]
    shutil.copyfile(root / "physical/common_flow/native_pg_binding.tcl", kd / "native_pg_binding.tcl")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slice")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import master_slice as MS
    sl = MS.load(a.slice)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    if not install(a.out, sl):
        raise SystemExit("core_infra: core slice with pushdown islands required")


if __name__ == "__main__":
    main()
