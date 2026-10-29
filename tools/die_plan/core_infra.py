"""Shared slice-to-core implementation (METHODOLOGY 12.2a1/12.7/12.8).

No per-die recipes: compile the slice's pushdown cells/ports, optional structured
core tree, and named bay cells into one OpenROAD hook. Coordinates and sink sets
come from the plan; the hook never selects a measured delay or a nearest leaf (the opt-in post-placement
exact-count rebind, core_tree.post_place_rebind, runs at the CTS hook from placed geometry only).
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
ICG = re.compile(r"ICGx(?:1|2|3|4|5|6|8|10|12|16)(?:p\d+)?(?:DC)?_ASAP7_75t_[RLS]\Z")
# ASAP7 7.5T RVT BUF footprint widths (um, asap7sc7p5t_28_R_1x_220121a.lef) and the placement site width.  Parallel
# island drivers sit side by side in one row; their pitch must clear the master width (HBM-CORES-REBAL-1 10-28: the
# fixed 1.08 um pitch overlapped BUFx16f/BUFx24 groups -> OT_CORE_INFRA_PLANNED_OVERLAP mp_isl0_ck1 mp_isl0_ck0).
BUF_WIDTH_UM = {"BUFx2": 0.27, "BUFx3": 0.324, "BUFx4": 0.378, "BUFx4f": 0.432, "BUFx5": 0.432, "BUFx6f": 0.54,
                "BUFx8": 0.648, "BUFx10": 0.756, "BUFx12": 0.864, "BUFx12f": 0.972, "BUFx16f": 1.188, "BUFx24": 1.62}
SITE_UM = 0.054
PARALLEL_PITCH_UM = 1.08


def parallel_pitch(master):
    """Row pitch of side-by-side parallel island drivers: the legacy 1.08 um where the master fits it (byte-identical
    plans), else the master width plus one site gap, on the site grid."""
    w = BUF_WIDTH_UM.get(master.split("_ASAP7")[0])
    if w is None:
        raise InfraError(f"{master}: no footprint width for parallel placement")
    return max(PARALLEL_PITCH_UM, round(math.ceil(round(w / SITE_UM, 6) + 1) * SITE_UM, 6))


CTS_FANOUT = 24        # legacy core-kit CTS sink-cluster size (gen_core_kit_legacy defaults: fanout 24)


def _cts_levels(leaf, name):
    """Planned stage count of a CTS-open local tree: ceil(log_F N) for the declared domain size N (plan census of
    the gate's / leaf's sinks) and the kit's CTS cluster fanout F. Geometry/census only, never a measurement."""
    n = leaf.get("domain_sinks", len(leaf.get("sinks", [])))
    f = leaf.get("cts_fanout", CTS_FANOUT)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or not isinstance(f, int) or f < 2:
        raise InfraError(f"{name}: CTS-open leaf needs a positive integer domain_sinks census and cts_fanout >= 2")
    k = 0
    while f ** k < n:
        k += 1
    return k


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


