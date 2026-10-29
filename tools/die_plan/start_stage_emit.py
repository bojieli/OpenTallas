#!/usr/bin/env python3
"""START-TREE-1 start stages as die-level flops beside their clock-tree node cell (DIE-HEAD-11, shared opt-in tool).

`count_align_plan --start-tree clock` puts every start (reset-release) stage that is not a data region on a clock-tree
node ('st:<tree_path>', bind region virtual=True).  The plan times such a stage as a flop clocked from that tree node.
This tool gives each stage its physical home and closes the loop with measured arrivals; any die can use it (inputs are
the generic bind / proof / die_trial clock-tree artefacts, nothing die-specific):

  emit   BIND PROOF --ctree DIR [--plan PLAN] --out OUT
         OUT/start_stages.json  ot_start_stages/1: one entry per virtual stage (ascii id, tree path, node cell, clock
                                net, PAD / EDGE_FALL, flop count, placement rect beside the node cell, parent, children)
                                + the die-level start nets (inputs from / outputs to data regions; direct region ports)
         OUT/start_stages.sv    module ot_die_start_stages: one ot_dp_landing_origin per stage (the plan's start stage
                                form: 3 sync flops + PAD, EDGE_FALL), clk = its own tap port of the die clock tree;
                                the start-tree ROOT stage is the die's root counter ot_dp_landing_root #(SETTLE) on its
                                own tap (same form as a root partition's origin), so nothing outside drives the root
         OUT/ctree.v, ctree.tcl the input die clock tree + one tap port t_st_<id>__clk per stage, driven by the node
                                cell's output net, pin at the stage's clock pin site (so the die clock run measures it)
  proof  PROOF --stages OUT/start_stages.json --arr TT=arr_TT.txt [--arr FF=...] --out NEWPROOF
         copy of a die_sta_related proof dir with the MEASURED stage clock pins added as taps '__st__<tree_path>'.
         die_sta_related.virtual_tap() only models a stage whose tap is absent, so the plan / bind / die STA (12.16d
         start-port recheck) then use the built arrival instead of the model (node + median tap leg).

Placement (geometry only): the stage's flops are one row segment on the node cell's row, right of the cell (then left,
then the rows above / below), clear of every die clock cell of the tree and of the other stages, both ends on a legal
die_trial SiteMap point when --plan is given.  No timing value is used.  Default flows are unchanged (new file).
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

SCHEMA = "ot_start_stages/1"
FLOP_W_UM = 1.08        # ASAP7 DFFHQNx1_ASAP7_75t_R LEF SIZE 1.08 x 0.27
CLK_CELL_W_UM = 1.62    # die clock cell footprint (BUFx24 / CKINVDCx16, LEF SIZE 1.62 x 0.27)
ROW_UM = 0.27
GAP_UM = 0.54           # two sites between the node cell and the stage
MAX_ROW_TRIES = 40
STAGE_MODULE = "ot_dp_landing_origin"
ROOT_MODULE = "ot_dp_landing_root"
ROOT_SETTLE = 64        # count_align_bind --root-settle default (root_settle_cycles)


class StageError(ValueError):
    pass


def path_id(path, encoding="unicode"):
    """Injective ASCII label of the declared tree-path encoding (legacy unicode or die_trial base36)."""
    if encoding not in ("unicode", "base36"):
        raise StageError(f"unknown tree-path encoding {encoding!r}")
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    valid = (all(c in chars for c in path[1:]) if encoding == "base36" else
             all(ord(c) >= 0x100 for c in path[1:]))
    if not path or path[0] != "h" or not valid:
        raise StageError(f"not a START-TREE-1 {encoding} tree path: {path!r}")
    return "h" + "".join(f"_{chars.index(c) if encoding == 'base36' else ord(c) - 0x100}" for c in path[1:])


def sv_name(x):
    return re.sub(r"\W", "_", x)


def stage_flops(r, settle=None):
    """flops of one stage: an origin = 3 sync + PAD + EDGE_FALL; the root counter = clog2(SETTLE + 1) count bits + start"""
    if settle is not None:
        return int(settle).bit_length() + 1
    return 3 + int(r.get("pad", 0) or 0) + int(bool(r.get("edge_fall")))


def stages_of(bind):
    """virtual regions of a --start-tree clock bind -> {region name: tree path}"""
    out = {}
    for x, r in bind["regions"].items():
        if r.get("virtual"):
            if not x.startswith("st:"):
                raise StageError(f"virtual region {x!r} is not an 'st:<tree_path>' stage")
            out[x] = x[3:].split("@", 1)[0]
    return out


def ctree_cells(ctree_v, ctree_tcl):
    """{instance: (cell, A net, Y net)} and {instance: (x, y)} of a die_trial ctree"""
    cells = {m.group(2): (m.group(1), m.group(3), m.group(4)) for m in re.finditer(
        r"^\s*(\w+)\s+(\w+)\s*\(\s*\.A\((\w+)\)\s*,\s*\.Y\((\w+)\)\s*\);", ctree_v, re.M)}
    xy = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(
        r"place_inst -name (\S+) -location \{([-\d.]+) ([-\d.]+)\}", ctree_tcl)}
    # Current clock-tree converter emits explicit native homes through ot_place.
    for m in re.finditer(r"^ot_place \{([^}]+)\} ([-\d.]+) ([-\d.]+) (\w+)\s*$", ctree_tcl, re.M):
        key, pos = m.group(1), (float(m.group(2)), float(m.group(3)))
        if key in xy and xy[key] != pos:
            raise StageError(f"conflicting clock home for {key}")
        xy[key] = pos
    return cells, xy


class Rows:
    """occupied x-intervals per row y (clock cells + placed stages)"""
    def __init__(self):
        self.r = {}

    def key(self, y):
        return round(y, 3)

    def add(self, x0, x1, y):
        self.r.setdefault(self.key(y), []).append((x0, x1))

    def free(self, x0, x1, y):
        return all(x1 <= a or x0 >= b for a, b in self.r.get(self.key(y), ()))


def polarity(cells, inst):
    """number of inverting die clock cells from the tree root to inst's output, inclusive (cell name has INV)"""
    drv = {y: k for k, (_, _, y) in cells.items()}
    n, k, seen = 0, inst, set()
    while k is not None:
        if k in seen:
            raise StageError(f"ctree.v: clock net loop at {k}")
        seen.add(k)
        c, a, _ = cells[k]
        n += "INV" in c.upper()
        k = drv.get(a)
    return n


