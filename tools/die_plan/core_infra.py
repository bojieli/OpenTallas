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
    # OpenDB/Yosys instance identities commonly contain literal \[ and \].
    # Braced Tcl words preserve these; only a trailing odd backslash run can
    # escape our closing brace. Never strip or canonicalize the instance name.
    if any(c in value for c in "{}\n\r") or (len(value) - len(value.rstrip("\\"))) % 2:
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
        used, counts, levels = set(), {}, set()
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
            group = leaf.get("load_class", "register")
            if group not in ("register", "macro"):
                raise InfraError(f"{n}: unknown load_class {group!r}")
            counts.setdefault(group, []).append(len(sinks))
        if len(levels) != 1:
            raise InfraError(f"core tree leaves have unequal stage counts: {sorted(levels)}")
        if tree.get("equal_load", True):
            for group, cc in counts.items():
                if max(cc) - min(cc) > 1:
                    raise InfraError(f"core tree {group} leaf sink counts are unequal: {min(cc)}..{max(cc)}")
        elif tree.get("load_balance") != "joint_nldm_plan":
            raise InfraError("unequal-count leaves require explicit joint_nldm_plan electrical balancing")
        owner = {sink: leaf["node"] for leaf in leaves for sink in leaf["sinks"]}
        for pair in tree.get("same_leaf_pairs", []):
            if len(pair) != 2 or any(s not in owner for s in pair) or owner[pair[0]] != owner[pair[1]]:
                raise InfraError(f"zero-logic related pair does not share its planned leaf: {pair}")
        tree["depth"] = next(iter(levels))
    for b in sl.get("bays", []):
        assignments = b.get("cells", [])
        if b.get("bits", 0) and not assignments:
            raise InfraError(f"bay {b['name']}: bits require explicit cell assignments; metadata alone is not a built bay")
        for c in assignments:
            xy(c.get("xy_um"), f"bay {b['name']}/{c.get('name')}", outline)
            bays.append(dict(c, bay=b["name"], rect_um=b["rect_um"], regions_um=b.get("regions_um", [])))
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
    placements = sl.get("cell_placements", {})
    if placements:
        if set(placements) != {c["name"] for c in cells}:
            raise InfraError("frozen cell_placements must cover exactly the planned infrastructure cells")
        for c in cells:
            p = placements[c["name"]]
            if p.get("master") != c["master"]:
                raise InfraError(f"frozen placement master differs for {c['name']}")
            c["xy_um"] = xy(p.get("centre_um"), c["name"], outline)
            c["origin_um"] = xy(p.get("origin_um"), c["name"], outline)
            c["orient"] = p["orient"]
    return dict(module=sl["module"], outline_um=outline, cells=cells, ports=ports, arcs=arcs,
                core_tree=tree, core_clock_port=clock_port, clock_entry=entry,
                bays=bays, entry_pins=sl.get("entry_pins", []), clock_ndr=sl.get("clock_ndr"))


def named_tree_report(report, clock_port, macro_pins=None, load_balance="equal_counts"):
    """Normalize a pre-build named-sink H-tree report, including same-stage macro
    branches. Used by the shared core helper, not a per-die physical recipe.
    Sink identities must come from the actual placement after mandatory data
    placement hooks. No nearest-sink assignment or clock measurement is read.
    """
    if report.get("entry_chain", 0):
        raise InfraError("named tree report entry chain needs explicit planned nodes")
    if not report.get("leaf_assignments"):
        raise InfraError("named tree report lacks explicit leaf_assignments")
    root = "mp_core_root"
    names = {"root": root}
    names.update({row[0]: "mp_core_" + row[0] for row in report["nodes"]})
    nodes = [dict(name=root, master="BUFx24_ASAP7_75t_R", xy_um=report["entry"], parent="port:" + clock_port)]
    for name, parent, point, cell in report["nodes"]:
        nodes.append(dict(name=names[name], master=cell, xy_um=point, parent=names[parent]))
    leaves = []
    by_leaf = {}
    for leaf in report["leaf_assignments"]:
        name = "mp_core_" + leaf["name"]
        nodes.append(dict(name=name, master=leaf["cell"], xy_um=leaf["xy_um"], parent=names[leaf["parent"]]))
        leaves.append(dict(node=name, sinks=list(leaf["sinks"]), load_class="register"))
        by_leaf[leaf["name"]] = leaf
    for k, (inst, matched_leaf, point) in enumerate(report.get("macros", [])):
        if not macro_pins or inst not in macro_pins:
            raise InfraError(f"named tree report requires explicit clock pin for macro {inst}")
        leaf = by_leaf[matched_leaf]
        name = f"mp_core_macro{k}"
        nodes.append(dict(name=name, master=leaf["cell"], xy_um=point, parent=names[leaf["parent"]]))
        leaves.append(dict(node=name, sinks=[inst + "/" + macro_pins[inst]], load_class="macro"))
    if load_balance not in ("equal_counts", "joint_nldm_plan"):
        raise InfraError("unsupported named-tree load balance model")
    return dict(clock_port=clock_port, nodes=nodes, leaves=leaves, equal_load=load_balance == "equal_counts",
                load_balance=load_balance,
                source_geometry=report.get("source_geometry"),
                load_basis="equal register counts per leaf; macro leaves separately classified and timed")


def emit_tcl(sl):
    plan = compile_slice(sl)
    tree = plan.get("core_tree")
    if tree and not tree.get("equal_load", True):
        q = tree.get("model_qualification", {})
        if q.get("measured_timing_used") is not False:
            raise InfraError("unequal-count tree refuses build until joint NLDM plan model qualifies both corners")
        for corner, low, high in (("TT", 230., 270.), ("FF", 182.5, 222.5)):
            result = q.get("corners", {}).get(corner, {})
            if not result or result["leaf_window"] > 20 or result["leaf_min"] < low or result["leaf_max"] > high or result["slew_max"] > 80:
                raise InfraError(f"unequal-count tree model target FAIL/NOT RUN at {corner}; no physical build")
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
        if c.get("origin_um") is not None:
            ox, oy = c["origin_um"]
            lines.append(f"ot_ci_origin_assert {word(c['name'])} {ox:g} {oy:g} {word(c['orient'])}")
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
        regions = " ".join("{" + " ".join(f"{v:g}" for v in q) + "}" for q in b.get("regions_um", []))
        lines.append(f"ot_ci_bay_cell {word(b['name'])} {x:g} {y:g} {{{r}}} {{{regions}}}")
    for p in plan["entry_pins"]:
        if not p.get("pin"):
            raise InfraError(f"entry {p.get('name')}: an actual core pin binding is required")
        if p.get("layer") != "M7":
            raise InfraError(f"entry {p['name']}: die signal on-ramp must be M7")
        x, y = p["xy_um"]
        lines.append(f"ot_ci_entry {word(p['pin'])} {x:g} {y:g}")
    if plan.get("clock_ndr"):
        ndr = plan["clock_ndr"]
        if not plan["core_tree"] or ndr.get("layers") != ["M4", "M5"]:
            raise InfraError("core clock NDR requires a planned tree on M4/M5")
        wm, sm = ndr["width_multiplier"], ndr["spacing_multiplier"]
        if not all(isinstance(v, (int, float)) and 1 <= v <= 8 for v in (wm, sm)):
            raise InfraError("core clock width/spacing multiplier must lie in [1, 8]")
        lines.append(f"ot_ci_clock_ndr {word(ndr['name'])} {wm:g} {sm:g}")
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