def compile_slice(sl, kd=None):
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
            drect = island.get("driver_rect_um")
            if drect is not None:
                # HBM-CORES-REBAL-5 (master_plan.pushdown_island driver_rect): the drivers sit in the planned
                # macro-channel site; the ft pins stay at the island centre
                if len(drect) != 4 or not (drect[2] > drect[0] and drect[3] > drect[1]):
                    raise InfraError(f"{name}: driver_rect_um must be [x0, y0, x1, y1]")
                xy([drect[0], drect[1]], f"{name} driver_rect", outline)
                xy([drect[2], drect[3]], f"{name} driver_rect", outline)
                rect = [float(v) for v in drect]
                cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
            for kind, master, yy, nbuf in (("ck", driver["cell"], cy + .54, count),
                                           ("rst", "BUFx4_ASAP7_75t_R", cy - .54, 1)):
                ip = [p for p in plist if p["name"].endswith(f"_{kind}_i")]
                op = [p for p in plist if p["name"].endswith(f"_{kind}_o")]
                if len(ip) != 1 or len(op) != 1:
                    raise InfraError(f"{name}: exactly one {kind} input/output feedthrough pair required")
                pitch = parallel_pitch(master) if nbuf > 1 else PARALLEL_PITCH_UM
                for k in range(nbuf):
                    n = add_cell(dict(name=f"mp_{name}_{kind}{k}", master=master,
                                      xy_um=[cx + (k - (nbuf - 1) / 2) * pitch, yy]), rect)
                    arcs.append(dict(cell=n, source=ip[0]["name"], sink=op[0]["name"]))
    # partition H-tree leg repeaters (COORD 06:53): one fixed BUF per site between its own in/out ft ports
    for rep in sl.get("pushdown", {}).get("clock_repeaters", []):
        for p in rep.get("ft_ports", []):
            p = dict(p)
            n = p["name"]
            if not IDENT.fullmatch(n) or n in seen_ports:
                raise InfraError(f"duplicate/invalid feedthrough port {n!r}")
            seen_ports.add(n)
            direction = {"in": "INPUT", "out": "OUTPUT"}.get(p.get("dir"), p.get("dir"))
            if direction not in ("INPUT", "OUTPUT"):
                raise InfraError(f"{n}: input or output required")
            if p.get("layer", "M5") != "M5":
                raise InfraError(f"{n}: clock repeater feedthrough must terminate on M5")
            p.update(direction=direction, xy_um=xy(p.get("xy_um"), n, outline))
            ports.append(p)
        ip = [p["name"] for p in rep.get("ft_ports", []) if p.get("dir") == "in"]
        op = [p["name"] for p in rep.get("ft_ports", []) if p.get("dir") == "out"]
        if len(ip) != 1 or len(op) != 1:
            raise InfraError(f"{rep.get('name')}: exactly one in/out feedthrough pair required")
        n = add_cell(dict(name=f"mp_{rep['name']}", master=rep.get("cell"), xy_um=rep.get("xy_um")),
                     rep.get("rect_um"))
        arcs.append(dict(cell=n, source=ip[0], sink=op[0]))
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
        # ICG-aware tree (S81-CORE-LAT r4, 12.8b): an EXISTING RTL clock gate is one tree stage. The plan fixes its
        # coordinate (region root) and its parent node; its CLK pin moves from the core clock net to the parent's
        # output, its gated domain (the gate's output net, every original gated sink) stays intact and is built
        # below it as a CTS-open leaf. Gated and ungated leaves must sit at the same stage count.
        gates, copied = [], set()
        for g in tree.get("gates", []):
            g = dict(g)
            inst, par = g.get("inst"), g.get("parent")
            word(inst or "")
            if not inst or inst in nn or inst in depth or inst in seen_cells:
                raise InfraError(f"duplicate/invalid clock gate {inst!r}")
            if par not in depth:
                raise InfraError(f"gate {inst}: parent must precede child; missing parent/cycle")
            if par.startswith("port:"):
                raise InfraError(f"gate {inst}: the core clock port drives the planned root only; hang gates from a node")
            if not ICG.fullmatch(str(g.get("master", ""))):
                raise InfraError(f"gate {inst}: only an ASAP7 ICG master is a clock-gate stage, got {g.get('master')!r}")
            g["xy_um"] = xy(g.get("xy_um"), inst, outline)
            g.setdefault("clk_pin", "CLK")
            g.setdefault("out_pin", "GCLK")
            rect = g.get("island_rect_um") or [0, 0, *outline]
            x, y = g["xy_um"]
            if not (rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]):
                raise InfraError(f"gate {inst}: planned position is outside its island")
            g["rect_um"] = rect
            # CLOCK-GATE COPY (S81-CORE-LAT-R7, COORD ruling R6 (3)): a NEW ICG instance of the SAME master whose
            # enable pins (ENA/SE) connect to the SAME nets as an existing RTL gate (same registered enable), so its
            # gated sinks keep exactly the original gating function; the copy takes the NAMED members out of the
            # original's gated domain. Structural only (no timing input); kit LEC on the post-hook netlist must prove it.
            if "clone_of" in g:
                orig = next((o for o in gates if o["inst"] == g["clone_of"]), None)
                if orig is None or "clone_of" in orig:
                    raise InfraError(f"gate copy {inst}: clone_of must name an original RTL gate listed before it")
                if g["master"] != orig["master"]:
                    raise InfraError(f"gate copy {inst}: master {g['master']} differs from {orig['inst']} {orig['master']}")
                if (g["clk_pin"], g["out_pin"]) != (orig["clk_pin"], orig["out_pin"]):
                    raise InfraError(f"gate copy {inst}: clk/out pins differ from {orig['inst']}")
                g["enable_pins"] = list(g.get("enable_pins", ["ENA", "SE"]))
                if not g["enable_pins"] or len(set(g["enable_pins"])) != len(g["enable_pins"]) or \
                        set(g["enable_pins"]) & {g["clk_pin"], g["out_pin"]}:
                    raise InfraError(f"gate copy {inst}: enable_pins must be distinct non-clock pins")
                mem = g.get("members", [])
                if not mem or len(set(mem)) != len(mem):
                    raise InfraError(f"gate copy {inst}: members must be a non-empty list of distinct named gated sinks")
                for s_ in mem:
                    word(s_)
                    if s_ in copied:
                        raise InfraError(f"gated sink {s_} assigned to two gate copies")
                    copied.add(s_)
                orig.setdefault("copies", []).append(inst)
            elif "members" in g:
                raise InfraError(f"gate {inst}: only a gate copy (clone_of) lists members")
            depth[inst] = depth[par] + 1
            gates.append(g)
        gate_names = {g["inst"] for g in gates}
        tree["gates"] = gates
        leaves = tree.get("leaves", [])
        used, counts, levels = set(), {}, set()
        if not leaves:
            raise InfraError("core_tree requires explicitly assigned sink leaves")
        domains = set()
        cts_levels = {}
        # DIE-KV-14b opt-in core_tree.stage_basis = "total": a CTS-open leaf counts its planned node depth PLUS its
        # declared CTS-built stage count (leaf.cts_stages, plan-computed from the census), so a planned macro leaf
        # chain can sit at the SAME total stage count as the register leaves below a CTS-open node (12.8 d1).
        # Absent (default "node_depth"): the legacy check below, unchanged.
        basis = tree.get("stage_basis", "node_depth")
        if basis not in ("node_depth", "total"):
            raise InfraError(f"core_tree.stage_basis must be node_depth or total, got {basis!r}")

        def _open_stages(leaf, n):
            if basis != "total":
                return _cts_levels(leaf, n), 0
            k = leaf.get("cts_stages")
            if not isinstance(k, int) or isinstance(k, bool) or k < 1:
                raise InfraError(f"{n}: stage_basis total needs an integer cts_stages >= 1 on every CTS-open leaf")
            return k, k
        for leaf in leaves:
            n = leaf["node"]
            if leaf.get("load_class") == "gated_domain":
                if n not in gate_names or n in domains:
                    raise InfraError(f"gated_domain leaf {n}: must name a planned clock gate exactly once")
                if leaf.get("sinks"):
                    raise InfraError(f"gated_domain leaf {n}: gated sinks stay on the gate output; do not list them")
                gd = next(g for g in gates if g["inst"] == n)
                if "clone_of" in gd and leaf.get("domain_sinks") != len(gd["members"]):
                    raise InfraError(f"gated_domain leaf {n}: a gate copy's domain is exactly its {len(gd['members'])} members")
                domains.add(n)
                cts_levels[n], extra = _open_stages(leaf, n)
                levels.add(depth[n] + extra)
                continue
            if n not in nn:
                raise InfraError(f"unknown leaf driver {n}")
            if leaf.get("cts_open"):
                cts_levels[n], extra = _open_stages(leaf, n)
                levels.add(depth[n] + extra)
            else:
                levels.add(depth[n])
            sinks = leaf.get("sinks", [])
            if not sinks:
                raise InfraError(f"{n}: empty leaf")
            for s in sinks:
                word(s)
                if s in copied:
                    raise InfraError(f"clock sink {s} is a gate-copy member and a direct leaf sink")
                if s in used:
                    raise InfraError(f"clock sink assigned twice: {s}")
                used.add(s)
            group = leaf.get("load_class", "register")
            if group not in ("register", "macro"):
                raise InfraError(f"{n}: unknown load_class {group!r}")
            counts.setdefault(group, []).append(len(sinks))
        if gate_names - domains:
            raise InfraError(f"planned clock gates without a gated_domain leaf: {sorted(gate_names - domains)}")
        if len(levels) != 1:
            raise InfraError(f"core tree leaves have unequal stage counts: {sorted(levels)}")
        if cts_levels and len(set(cts_levels.values())) != 1:
            raise InfraError(f"CTS-open leaves have unequal planned local stage counts: "
                             f"{dict(sorted(cts_levels.items()))}")
        tree["cts_open"] = sorted(cts_levels)
        if tree.get("equal_load", True):
            for group, cc in counts.items():
                if max(cc) - min(cc) > 1:
                    raise InfraError(f"core tree {group} leaf sink counts are unequal: {min(cc)}..{max(cc)}")
        elif tree.get("load_balance") != "joint_nldm_plan":
            raise InfraError("unequal-count leaves require explicit joint_nldm_plan electrical balancing")
        owner = {sink: leaf["node"] for leaf in leaves for sink in leaf.get("sinks", [])}
        for pair in tree.get("same_leaf_pairs", []):
            if len(pair) != 2 or any(s not in owner for s in pair) or owner[pair[0]] != owner[pair[1]]:
                raise InfraError(f"zero-logic related pair does not share its planned leaf: {pair}")
        tree["depth"] = next(iter(levels))
        rb = tree.get("post_place_rebind")
        if rb is not None:
            # FLOW-GEN-2: post-placement exact-count rebind among the plan's register leaves (core_leaf_rebind.py)
            if rb != "exact_count":
                raise InfraError(f"core_tree.post_place_rebind must be 'exact_count', got {rb!r}")
            if len(rebind_leaves(tree)) < 2:
                raise InfraError("core_tree.post_place_rebind needs at least two non-open register leaves")
    reserved = []
    for b in sl.get("bays", []):
        assignments = b.get("cells", [])
        if b.get("bits", 0) and not assignments and sl.get("kind") == "partition":
            # partition station/repeater bay: a reserved site region the kit's ft-station step fills (12.2b);
            # the kit holds it as a named region, it never becomes a blockage for those cells
            reserved.append(dict(name=b["name"], rect_um=b["rect_um"], regions_um=b.get("regions_um", []),
                                 bits=b["bits"], kind=b.get("kind")))
            continue
        if b.get("bits", 0) and not assignments:
            raise InfraError(f"bay {b['name']}: bits require explicit cell assignments; metadata alone is not a built bay")
        for c in assignments:
            xy(c.get("xy_um"), f"bay {b['name']}/{c.get('name')}", outline)
            bays.append(dict(c, bay=b["name"], rect_um=b["rect_um"], regions_um=b.get("regions_um", [])))
    entry = next((i["clock_pin"] for i in sl.get("islands", []) if i.get("clock_pin")), None)
    clock_port = sl.get("core_clock_port") or ((tree or {}).get("clock_port"))
    if sl.get("kind") == "partition" and not clock_port:
        entry = None      # partition PHY-strip clock entry: placed by the partition io step, checked by kit_check
    if entry and not clock_port:
        raise InfraError("clock entry requires explicit core_clock_port (or core_tree.clock_port); port names are never guessed")
    if entry and entry.get("layer") != "M5":
        raise InfraError("core clock entry must terminate on M5")
    if entry:
        xy(entry.get("xy_um"), "clock entry", outline)
        if kd is not None:
            import master_slice as MS
            entry = dict(entry, xy_um=list(MS.snap_on_track(kd, entry["layer"], *entry["xy_um"])))
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
                bays=bays, reserved_bays=reserved,
                entry_pins=[p for p in sl.get("entry_pins", []) if p.get("pin")],
                unbound_entry_pins=sum(1 for p in sl.get("entry_pins", []) if not p.get("pin")),
                clock_ndr=sl.get("clock_ndr"))


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