def place_stage(xy, n_flops, rows, site=None, W=None, H=None):
    """row segment for n_flops beside a clock cell at xy (lower-left): right, left, then rows +-k"""
    w = n_flops * FLOP_W_UM
    x, y = xy
    for k in range(MAX_ROW_TRIES):
        for dy in ((0.0,) if k == 0 else (k * ROW_UM, -k * ROW_UM)):
            yy = y + dy
            for x0 in (x + CLK_CELL_W_UM + GAP_UM, x - GAP_UM - w):
                x1 = x0 + w
                if x0 < 0 or yy < 0 or (W is not None and x1 > W) or (H is not None and yy + ROW_UM > H):
                    continue
                if not rows.free(x0, x1, yy):
                    continue
                if site is not None and not (site.legal((x0, yy)) and site.legal((x1, yy + ROW_UM))):
                    continue
                return [round(x0, 3), round(yy, 3), round(x1, 3), round(yy + ROW_UM, 3)]
    raise StageError(f"no free legal row segment ({n_flops} flops) within {MAX_ROW_TRIES} rows of {xy}")


def emit(bind, meta, ctree_v, ctree_tcl, site=None, die_wh=(None, None), root_settle=None, path_encoding="unicode", reset_wave=False):
    """-> (stages json dict, start_stages.sv text, patched ctree.v, patched ctree.tcl)"""
    settle = int(root_settle if root_settle is not None else bind.get("root_settle_cycles", ROOT_SETTLE))
    if settle < 1:
        raise StageError(f"root SETTLE must be >= 1 (got {settle})")
    st = stages_of(bind)
    if not st:
        raise StageError("bind has no virtual start stages (not a --start-tree clock bind?)")
    sp = bind.get("start_ports") or {}
    reg = bind["regions"]
    cells, cxy = ctree_cells(ctree_v, ctree_tcl)
    rows = Rows()
    for inst, (x, y) in cxy.items():
        rows.add(x, x + CLK_CELL_W_UM, y)
    ncell, nxy = meta.get("node_cell", {}), meta.get("node_xy_um", {})
    # Resolve clock source from the actual A/Y connectivity, independently of placement identity.
    path_by_cell = {}
    for path, inst in ncell.items():
        try:
            path_id(path, path_encoding)
        except StageError:
            continue  # region-name aliases in proof.node_cell are not clock-tree paths
        key = inst if inst in cells else f"ck_{inst}" if f"ck_{inst}" in cells else None
        if key is None or key in path_by_cell:
            raise StageError(f"node_cell is missing or ambiguous for {path}: {inst}")
        path_by_cell[key] = path
    driver = {}
    for key, (_, _, net) in cells.items():
        if net in driver:
            raise StageError(f"clock net {net} has multiple drivers")
        driver[net] = key
    root_inputs = set(re.findall(r"\binput\s+(?:wire\s+)?([A-Za-z_][A-Za-z0-9_$]*)\s*;", ctree_v))
    ids = {}
    for x, p in st.items():
        path_id(p, path_encoding)
        inst = ncell.get(p)
        if inst is None:
            raise StageError(f"stage {x}: tree path not in the proof's node_cell")
        i = sv_name(inst[3:] if inst.startswith("ck_") else inst)    # one stage per tree node = its node cell
        if "@" in x:
            i += "_r" + hashlib.sha256(x.encode()).hexdigest()[:16]
        if i in ids.values():
            raise StageError(f"two stages on one node cell {inst}")
        ids[x] = i
    into = {}
    outof = {}
    for pid, c in sorted(sp.items()):
        if c["dst"] in into:
            raise StageError(f"start node {c['dst']} has two start ports ({into[c['dst']]}, {pid})")
        into[c["dst"]] = pid
        outof.setdefault(c["src"], []).append(pid)
    stages = []
    for x in sorted(st, key=lambda q: (len(st[q]), st[q])):
        p, r = st[x], reg[x]
        inst = ncell[p]
        key = inst if inst in cells else f"ck_{inst}" if f"ck_{inst}" in cells else None
        if key is None or key not in cxy:
            raise StageError(f"stage {x}: node cell {inst} not in the clock tree netlist / placement")
        root = r.get("parent") is None
        nf = stage_flops(r, settle if root else None)
        reset_ff = (2 + int(bool(r.get("edge_fall")))) if reset_wave and not root else 0
        nf += reset_ff
        rect = place_stage(cxy[key], nf, rows, site, *die_wh)
        inv = polarity(cells, key) % 2
        # an inverting tree (die_trial --clock-cell inv/inv2): a node cell with inverted output -> the stage takes the
        # cell's INPUT net (true polarity, one cell earlier); the measured proof (subcommand proof) times it as built
        net = cells[key][1] if inv else cells[key][2]
        source = driver.get(net)
        source_root = source is None
        if source_root:
            if net not in root_inputs:
                raise StageError(f"stage {x}: clock net {net} has no driver or declared root input")
            source_path, source_stages = "__source__", 0
        else:
            if source not in path_by_cell:
                raise StageError(f"stage {x}: clock driver {source} absent from node_cell")
            source_path = path_by_cell[source]
            source_stages = int(meta["node_stages"][source_path])
        rows.add(rect[0], rect[2], rect[1])
        tp = into.get(x)
        if r.get("parent") is not None and tp is None:
            raise StageError(f"stage {x}: has a parent but no start port into it")
        stages.append(dict(
            id=ids[x], region=x, tree_path_id=path_id(p, path_encoding), node_cell=key, node_xy_um=list(nxy.get(p, cxy[key])),
            clock_source_path=source_path, clock_source_cell=source, clock_source_root=source_root,
            clock_source_stages=source_stages,
            clock_net=net, clock_from="A" if inv else "Y", clock_port=f"t_st_{ids[x]}__clk", clock_pin_xy_um=[rect[0], rect[1]],
            rect_um=rect, flops=nf, pad=int(r.get("pad", 0) or 0), edge_fall=bool(r.get("edge_fall")),
            root=root, module=ROOT_MODULE if root else STAGE_MODULE, settle=settle if root else None, start_port_in=tp, parent=r.get("parent"),
            start_ports_out=sorted(outof.get(x, [])), children=sorted(sp[q]["dst"] for q in outof.get(x, []))))
    by_region = {s["region"]: s for s in stages}

    def start_net(x):
        return f"st_{by_region[x]['id']}_start" if x in by_region else f"rs_{sv_name(x)}"
    ins, outs, direct = [], [], []
    for pid, c in sorted(sp.items()):
        a, b = c["src"] in by_region, c["dst"] in by_region
        if a and b:
            continue
        if b:
            ins.append(dict(port=pid, src_region=c["src"], src_part=c.get("launch_part"), net=start_net(c["src"]),
                            stage=by_region[c["dst"]]["id"]))
        elif a:
            outs.append(dict(port=pid, dst_region=c["dst"], dst_part=c.get("capture_part"),
                             net=f"pst_{sv_name(c['dst'])}", stage=by_region[c["src"]]["id"]))
        else:
            direct.append(dict(port=pid, src_region=c["src"], dst_region=c["dst"], src_part=c.get("launch_part"),
                               dst_part=c.get("capture_part")))
    in_nets = sorted({i["net"] for i in ins})
    sv = [f"// GENERATED by tools/die_plan/start_stage_emit.py ({SCHEMA}): START-TREE-1 die-level start stages,",
          "// one ot_dp_landing_origin per virtual tree-node stage, clocked by its own die clock-tree tap port.",
          "module ot_die_start_stages ("]
    roots = [s["id"] for s in stages if s["root"]]
    real_root = reg.get(bind.get("root"))
    root_in_partition = (isinstance(real_root, dict) and real_root.get("virtual") is False
                         and real_root.get("parent") is None)
    if len(roots) != 1 and not (not roots and root_in_partition):
        raise StageError(f"start tree must have exactly one root stage or a declared real root partition, found {roots}")
    # A real root partition already contains ot_dp_landing_root. Its rs_* output
    # feeds virtual stages through die_inputs; emitting another root changes reset timing.
    reset_inputs = []
    if reset_wave:
        if not (len(roots) == 1 or root_in_partition):
            raise StageError("bounded reset wave needs one virtual root or the declared real root partition")
        reset_parts = {e['src_region']: e['src_part'] for e in ins}
        if any(not p for p in reset_parts.values()):
            raise StageError("bounded reset wave needs physical real-parent reset outputs")
        reset_inputs = [dict(region=n, part=p, net='rraw_' + sv_name(n)) for n,p in sorted(reset_parts.items())]
    pl = ((["    input  wire rst_raw_n"] if roots else []) + [f"    input  wire {e['net']}" for e in reset_inputs]) if reset_wave else ["    input  wire rst_raw_n"]
    pl += [f"    input  wire {s['clock_port']}" for s in stages]
    pl += [f"    input  wire {n}" for n in in_nets]
    pl += [f"    output wire {o['net']}" for o in outs]
    sv.append(",\n".join(pl))
    sv.append(");")
    for s in stages:
        sv.append(f"    wire st_{s['id']}_start;")
    for s in stages:
        local_reset = "rst_raw_n"
        if reset_wave and not s["root"]:
            parent_reset = (f"st_{by_region[s['parent']]['id']}_rraw" if s['parent'] in by_region
                            else 'rraw_' + sv_name(s['parent']))
            name, clk = s['id'], s['clock_port']
            local_reset = f"st_{name}_rraw"
            sv += [f"    wire {local_reset};",
                   f"    ot_die_start_reset_relay #(.EDGE_FALL({int(s['edge_fall'])})) u_rst_{name} "
                   f"(.clk({clk}), .d({parent_reset}), .q({local_reset}));"]
            s['reset_parent'] = parent_reset
            s['reset_output'] = local_reset
            s['reset_flops'] = 2 + int(s['edge_fall'])
        if s["root"]:
            if reset_wave:
                # The single timed local root reset feeds the root counter and
                # starts the bounded relay stream; it never fans out globally.
                sv.append(f"    wire st_{s['id']}_rraw = rst_raw_n;")
                s['reset_parent'] = 'rst_raw_n'
                s['reset_output'] = f"st_{s['id']}_rraw"
                s['reset_flops'] = 0
            # the start-tree root stage IS the die's root counter (DIE-HEAD-11): SETTLE cycles after the raw release on
            # its own tree tap, the same ot_dp_landing_root a root partition uses; no die-top root start input
            sv.append(f"    {ROOT_MODULE} #(.SETTLE({s['settle']})) u_st_{s['id']} "
                      f"(.clk({s['clock_port']}), .rst_raw_n(rst_raw_n), .start(st_{s['id']}_start));")
            continue
        ps = start_net(s["parent"])
        sv.append(f"    {STAGE_MODULE} #(.PAD({s['pad']}), .EDGE_FALL({int(s['edge_fall'])})) u_st_{s['id']} "
                  f"(.clk({s['clock_port']}), .rst_raw_n({local_reset}), .p_start({ps}), .start(st_{s['id']}_start));")
    for o in outs:
        sv.append(f"    assign {o['net']} = st_{o['stage']}_start;")
    sv.append("endmodule")
    if reset_wave:
        sv += ["(* keep_hierarchy *) module ot_die_start_reset_relay #(parameter bit EDGE_FALL=0) (",
               "    input wire clk, input wire d, output wire q);",
               '    (* keep = "true" *) reg r0, r1;', "    wire x;",
               "    if (EDGE_FALL) begin: g_fall",
               '        (* keep = "true" *) reg rf;', "        always @(negedge clk) rf <= d;",
               "        assign x=rf;", "    end else begin: g_rise assign x=d; end",
               "    always @(posedge clk) begin r0<=x; r1<=r0; end",
               "    assign q=r1;", "endmodule"]
    # die clock tree: one tap port per stage on its node cell's output net, pin at the stage's clock pin site
    mh = re.search(r"module\s+(\w+)\s*\(([^)]*)\);", ctree_v)
    if mh is None:
        raise StageError("ctree.v: module header not found")
    have = {q.strip() for q in mh.group(2).split(",")}
    clash = [s["clock_port"] for s in stages if s["clock_port"] in have]
    if clash:
        raise StageError(f"ctree.v already has stage tap ports {clash[:3]}")
    new_ports = [s["clock_port"] for s in stages]
    v = ctree_v[:mh.start(2)] + mh.group(2) + ", " + ", ".join(new_ports) + ctree_v[mh.end(2):]
    k = v.index(";", v.index("module")) + 1
    v = v[:k] + "".join(f"\n  output {q};" for q in new_ports) + v[k:]
    e = v.rindex("endmodule")
    v = v[:e] + "".join(f"  assign {s['clock_port']} = {s['clock_net']};\n" for s in stages) + v[e:]
    pins = "".join(f"place_pin -pin_name {s['clock_port']} -layer M9 -location {{{s['clock_pin_xy_um'][0]:.3f} "
                   f"{s['clock_pin_xy_um'][1]:.3f}}} -pin_size {{0.04 0.32}}\n" for s in stages)
    m = list(re.finditer(r"^place_pin .*\n", ctree_tcl, re.M))
    if not m:
        raise StageError("ctree.tcl: no place_pin lines")
    t = ctree_tcl[:m[-1].end()] + pins + ctree_tcl[m[-1].end():]
    doc = dict(schema=SCHEMA, stage_module=STAGE_MODULE, root_module=ROOT_MODULE, root_settle=settle,
               flop_w_um=FLOP_W_UM, stages=stages,
               die_inputs=ins, die_outputs=outs, direct_ports=direct,
               **(dict(reset_wave="bounded_synchronous_parent_relays", reset_inputs=reset_inputs,
                       reset_rule="ordinary timed relay flops, no async controls or false paths; cold/warm flush + START lead proven separately") if reset_wave else {}),
               counts=dict(stages=len(stages), flops=sum(s["flops"] for s in stages), die_inputs=len(ins),
                           die_outputs=len(outs), direct_ports=len(direct),
                           max_cell_to_stage_um=max(abs(s["rect_um"][0] - cxy[s["node_cell"]][0]) +
                                                    abs(s["rect_um"][1] - cxy[s["node_cell"]][1]) for s in stages)))
    return doc, "\n".join(sv) + "\n", v, t


def proof_with_stages(proof, stages_doc, arrs, out):
    """copy a die_sta_related proof dir and add every stage's MEASURED clock pin as tap '__st__<tree_path>' (arrival
    files: die_trial / combo 'T <port> <late> <early> [slew]' lines).  DIE-HEAD-12: a both-edge readout (FLOW-ONEMODEL-2
    die_trial readout, 'F <port> <late> <early> [slew]' = the source FALLING edge at the same pin) also gives the stage
    tap its measured fall_late_ps / fall_early_ps, so an EDGE_FALL stage sample is timed on its own fall arrival like
    every other tap (tap_fall_merge keys taps by port and never sees the '__st__' names; without an F row the stage tap
    stays rise-only and a fall sample on it fails closed, as before).  Run it AFTER tap_fall_merge (which resets fall
    fields on every tap it does not match)."""
    out = Path(out)
    if out.exists():
        raise StageError(f"{out} exists")
    shutil.copytree(proof, out)
    st = stages_doc["stages"]
    for corner, f in arrs.items():
        T, F = {}, {}
        for line in Path(f).read_text().splitlines():
            s = line.split()
            if s and s[0] == "T":
                T[s[1]] = s[2:]
            elif s and s[0] == "F" and len(s) >= 4:
                F[s[1]] = s[2:]
        pf = out / f"tap_arrivals_{corner}.json"
        d = json.loads(pf.read_text())
        meta = d
        have = {t["port"] for t in d["taps"]}
        for s in st:
            identity = s["region"][3:]
            placement_path = identity.split("@", 1)[0]
            if "clock_source_path" not in s and s.get("clock_from") == "A":
                raise StageError("A-driven legacy stage manifest lacks actual clock source; re-emit")
            path = s.get("clock_source_path", placement_path)
            source_root = bool(s.get("clock_source_root"))
            if source_root:
                if path != "__source__" or s.get("clock_source_stages") != 0:
                    raise StageError("invalid root-input clock source metadata")
                for field in ("node_late_ps", "node_early_ps", "node_fall_late_ps", "node_fall_early_ps",
                              "node_stages", "cppr_node_range_ps"):
                    meta.setdefault(field, {})["__source__"] = 0
                meta["cppr_node_range_ps"]["__source__@fall"] = 0
                meta.setdefault("node_xy_um", {})["__source__"] = None
            elif path not in meta["node_stages"]:
                raise StageError(f"clock source path {path} absent from measured proof")
            k = f"__st__{identity}"
            if k in have:
                raise StageError(f"proof {pf} already has {k}")
            if s["clock_port"] not in T:
                raise StageError(f"{f}: no arrival for {s['clock_port']}")
            v = T[s["clock_port"]]
            d["taps"].append(dict(port=k, part=None, late_ps=float(v[0]), early_ps=float(v[1]),
                                  **({"slew_ps": float(v[2])} if len(v) > 2 else {}), cppr_node="__source__" if source_root else "h", tree_path=path,
                                  clock_source_root=source_root, placement_tree_path=placement_path,
                                  stages_from_root=int(meta["node_stages"][path]), xy_um=list(s["clock_pin_xy_um"]),
                                  leaf_cell=s.get("clock_source_cell", s["node_cell"]),
                                  placement_cell=s["node_cell"], start_stage=s["id"],
                                  **({"fall_late_ps": float(F[s["clock_port"]][0]),
                                      "fall_early_ps": float(F[s["clock_port"]][1])} if s["clock_port"] in F else {})))
        d.setdefault("basis_start_stages", f"{SCHEMA} measured stage clock pins ({len(st)})")
        pf.write_text(json.dumps(d, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emit")
    e.add_argument("bind")
    e.add_argument("proof", help="die_sta_related proof dir (tap_arrivals_<C>.json with node_cell / node_xy_um)")
    e.add_argument("--corner", default="TT")
    e.add_argument("--ctree", required=True, help="die_trial clock dir with ctree.v + ctree.tcl")
    e.add_argument("--plan", help="die plan: stage rows must be legal die_trial SiteMap points")
    e.add_argument("--reset-wave", action="store_true", help="bounded ordinary synchronous reset relay stream along START graph; real root/local reset inputs required")
    e.add_argument("--path-encoding", choices=("unicode", "base36"), default="unicode",
                   help="declared tree path alphabet; die_trial/trial_tap_arrivals use base36")
    e.add_argument("--out", required=True)
    e.add_argument("--root-settle", type=int, help="root counter SETTLE cycles (default: bind root_settle_cycles, else 64)")
    p = sub.add_parser("proof")
    p.add_argument("proof")
    p.add_argument("--stages", required=True)
    p.add_argument("--arr", action="append", required=True, metavar="CORNER=FILE")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "emit":
        bind = json.loads(Path(a.bind).read_text())
        meta = json.loads((Path(a.proof) / f"tap_arrivals_{a.corner}.json").read_text())
        cd = Path(a.ctree)
        site, wh = None, (None, None)
        if a.plan:
            import schema as S
            import die_trial as DT
            P = S.Plan(S.load(a.plan))
            site, wh = DT.SiteMap(P), (P.W, P.H)
        doc, sv, v, t = emit(bind, meta, (cd / "ctree.v").read_text(), (cd / "ctree.tcl").read_text(), site, wh,
                            a.root_settle, a.path_encoding, a.reset_wave)
        o = Path(a.out)
        o.mkdir(parents=True, exist_ok=True)
        (o / "start_stages.json").write_text(json.dumps(doc, indent=1))
        (o / "start_stages.sv").write_text(sv)
        (o / "ctree.v").write_text(v)
        (o / "ctree.tcl").write_text(t)
        print(json.dumps(doc["counts"]))
    else:
        arrs = dict(x.split("=", 1) for x in a.arr)
        proof_with_stages(a.proof, json.loads(Path(a.stages).read_text()), arrs, a.out)
        print(f"proof {a.out}: {len(json.loads(Path(a.stages).read_text())['stages'])} measured stage taps")


if __name__ == "__main__":
    main()