# ASAP7 preferred directions: horizontal M2/M4/M6, vertical M3/M5/M7
H_LAYERS, V_LAYERS = ("M2", "M4", "M6"), ("M3", "M5", "M7")


def _seg_hits(a, b, rects):
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return [r for r in rects if x0 < r[2] and r[0] < x1 + 1e-9 and y0 < r[3] and r[1] < y1 + 1e-9
            and (x1 - x0 > 1e-9 and r[1] <= a[1] <= r[3] or y1 - y0 > 1e-9 and r[0] <= a[0] <= r[2])]


def trunk_pg_clearance(sl, plan):
    """COORD 10-26 (GEOM-REVIEW, VMR model): a planned core clock trunk may only run where PG allows it.  Every tree
    edge parent -> child is an L on core_tree.trunk_layers (one horizontal + one vertical layer); the edge is legal when
    at least one L orientation crosses no declared PG obstruction (macro PG pins/stripes, slice pg_obstructions_um
    {layer: [rects]}) on its layer.  A tree without a PG declaration is refused (PG not modelled = not a plan)."""
    tree = plan.get("core_tree")
    if not tree:
        return dict(verdict="NOT APPLICABLE")
    pg = sl.get("pg_obstructions_um")
    if pg is None:
        return dict(verdict="NOT RUN", issue="slice declares no pg_obstructions_um (macro PG pins/stripes); "
                                             "core trunk legality unknown -> no physical build")
    layers = tree.get("trunk_layers") or ["M4", "M5"]
    hl = [l for l in layers if l in H_LAYERS]
    vl = [l for l in layers if l in V_LAYERS]
    if len(hl) != 1 or len(vl) != 1:
        return dict(verdict="FAIL", issue=f"trunk_layers {layers} must name one horizontal and one vertical layer")
    hr, vr = pg.get(hl[0], []), pg.get(vl[0], [])
    xy_of = {c["name"]: c["xy_um"] for c in tree["nodes"]}
    if tree.get("clock_port") and plan.get("clock_entry"):
        xy_of["port:" + tree["clock_port"]] = plan["clock_entry"]["xy_um"]
    bad = []
    for c in list(tree["nodes"]) + [dict(name=g["inst"], parent=g["parent"], xy_um=g["xy_um"])
                                    for g in tree.get("gates", [])]:
        a, b = xy_of.get(c["parent"]), c["xy_um"]
        if a is None:
            continue
        ok = False
        for corner in ((b[0], a[1]), (a[0], b[1])):
            h_seg, v_seg = ((a, corner), (corner, b)) if corner[1] == a[1] else ((corner, b), (a, corner))
            if not _seg_hits(*h_seg, hr) and not _seg_hits(*v_seg, vr):
                ok = True
                break
        if not ok:
            bad.append(dict(edge=[c["parent"], c["name"]], from_um=a, to_um=b))
    return dict(verdict="FAIL" if bad else "PASS", layers=[hl[0], vl[0]], edges=len(tree["nodes"]),
                blocked_edges=len(bad), examples=bad[:10])


def emit_tcl(sl, kd=None):
    plan = compile_slice(sl, kd)
    tree = plan.get("core_tree")
    pgc = trunk_pg_clearance(sl, plan)
    if pgc["verdict"] not in ("PASS", "NOT APPLICABLE"):
        raise InfraError(f"core clock trunk PG clearance {pgc['verdict']}: {pgc.get('issue') or pgc['examples'][:3]}")
    band_info = []
    if tree and not tree.get("equal_load", True):
        q = tree.get("model_qualification", {})
        if q.get("measured_timing_used") is not False:
            raise InfraError("unequal-count tree refuses build until joint NLDM plan model qualifies both corners")
        # band_policy "gate" (default, unchanged for every existing caller): the 250+-20 TT / 202.5+-20 FF band gates.
        # band_policy "info" (METHODOLOGY 12.3a v5.0, COORD RULING S81-CORE-LAT-R9 19:22): the band is a design target,
        # reported only; the gates are tap window <= 20 ps and slew <= 80 ps at TT and FF (die related-pair STA decides).
        policy = q.get("band_policy", "gate")
        if policy not in ("gate", "info"):
            raise InfraError(f"unknown model_qualification band_policy {policy!r}")
        window_policy = q.get("window_policy", "gate")
        if window_policy not in ("gate", "info") or (window_policy == "info" and policy != "info"):
            raise InfraError("window_policy info requires band_policy info (12.3a design targets)")
        for corner, low, high in (("TT", 230., 270.), ("FF", 182.5, 222.5)):
            result = q.get("corners", {}).get(corner, {})
            if not result or (window_policy == "gate" and result["leaf_window"] > 20) or result["slew_max"] > 80 or (
                    policy == "gate" and (result["leaf_min"] < low or result["leaf_max"] > high)):
                raise InfraError(f"unequal-count tree model target FAIL/NOT RUN at {corner}; no physical build")
            if window_policy == "info":
                band_info.append(f"# core tap window INFO {corner}: {result['leaf_window']:g} ps (design target 20 ps; "
                                 "12.3a; actual related-pair STA/setup/hold sign-off unchanged)")
            if policy == "info":
                inb = low <= result["leaf_min"] and result["leaf_max"] <= high
                band_info.append(f"# core latency band INFO {corner}: model leaf {result['leaf_min']:g}..{result['leaf_max']:g} "
                                 f"window {result['leaf_window']:g} (target {low:g}..{high:g}: {'IN' if inb else 'OUT'}; not a gate, 12.3a)")
    lines = ["# Shared core infrastructure: plan-defined identities only; no measured adjustments.",
             "source /work/native_pg_binding.tcl", "source /work/core_infra_impl.tcl", "ot_ci_begin"]
    if band_info:
        lines[1:1] = band_info
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
        for g in t.get("gates", []):
            if "clone_of" in g:
                continue
            x, y = g["xy_um"]
            r = " ".join(f"{v:g}" for v in g["rect_um"])
            lines.append(f"ot_ci_tree_gate {word(g['inst'])} {g['master']} {word(g['parent'])} {word(g['clk_pin'])} "
                         f"{word(g['out_pin'])} {x:g} {y:g} {{{r}}}")
        # copies after every original: each copy reads its original's enable nets and takes members from its domain
        for g in t.get("gates", []):
            if "clone_of" not in g:
                continue
            x, y = g["xy_um"]
            r = " ".join(f"{v:g}" for v in g["rect_um"])
            pins = " ".join(word(q) for q in g["enable_pins"])
            mem = " ".join(word(q) for q in g["members"])
            lines.append(f"ot_ci_tree_gate_copy {word(g['inst'])} {g['master']} {word(g['clone_of'])} {word(g['parent'])} "
                         f"{word(g['clk_pin'])} {word(g['out_pin'])} {x:g} {y:g} {{{r}}} {{{pins}}} {{{mem}}}")
        for leaf in t["leaves"]:
            if leaf.get("load_class") == "gated_domain":
                lines.append(f"ot_ci_tree_domain {word(leaf['node'])} {leaf['domain_sinks']}")
                continue
            for s in leaf["sinks"]:
                lines.append(f"ot_ci_tree_sink {word(leaf['node'])} {word(s)}")
            if leaf.get("cts_open"):
                lines.append(f"ot_ci_tree_open {word(leaf['node'])}")
        lines.append("ot_ci_tree_finish")
        if any("clone_of" in g for g in t.get("gates", [])):
            # the copies exist only after this hook: the kit LEC must run on this netlist (lec.py --netlist)
            lines.append("ot_ci_lec_netlist /work/core_infra_post.v")
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


CTS_HOOK = "core_infra_cts.tcl"
REBIND_PY = "core_leaf_rebind.py"


def rebind_leaves(tree):
    """leaves a post-placement rebind may exchange sinks between: register class, not CTS-open (compile_slice has
    already asserted one stage depth and one clock port for every leaf)."""
    return [l["node"] for l in tree.get("leaves", [])
            if l.get("load_class", "register") == "register" and not l.get("cts_open")]


def emit_cts_tcl(plan):
    """PRE_CTS hook for a kit with a plan-built core tree (core_infra_cts.tcl + the plan's CTS-open count).
    TritonCTS then builds only the CTS-open nets; a leaf-complete tree (cts_open == []) skips it (R12, ODB-0370).
    Opt-in core_tree.post_place_rebind = "exact_count" (FLOW-GEN-2) adds the rebind leaf list and the pinned
    zero-logic pair sinks; without it the hook is byte-identical to the legacy one."""
    tree = plan.get("core_tree") or {}
    head = (f"# GENERATED by tools/die_plan/core_infra.py emit_cts_tcl: plan CTS-open nets = {len(tree.get('cts_open', []))}\n"
            f"set ::ot_ci_cts_plan_open {len(tree.get('cts_open', []))}\n")
    if tree.get("post_place_rebind") == "exact_count":
        pinned = sorted({s for pair in tree.get("same_leaf_pairs", []) for s in pair})
        head += ("# FLOW-GEN-2 post-placement exact-count leaf rebind (core_leaf_rebind.py)\n"
                 f"set ::ot_ci_leaf_rebind_leaves [list {' '.join(word(n) for n in rebind_leaves(tree))}]\n"
                 f"set ::ot_ci_leaf_rebind_pinned [list {' '.join(word(n) for n in pinned)}]\n")
    return head + (HERE / CTS_HOOK).read_text()


# --------------------------------------------------------------------------------------------- kit CTS-stage hook
# CTS-HOOK-PORT-1 (one implementation for every core-kit generator; first used by gen_core_kit_legacy, R12): a kit
# whose slice carries a plan-built core tree (core_infra_plan.json "core_tree") must run TritonCTS only on the plan's
# CTS-open nets (core_infra_cts.tcl at PRE_CTS) and must not let a post-CTS balancer edit the planned tree
# (tap_balance / leaf_affinity REPORT-ONLY).  A generator calls kit_cts_hook(kd, cfg) after master_slice.kit_apply
# and before it writes config.mk; a kit without a plan tree is left byte-identical.
CTS_PRE_CHAIN, CTS_POST_CHAIN = "core_infra_pre_cts.tcl", "core_infra_post_cts.tcl"
CTS_PRE_LINES = ("# S81-CORE-LAT-R12: plan-built tree -> TritonCTS only on CTS-open nets\n"
                 "source /work/core_infra_cts.tcl\n")
CTS_POST_LINES = ("# S81-CORE-LAT-R12: plan-built tree -> tap balance + leaf affinity measure/report only\n"
                  "set ::env(OT_TAP_REPORT_ONLY) 1\nset ::env(OT_LEAF_AFF_REPORT_ONLY) 1\n")
# kit stage scripts that build, re-tap or re-leaf the core clock themselves: a competing clock method for a plan tree
# (12.7c/12.8b: the plan owns the tree), and none of them has a report-only mode -> refused, never silently mixed
PLAN_TREE_CLOCK_EDITORS = ("regional_taps.tcl", "regional_taps_balance.tcl", "core_density_taps.tcl",
                           "core_tap_align.tcl", "f4_chain_leaf.tcl", "multiport_clock_stage_hold.tcl",
                           "head_lane_taps.tcl", "astk_zone_taps.tcl", "astk_face_taps.tcl")
_CFG_RE = re.compile(r"^\s*(override\s+)?export\s+([A-Za-z0-9_]+)\s*[:?]?=\s*(.*?)\s*$")
_SRC_RE = re.compile(r"^\s*source\s+\{?/work/([A-Za-z0-9_.-]+)\}?\s*$", re.M)


def cfg_effective(cfg, name):
    """GNU make value of `name` over generator config.mk lines: the last `override export` wins, else the last."""
    value, forced = None, False
    for line in cfg:
        m = _CFG_RE.match(line)
        if m and m[2] == name and (m[1] or not forced):
            value, forced = m[3], bool(m[1])
    return value


def _kit_stage_file(kd, cfg, var):
    val = cfg_effective(cfg, var)
    if not val:
        return None
    m = re.fullmatch(r"/work/([A-Za-z0-9_.-]+\.tcl)", val)
    if not m or not (kd / m[1]).is_file():
        raise SystemExit(f"{kd.name}: plan core tree: {var} = {val!r} is not a kit Tcl file; cannot chain {CTS_HOOK}")
    return m[1]


def _sourced(kd, name, seen=None):
    """name + every /work/*.tcl it sources (transitively) inside the kit."""
    seen = set() if seen is None else seen
    if name in seen or not (kd / name).is_file():
        return seen
    seen.add(name)
    for s in _SRC_RE.findall((kd / name).read_text()):
        _sourced(kd, s, seen)
    return seen


def _shared(kd, cfg, name, var):
    """True when the stage file is used by another config variable or sourced by another kit Tcl file."""
    ref = f"/work/{name}"
    for line in cfg:
        m = _CFG_RE.match(line)
        if m and m[2] != var and ref in m[3]:
            return True
    return any(p.name != name and ref in p.read_text() for p in sorted(kd.glob("*.tcl")))


def kit_cts_hook(kd, cfg):
    """Install the plan-tree CTS hook into a core kit; returns False (kit untouched) without a plan core tree.

    cfg is the generator's config.mk line list (mutated in place; the generator writes config.mk afterwards).
    PRE_CTS : core_infra_cts.tcl runs after the kit's own PRE_CTS hook (appended to that file when only PRE_CTS uses
              it, else via core_infra_pre_cts.tcl which sources both; added as PRE_CTS when the kit had none).
    POST_CTS: tap_balance / leaf_affinity REPORT-ONLY before the kit's own POST_CTS hook (prepended, or chained the
              same way); nothing to do without a POST_CTS hook.
    Fail-closed: plan tree without core_infra_cts.tcl, a stage hook that is not a kit Tcl file, or a kit stage script
    that builds / re-taps / re-leafs the clock itself (PLAN_TREE_CLOCK_EDITORS)."""
    kd = Path(kd)
    pj = kd / "core_infra_plan.json"
    if not pj.is_file() or not json.loads(pj.read_text()).get("core_tree"):
        return False
    if not (kd / CTS_HOOK).is_file():
        raise SystemExit(f"{kd.name}: plan tree without {CTS_HOOK} (core_infra.install too old)")
    pre, post = _kit_stage_file(kd, cfg, "PRE_CTS_TCL"), _kit_stage_file(kd, cfg, "POST_CTS_TCL")
    used = set()
    for f in (pre, post):
        if f:
            _sourced(kd, f, used)
    bad = sorted(used & set(PLAN_TREE_CLOCK_EDITORS))
    if bad:
        raise SystemExit(f"{kd.name}: plan core tree refuses kit clock editors at CTS {bad} (the plan owns the tree; "
                         "drop the tap / F4 / regional-tap option for a plan-tree kit)")
    if pre is None:
        (kd / CTS_PRE_CHAIN).write_text(f"# GENERATED by tools/die_plan/core_infra.py kit_cts_hook\n{CTS_PRE_LINES}")
        cfg.append(f"override export PRE_CTS_TCL = /work/{CTS_PRE_CHAIN}")
    elif _shared(kd, cfg, pre, "PRE_CTS_TCL"):
        (kd / CTS_PRE_CHAIN).write_text(f"# GENERATED by tools/die_plan/core_infra.py kit_cts_hook\n"
                                        f"source /work/{pre}\n{CTS_PRE_LINES}")
        cfg.append(f"override export PRE_CTS_TCL = /work/{CTS_PRE_CHAIN}")
    else:
        (kd / pre).write_text((kd / pre).read_text() + CTS_PRE_LINES)
    if post is not None:
        if _shared(kd, cfg, post, "POST_CTS_TCL"):
            (kd / CTS_POST_CHAIN).write_text(f"# GENERATED by tools/die_plan/core_infra.py kit_cts_hook\n"
                                             f"{CTS_POST_LINES}source /work/{post}\n")
            cfg.append(f"override export POST_CTS_TCL = /work/{CTS_POST_CHAIN}")
        else:
            (kd / post).write_text(CTS_POST_LINES + (kd / post).read_text())
    return True


def install(kd, sl):
    """Called by every kit's master_slice hook. No slice/pushdown means no change."""
    if sl.get("kind") not in ("core", "partition") or not sl.get("pushdown"):
        return False
    kd = Path(kd)
    script = emit_tcl(sl, kd)  # refuse incomplete plan BEFORE writing kit files
    wrapper = None
    if sl.get("logic_module") is not None or sl.get("logic_ports") is not None:
        if not sl.get("logic_module") or not sl.get("logic_ports"):
            raise InfraError("logic_module and logic_ports must be supplied together")
        wrapper = emit_wrapper(sl, sl["logic_module"], sl["logic_ports"])
    (kd / "master_core_infra.tcl").write_text(script)
    if wrapper is not None:
        (kd / "master_core_wrapper.v").write_text(wrapper)
    plan = compile_slice(sl, kd)
    (kd / "core_infra_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    if plan.get("core_tree"):
        # every core-kit generator chains it at PRE_CTS via kit_cts_hook (master_slice.plan_tree_cts); unused otherwise
        (kd / CTS_HOOK).write_text(emit_cts_tcl(plan))
        if plan["core_tree"].get("post_place_rebind"):
            shutil.copyfile(HERE / REBIND_PY, kd / REBIND_PY)
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
