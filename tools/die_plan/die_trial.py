#!/usr/bin/env python3
"""Trial die runs (early full-chip prototype) from a die_plan.json: every partition as an abstract, the die clock tree,
the die global route, die STA on budget stand-ins and die IR -- integration problems found long before G4.

    die_trial.py kit    PLAN.json --out DIR [--views VIEWDIR] [--leaf-um 600] [--rep-um 450] [--coarse-um 0.72]
    die_trial.py report DIR                       # parse grt / clock / psm / sta outputs -> DIR/trial.json
    die_trial.py clock  DIR                       # clock skew post-processing only (DIR/clock/*)

KIT (DIR/):
  abstracts/<module>.lef  partition abstract per TYPE: exact plan outline + every plan pin (buses, ft slots; the same
                          rectangles as the G3 kit io.tcl), interior clock-tap / reset pins on M7, the kit's M7 PG
                          stripes as VDD/VSS pins, OBS M1..M3 over the whole outline (partition logic) and OBS over every
                          planned hard core / ROM macro (type hard_cores[] origin/outline) up to the core view's top
                          layer (parsed from its LEF; M5 when no view).  A closed partition view in VIEWDIR/<type>/
                          <module>.lef replaces the abstract (none exist today for s81 / s81_head).
  grt/                    die global route of every die-level net on the abstracts: the ft slot crossings of every
                          partition instance (one net per bit, slot in pin -> out pin, the route the partition's
                          stations sit on), the reset spine (root -> every arst_n tap).  Capacity = the plan's budget:
                          M4..M7 at type ft_track_frac (default 0.25: the rest is the partition's own logic), M8 / M9
                          at layer_budget.cut_avail (0.6) of the PG-free tracks, die PG stripes and the die clock
                          H-tree (5 tracks per wire: 2W2S NDR + shields) as M8 / M9 obstructions.  M1-M3 get coarse
                          tracks (--coarse-um) so the GRT gcell stays die-sized; they are not routed.
  clock/                  die clock H-tree from the spine root to every partition clock tap (schema.tap_grid + core
                          taps): recursive bisection of the die (longer axis first), empty branches pruned, a branch
                          buffer at every node, repeaters every --rep-um along each leg, a leaf driver per leaf region
                          (<= --leaf-um) driving its taps.  ctree.v + place.tcl + ctree_<corner>.tcl: OpenROAD
                          estimate_parasitics -placement (M8/M9 RC, 2W NDR = R/2) and per-tap / per-node arrival at
                          SS / TT / FF.  `clock` then computes insertion and seam tap-to-tap skew with CPPR (common
                          path to the lowest common tree node removed) and a flat OCV derate on the uncommon path.
  psm/                    die PDN (die.pg.grid on M8 / M9 strapping the abstracts' M7 PG pins) + PDNSim with an
                          estimated per-partition power (set_pdnsim_inst_power) and C4 power bumps on a regular grid
                          outside the die IO windows (die_io.json).
  sta/                    budget stand-ins for die_sta.py (DIE-STA): PARTS/<module>/6_final.v per type = one face
                          flop per pin bit (in: pin -> D, out: QN -> pin; ft: in pin -> station 0, last station -> out
                          pin), each clocked from its nearest plan tap; die top = die_sta.py top (gen_rtl.die_top);
                          spine_<corner>.json = the clock tree's per-tap arrival as source latency offsets.

All runs are read-only diagnostics; nothing is written into the plan.  Heavy steps run in docker (openroad/orfs image)
through ot-run on a 1 TB host: DIR/run_<step>.sh.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import die_sta  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:latest")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
ROOT = HERE.parent.parent
BUF = "BUFx24_ASAP7_75t_R"
FLOP = "DFFHQNx1_ASAP7_75t_R"
NDR_TRACKS = 5                       # clock wire 2W2S + a shield each side (hbm_arch clock_htree.py)
TAP_LOAD_FF = 3.0                    # partition tap buffer input (ASSUMED: BUFx24 A ~ 2-3 fF)
OCV = (0.03, 0.05)                   # flat clock OCV derates reported (ASSUMED; no project OCV table)
CORNER_LIB = {"SS": "SS", "TT": "TT", "FF": "FF"}
# M8 / M9 setRC (ASAP7 platform setRC.tcl, kohm / fF per um); clock NDR 2W2S: R / 2, C x 1.1 (ASSUMED)
WIRE_R = (8.44765e-3 + 8.89556e-3) / 2 / 2
WIRE_C = (1.03962e-1 + 9.28446e-2) / 2 * 1.1


def sv(s):
    return gen_rtl.sv_id(s)


# --------------------------------------------------------------------------------------------------------- abstracts
_LEF_TOP = {}


def lef_top_layer(path):
    """highest metal layer named in a LEF (pins + OBS); None if the file is missing."""
    p = (ROOT / path) if path and not Path(path).is_absolute() else Path(path or "")
    if not path or not p.is_file():
        return None
    if str(p) not in _LEF_TOP:
        top = 0
        for m in re.finditer(r"LAYER\s+M(\d+)\b", p.read_text(errors="replace")):
            top = max(top, int(m.group(1)))
        _LEF_TOP[str(p)] = f"M{top}" if top else None
    return _LEF_TOP[str(p)]


def core_obs(t):
    """[(x0, y0, x1, y1, top_layer, module, has_view)] of a type's planned hard cores (ROM macros, closed leaves)."""
    out = []
    for h in t.get("hard_cores", []) or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        x0, y0 = h["origin_um"]
        w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        top = lef_top_layer(h.get("lef"))
        out.append((x0, y0, x0 + w, y0 + hh, top or "M5", h.get("module", "?"), top is not None))
    return out


def abstract_lef(P, tn, slots_only_pins=False):
    """partition abstract (see module doc).  Returns (lef text, stats)."""
    t = P.types[tn]
    w, h = t["outline_um"]
    top = P.layer_budget["partition_signal_max"]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {t['module']}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  SIZE {w:.4f} BY {h:.4f} ;"]

    def pin(name, d, use, rects):
        out = [f"  PIN {name}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT"]
        for ln, x0, y0, x1, y1 in rects:
            out += [f"      LAYER {ln} ;", f"        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;"]
        return out + ["    END", f"  END {name}"]
    dirs = {}
    for b in t.get("buses", []):
        dirs[b["name"]] = "INPUT" if b["dir"] == "in" else "OUTPUT"
    for sl in t.get("ft_slots", []):
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "INPUT", "OUTPUT"
    npins = 0
    for bus, bit, ln, x, y, f in sorted(gen_phys.type_pins(P, tn), key=lambda p: (p[0], p[1])):
        lw = gen_phys.LAYER_W.get(ln, 0.04) / 2
        pl = gen_phys.PIN_LEN_UM
        r = {"E": (x - pl, y - lw, x, y + lw), "W": (x, y - lw, x + pl, y + lw),
             "N": (x - lw, y - pl, x + lw, y), "S": (x - lw, y, x + lw, y + pl)}[f]
        L += pin(f"{bus}[{bit}]", dirs.get(bus, "INPUT"), "SIGNAL", [(ln, *r)])
        npins += 1
    tw = gen_phys.LAYER_W.get(top, 0.032) / 2
    for name, x, y in gen_phys.tap_pins(P, tn):
        L += pin(name, "INPUT", "SIGNAL" if name == "arst_n" else "CLOCK",
                 [(top, x - tw, y - 2 * gen_phys.PIN_LEN_UM, x + tw, y + 2 * gen_phys.PIN_LEN_UM)])
    # PG: the kit's M7 stripes only (gen_phys.PDN: width 0.288, VSS one width + spacing 0.096 after VDD, pitch 8.64)
    for net, j in (("VDD", 0), ("VSS", 1)):
        rects = []
        c = 4.128 + j * (0.288 + 0.096)
        while c + 0.144 < w:
            rects.append(("M7", c - 0.144, 0.0, c + 0.144, h))
            c += 8.64
        L += pin(net, "INOUT", "POWER" if net == "VDD" else "GROUND", rects)
    cores = core_obs(t)
    L += ["  OBS"] + [f"    LAYER M{i} ;\n      RECT 0 0 {w:.4f} {h:.4f} ;" for i in (1, 2, 3)]
    by_layer = defaultdict(list)
    for x0, y0, x1, y1, tl, _, _ in cores:
        for i in range(4, min(int(tl[1:]), int(top[1:])) + 1):
            by_layer[i].append((x0, y0, x1, y1))
    for i in sorted(by_layer):
        L.append(f"    LAYER M{i} ;")
        L += [f"      RECT {a:.4f} {b:.4f} {c:.4f} {d:.4f} ;" for a, b, c, d in by_layer[i]]
    L += ["  END", f"END {t['module']}", "END LIBRARY", ""]
    st = dict(pins=npins, cores=len(cores), cores_with_view=sum(1 for c in cores if c[6]),
              core_area_um2=round(sum((c[2] - c[0]) * (c[3] - c[1]) for c in cores), 1),
              core_top_layers=sorted({c[4] for c in cores}))
    return "\n".join(L), st


# ------------------------------------------------------------------------------------------------------- clock tree
def clock_taps(P):
    """[(part, port, x_die, y_die)] every partition clock tap (R4 grid + early core taps), snapped as the kit."""
    out = []
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        for port, x, y in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn):
            X, Y = P.to_die(n, (x, y))
            out.append((n, port, round(X, 3), round(Y, 3)))
    return out


def build_htree(P, taps, leaf_um=600.0):
    """explicit H-tree: nodes {id: dict(x, y, parent, level, kids, taps)} rooted at the spine root.  Region bisection
    along the longer axis at the region midpoint; the child node sits at the child region centre (the leg runs along
    the split axis, so every node-to-node leg is a straight M8 (H) or M9 (V) run).  The first leg goes from the spine
    root to the first child centre (root need not be the centre).  Regions without taps are pruned."""
    W, H = P.W, P.H
    root = P.clock.get("spine", {}).get("root_um") or [W / 2, H / 2]
    nodes = {}

    def mk(x, y, parent, level, region):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[round(v, 3) for v in region])
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i

    def rec(nid, region, tlist):
        x0, y0, x1, y1 = region
        if max(x1 - x0, y1 - y0) <= leaf_um or len(tlist) <= 1:
            nodes[nid]["taps"] = tlist
            return
        if x1 - x0 >= y1 - y0:
            xm = (x0 + x1) / 2
            halves = [((x0, y0, xm, y1), [t for t in tlist if t[2] < xm]), ((xm, y0, x1, y1), [t for t in tlist if t[2] >= xm])]
        else:
            ym = (y0 + y1) / 2
            halves = [((x0, y0, x1, ym), [t for t in tlist if t[3] < ym]), ((x0, ym, x1, y1), [t for t in tlist if t[3] >= ym])]
        for reg, tl in halves:
            if not tl:
                continue
            cx, cy = (reg[0] + reg[2]) / 2, (reg[1] + reg[3]) / 2
            px, py = nodes[nid]["x"], nodes[nid]["y"]
            # keep legs straight: move along the split axis only (the other coordinate is shared by construction,
            # except below the off-centre spine root, where an L-leg via a corner node is used)
            if abs(px - cx) > 1e-6 and abs(py - cy) > 1e-6:
                mid = mk(cx, py, nid, nodes[nid]["level"] + 1, reg)
                nodes[mid]["corner"] = True
                c = mk(cx, cy, mid, nodes[nid]["level"] + 1, reg)
            else:
                c = mk(cx, cy, nid, nodes[nid]["level"] + 1, reg)
            rec(c, reg, tl)
    r = mk(root[0], root[1], None, 0, (0, 0, W, H))
    rec(r, (0.0, 0.0, W, H), list(taps))
    return nodes


def tree_netlist(nodes, taps, rep_um=450.0):
    """buffered tree: a BUF at every node (branch / leaf driver), repeaters every rep_um along each leg.
    -> (verilog, placements [(inst, x, y)], tap ports [(port, x, y)], node_buf {node id: inst}, path {tap port: [inst]})"""
    cells, place, wires = [], [], []
    node_buf, parent_of = {}, {}
    k = 0

    def net(i):
        return f"n{i}"
    # node buffers
    for i, nd in nodes.items():
        node_buf[i] = f"b{i}"
    for i, nd in sorted(nodes.items()):
        if nd["parent"] is None:
            src = "root"
        else:
            p = nodes[nd["parent"]]
            L = abs(p["x"] - nd["x"]) + abs(p["y"] - nd["y"])
            nrep = max(0, int(math.ceil(L / rep_um)) - 1)
            src = f"{net(nd['parent'])}"
            prev_inst = node_buf[nd["parent"]]
            for j in range(nrep):
                f = (j + 1) / (nrep + 1)
                x = p["x"] + (nd["x"] - p["x"]) * f
                y = p["y"] + (nd["y"] - p["y"]) * f
                inst = f"r{i}_{j}"
                o = f"rn{i}_{j}"
                cells.append(f"  {BUF} {inst} (.A({src}), .Y({o}));")
                wires.append(o)
                place.append((inst, x, y))
                parent_of[inst] = prev_inst
                prev_inst = inst
                src = o
            parent_of[node_buf[i]] = prev_inst
        cells.append(f"  {BUF} {node_buf[i]} (.A({src}), .Y({net(i)}));")
        wires.append(net(i))
        place.append((node_buf[i], nd["x"], nd["y"]))
    tap_ports = []
    for i, nd in sorted(nodes.items()):
        for (part, port, x, y) in nd["taps"]:
            tp = f"t_{sv(part)}__{port}"
            tap_ports.append((tp, x, y, part, port, i))
            cells.append(f"  assign {tp} = {net(i)};")
    v = ["module ctree (root, " + ", ".join(t[0] for t in tap_ports) + ");", "  input root;"]
    v += [f"  output {t[0]};" for t in tap_ports]
    v += [f"  wire {w};" for w in wires]
    v += [c for c in cells if not c.lstrip().startswith("assign")]
    v += [c for c in cells if c.lstrip().startswith("assign")]
    v.append("endmodule")
    return "\n".join(v) + "\n", place, tap_ports, node_buf, parent_of


def clock_kit(P, out, leaf_um, rep_um):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    taps = clock_taps(P)
    nodes = build_htree(P, taps, leaf_um)
    v, place, tap_ports, node_buf, parent_of = tree_netlist(nodes, taps, rep_um)
    (out / "ctree.v").write_text(v)
    segs = []
    for i, nd in nodes.items():
        if nd["parent"] is not None:
            p = nodes[nd["parent"]]
            segs.append((p["x"], p["y"], nd["x"], nd["y"], nd["level"]))
    # leaf -> tap last-mile legs (L: horizontal on M8, then vertical on M9)
    leaf_legs = []
    for tp, x, y, part, port, i in tap_ports:
        nd = nodes[i]
        leaf_legs.append((nd["x"], nd["y"], x, y))
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}",
           "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }",
           "read_verilog /work/clock/ctree.v", "link_design ctree",
           f"initialize_floorplan -die_area {{0 0 {P.W:g} {P.H:g}}} -core_area {{0 0 {P.W:g} {P.H:g}}} -site asap7sc7p5t",
           "source /work/clock/make_tracks.tcl"]
    sz9 = "{0.04 0.32}"
    root = nodes[0]
    tcl.append(f"place_pin -pin_name root -layer M9 -location {{{root['x']:.3f} {root['y']:.3f}}} -pin_size {sz9}")
    for tp, x, y, *_ in tap_ports:
        tcl.append(f"place_pin -pin_name {tp} -layer M9 -location {{{x:.3f} {y:.3f}}} -pin_size {sz9}")
    for inst, x, y in place:
        tcl.append(f"place_inst -name {inst} -location {{{max(0.0, x):.3f} {max(0.0, y):.3f}}} -status PLACED")
    tcl += [f"set_wire_rc -signal -resistance {WIRE_R:.6e} -capacitance {WIRE_C:.6e}",
            f"set_wire_rc -clock -resistance {WIRE_R:.6e} -capacitance {WIRE_C:.6e}",
            "estimate_parasitics -placement",
            "create_clock -name vclk -period 833.333",
            f"set_driving_cell -lib_cell {BUF} -pin Y [get_ports root]",
            "set_input_delay 0 -clock vclk [get_ports root]",
            f"set_load {TAP_LOAD_FF} [all_outputs]",
            "set_output_delay 0 -clock vclk [all_outputs]",
            "set fh [open /work/clock/arr_$::env(CORNER).txt w]",
            # arrival at a port = period - slack (output delay 0); at a buffer output pin = its arrival property
            "foreach p [get_ports t_*] { set n [get_full_name $p]; "
            "set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; "
            "puts $fh \"T $n [expr {833.333 - $smx}] [expr {$smn}]\" }",
            "foreach i [get_cells b*] { set q [get_pins [get_full_name $i]/Y]; "
            "puts $fh \"N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]\" }",
            "close $fh",
            "report_checks -path_delay max -group_path_count 1 -format full -fields {cap slew fanout}",
            "puts OT_DONE"]
    (out / "ctree.tcl").write_text("\n".join(tcl) + "\n")
    meta = dict(leaf_um=leaf_um, rep_um=rep_um, buffer=BUF, wire_r_kohm_um=WIRE_R, wire_c_ff_um=WIRE_C,
                tap_load_ff=TAP_LOAD_FF, nodes=len(nodes), leaves=sum(1 for n in nodes.values() if n["taps"]),
                repeaters=sum(1 for i, *_ in place if i.startswith("r")), taps=len(tap_ports),
                wire_um=round(sum(abs(a - c) + abs(b - d) for a, b, c, d, _ in segs) +
                              sum(abs(a - c) + abs(b - d) for a, b, c, d in leaf_legs), 1),
                levels=max(n["level"] for n in nodes.values()))
    tree = dict(meta=meta, nodes={i: {k: v for k, v in n.items() if k != "taps"} | dict(ntaps=len(n["taps"]))
                                  for i, n in nodes.items()},
                taps=[dict(port=tp, part=part, tap=port, xy=[x, y], node=i) for tp, x, y, part, port, i in tap_ports],
                node_buf=node_buf, parent_of=parent_of)
    (out / "tree.json").write_text(json.dumps(tree) + "\n")
    return nodes, segs, leaf_legs, meta


def reserve_rects(segs, leaf_legs, P):
    """M8 (H) / M9 (V) reservation rectangles of the clock tree wires (NDR_TRACKS tracks wide)."""
    out = []
    for x0, y0, x1, y1, *_ in segs:
        out += _leg_rects(x0, y0, x1, y1, P)
    for x0, y0, x1, y1 in leaf_legs:
        out += _leg_rects(x0, y0, x1, y1, P)
    return out


def _leg_rects(x0, y0, x1, y1, P):
    h = NDR_TRACKS * P.layers["M8"]["pitch_um"] / 2
    v = NDR_TRACKS * P.layers["M9"]["pitch_um"] / 2
    r = []
    if abs(x1 - x0) > 1e-6:          # horizontal run on M8 at y0
        a, b = sorted((x0, x1))
        r.append(("M8", a, y0 - h, b, y0 + h))
    if abs(y1 - y0) > 1e-6:          # vertical run on M9 at x1
        a, b = sorted((y0, y1))
        r.append(("M9", x1 - v, a, x1 + v, b))
    return r


# --------------------------------------------------------------------------------------------------------- GRT kit
def coarse_tracks(P, coarse):
    lines = []
    for n in ("M1", "M2", "M3"):
        lines.append(f"make_tracks {n} -x_offset {coarse / 2:g} -x_pitch {coarse:g} -y_offset {coarse / 2:g} "
                     f"-y_pitch {coarse:g}")
    for n in ("M4", "M5", "M6", "M7", "M8", "M9"):
        L = P.layers[n]
        lines.append(f"make_tracks {n} -x_offset {L['offset_um']:g} -x_pitch {L['pitch_um']:g} "
                     f"-y_offset {L['offset_um']:g} -y_pitch {L['pitch_um']:g}")
    return "\n".join(lines) + "\n"


def pg_stripes(P):
    """[(layer, x0, y0, x1, y1)] of the die PG stripes (die.pg.grid)."""
    out = []
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        if not L:
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = P.H if L["dir"] == "V" else P.W
        span = P.W if L["dir"] == "V" else P.H
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                out.append((g["layer"],) + ((a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)))
            pos += g["pitch_um"]
    return out


def ft_nets(P):
    """[(inst, slot, nbits_connected, in_bits, out_bits)] and the die route netlist connections per instance."""
    rows = []
    for n, p in sorted(P.parts.items()):
        t = P.types[p["type"]]
        for s in t.get("ft_slots", []) or []:
            rows.append((n, s["name"], int(s["width"]), int(s.get("stations", 1))))
    return rows


def route_netlist(P, type_bits):
    """die route netlist: every instance's ft slots S_i[b] -> S_o[b] joined (one net per bit), arst_n on the reset
    spine.  type_bits {type: {bus: nbits}} from the plan pins."""
    v = [f"module {sv(P.name)}_route (rst_n);", "  input rst_n;"]
    insts, nft = [], 0
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        t = P.types[tn]
        conns = [".arst_n(rst_n)"]
        for s in t.get("ft_slots", []) or []:
            bi, bo = type_bits[tn].get(s["name"] + "_i", 0), type_bits[tn].get(s["name"] + "_o", 0)
            k = min(bi, bo)
            if k <= 0:
                continue
            w = f"ft_{sv(n)}__{sv(s['name'])}"
            v.append(f"  wire [{k - 1}:0] {w};")
            conns.append(f".{s['name']}_i({w})")
            conns.append(f".{s['name']}_o({w})")
            nft += k
        insts.append(f"  {t['module']} {sv(n)} ({', '.join(conns)});")
    v += insts + ["endmodule"]
    return "\n".join(v) + "\n", nft


PLACE_PROC = ("proc ot_place {n x y o} { set b [ord::get_db_block]; set i [$b findInst $n]; $i setOrient $o; "
              "set d [[$b getTech] getDbUnitsPerMicron]; set X [expr {round($x*$d)}]; set Y [expr {round($y*$d)}]; "
              "$i setLocation $X $Y; set bb [$i getBBox]; "
              "$i setLocation [expr {2*$X - [$bb xMin]}] [expr {2*$Y - [$bb yMin]}]; set bb [$i getBBox]; "
              "if {[$bb xMin] != $X || [$bb yMin] != $Y} { puts \"OT_PLACE_MISMATCH $n [$bb xMin] [$bb yMin]\" }; "
              "$i setPlacementStatus FIRM }")


def grt_tcl(P, out, coarse, lefs, reserve, adjust):
    W, H = P.W, P.H
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die global route on abstracts, die {P.name}.",
         "set t0 [clock seconds]",
         f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"]
    t += [f"read_lef /work/abstracts/{x}" for x in lefs]
    t += [f"read_verilog /work/grt/route.v", f"link_design {sv(P.name)}_route",
          f"initialize_floorplan -die_area {{0 0 {W:g} {H:g}}} -core_area {{0 0 {W:g} {H:g}}} -site asap7sc7p5t",
          "source /work/grt/tracks.tcl", PLACE_PROC,
          "puts \"OT_T floorplan [expr {[clock seconds]-$t0}]\""]
    rp = {n: (x, y, L) for n, L, x, y in gen_phys.die_root_pins(P)}
    x, y, L = rp["rst_n"]
    t.append(f"place_pin -pin_name rst_n -layer {L} -location {{{x:.4f} {y:.4f}}} -pin_size {{0.32 0.04}}")
    for n, p in sorted(P.parts.items()):
        ox, oy = p["origin_um"]
        t.append(f"ot_place {sv(n)} {ox:g} {oy:g} {p.get('orient', 'R0')}")
    t.append("puts \"OT_T placed [expr {[clock seconds]-$t0}]\"")
    t.append("source /work/grt/obs.tcl")
    t.append("puts \"OT_T obs [expr {[clock seconds]-$t0}]\"")
    t.append("set_routing_layers -signal M4-M7")          # ruling 9.3: signals <= M7; M8/M9 = clock/reset/PG
    for L, a in adjust:
        t.append(f"set_global_routing_layer_adjustment {L} {a:g}")
    t += ["global_route -congestion_iterations 50 -allow_congestion -verbose "
          "-congestion_report_file /work/grt/congestion.rpt",
          "puts \"OT_T grt [expr {[clock seconds]-$t0}]\"",
          "if {[catch {grt::report_layer_wire_lengths} e]} { puts \"OT_NO_LAYER_WL $e\" }",
          "write_guides /work/grt/route.guide",
          "puts \"OT_T guides [expr {[clock seconds]-$t0}]\"",
          "puts OT_DONE"]
    obs = []
    for L, a, b, c, d in pg_stripes(P):
        obs.append(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}")
    for L, a, b, c, d in reserve:
        obs.append(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}")
    (Path(out) / "obs.tcl").write_text("\n".join(obs) + "\n")
    return "\n".join(t) + "\n"


# --------------------------------------------------------------------------------------------------------- PSM kit
def part_power(P, plan_dir, density_w_mm2):
    """{part: W}: uniform areal density (technology.json clock energy 8.5e-11 J/mm2/cycle at 1.2 GHz = 0.102 W/mm2
    ungated clock, + logic / leakage; the density is a parameter of the run: IR scales linearly)."""
    return {n: round(density_w_mm2 * P.types[p["type"]]["outline_um"][0] * P.types[p["type"]]["outline_um"][1] * 1e-6, 6)
            for n, p in P.parts.items()}


def io_windows(P, plan_dir):
    io = P.die.get("io")
    if not io:
        f = Path(plan_dir) / "die_io.json"
        io = json.loads(f.read_text()) if f.is_file() else []
    return io


def psm_tcl(P, lefs, power, bumps):
    W, H = P.W, P.H
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die PDN + PDNSim on abstracts, die {P.name}.",
         "set t0 [clock seconds]", f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"]
    t += [f"read_lef /work/abstracts/{x}" for x in lefs]
    t += [f"foreach f [glob {PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
          "read_verilog /work/psm/psm.v", f"link_design {sv(P.name)}_psm",
          f"initialize_floorplan -die_area {{0 0 {W:g} {H:g}}} -core_area {{0 0 {W:g} {H:g}}} -site asap7sc7p5t",
          "source /work/grt/tracks.tcl", PLACE_PROC]
    for n, p in sorted(P.parts.items()):
        ox, oy = p["origin_um"]
        t.append(f"ot_place {sv(n)} {ox:g} {oy:g} {p.get('orient', 'R0')}")
    t += ["puts \"OT_T placed [expr {[clock seconds]-$t0}]\"", "source /work/psm/pdn.tcl", "pdngen",
          "puts \"OT_T pdngen [expr {[clock seconds]-$t0}]\"",
          "write_db /work/psm/pdn_grid.odb",
          "source /work/psm/bumps.tcl",
          "puts \"OT_T bumps [expr {[clock seconds]-$t0}]\"",
          "write_db /work/psm/pdn_bumps.odb",
          "source /work/psm/power.tcl",
          f"source {PLAT}/setRC.tcl",
          "set pg_failed 0",
          "foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} e]} { incr pg_failed; puts \"OT_PG_CHECK_FAIL $n $e\" } "
          "else { puts \"OT_PG_CHECK_OK $n\" } }",
          "puts \"OT_T check [expr {[clock seconds]-$t0}]\"",
          "if {$pg_failed} { error \"power-grid connectivity failed\" }",
          "if {[catch {analyze_power_grid -net VDD -error_file /work/psm/psm_VDD.rpt "
          "-voltage_file /work/psm/ir_VDD.csv} e]} { puts \"OT_PSM_FAIL $e\"; error $e } else { puts OT_PSM_OK }",
          "puts \"OT_T psm [expr {[clock seconds]-$t0}]\"",
          "puts OT_DONE"]
    return "\n".join(t) + "\n"


def psm_pdn_tcl(P):
    g = P.die.get("pg", {}).get("grid")
    lines = ["add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power",
             "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground",
             "global_connect", "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}",
             "define_pdn_grid -name {top} -voltage_domains {CORE}"]
    for s in g:
        lines.append(f"add_pdn_stripe -grid {{top}} -layer {{{s['layer']}}} -width {{{s['width_um']:g}}} "
                     f"-pitch {{{s['pitch_um']:g}}} -offset {{{s['offset_um']:g}}} -spacing "
                     f"{{{s['pitch_um'] / 2 - s['width_um']:g}}}")
    ls = [s["layer"] for s in g]
    for a, b in zip(ls, ls[1:]):
        lines.append(f"add_pdn_connect -grid {{top}} -layers {{{a} {b}}}")
    lines += ["define_pdn_grid -name {parts} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} "
              "-halo {0 0 0 0} -default", f"add_pdn_connect -grid {{parts}} -layers {{M7 {ls[0]}}}"]
    return "\n".join(lines) + "\n"


def bump_grid(P, io, pitch=150.0, size=60.0):
    """C4 power bumps: a regular grid at `pitch` (alternating VDD / VSS by row+col parity) inside the die, minus the
    seal ring / corner keep-out channels and the die IO windows (signal bumps).  -> [(net, x, y)]"""
    keep = [c["rect_um"] for c in P.die.get("channels", [])] + [w["rect_um"] for w in io]
    out = []
    nx, ny = int(P.W // pitch), int(P.H // pitch)
    x0 = (P.W - (nx - 1) * pitch) / 2
    y0 = (P.H - (ny - 1) * pitch) / 2
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * pitch, y0 + j * pitch
            if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in keep):
                continue
            out.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 3), round(y, 3)))
    return out


def bumps_tcl(P, bumps, size=4.0):
    """Attach each source to actual M9 metal of its own net after pdngen.

    Stripe origins depend on the floorplan core origin and pdngen net phase.
    Computing them from the plan offset produced isolated voltage-source pins.
    """
    t = ["set block [ord::get_db_block]", "set m9 [[ord::get_db_tech] findLayer M9]",
         "set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set bump_shapes {}", "set bump_x_cache {}",
         "foreach net_name {VDD VSS} {",
         "  set shapes {}",
         "  foreach wire [[$block findNet $net_name] getSWires] {",
         "    foreach shape [$wire getWires] {",
         "      if {[$shape isVia] || [$shape getTechLayer] ne $m9} continue",
         "      lappend shapes [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]",
         "    }",
         "  }",
         "  if {![llength $shapes]} { error \"no actual M9 metal for $net_name voltage sources\" }",
         "  dict set bump_shapes $net_name $shapes",
         "}"]
    for k, (net, x, y) in enumerate(bumps):
        t += [f"set bx [expr {{{x:g}*$bump_dbu}}]; set by [expr {{{y:g}*$bump_dbu}}]",
              f"set cache_key [list {net} $bx]",
              "if {![dict exists $bump_x_cache $cache_key]} {",
              "  set nearest {}; set x_distance 1e30",
              f"  foreach rect [dict get $bump_shapes {net}] {{",
              "    lassign $rect x0 y0 x1 y1",
              "    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]",
              "    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }",
              "  }",
              "  dict set bump_x_cache $cache_key $nearest",
              "}",
              "set best {}; set best_distance 1e30",
              "foreach rect [dict get $bump_x_cache $cache_key] {",
              "  lassign $rect x0 y0 x1 y1",
              "  set cx [expr {($x0+$x1)/2.0}]",
              f"  set half [expr {{min({size:g}*$bump_dbu/2.0,($y1-$y0)/2.0)}}]",
              "  set cy [expr {max($y0+$half,min($y1-$half,$by))}]",
              "  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]",
              "  if {$distance < $best_distance} {",
              "    set best_distance $distance",
              "    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]",
              "  }",
              "}",
              f"set bt [odb::dbBTerm_create [$block findNet {net}] {net}_b{k}]; $bt setIoType INOUT; "
              f"$bt setSigType {'POWER' if net == 'VDD' else 'GROUND'}; set bp [odb::dbBPin_create $bt]",
              "odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM"]
    t.append(f'puts "OT_BUMPS actual_m9_sources {len(bumps)} cached_columns [dict size $bump_x_cache]"')
    return "\n".join(t) + "\n"


# --------------------------------------------------------------------------------------------------------- STA kit
def standin_netlist(P, tn, hold_contract=True, clock_contract=True):
    """budget stand-in of a partition type for die_sta.py: one face flop per pin bit next to its pin, clocked from the
    nearest plan clock tap (no internal logic: the partition's internal paths are its own G3 closure).  hold_contract:
    every input bit reaches its face flop through the boundary-hold contract cell (die_sta.bhold_cell(tol)): the port
    -> D minimum a signed kit guarantees under the signoff.py hold_ff overlay (input min -insertion_tol).
    clock_contract: every clock tap port drives ONE clock-latency contract cell (die_sta.clat_cell: input cap = the
    kit CTS root load the die tree is balanced against, constant delay = the type's bound TT / FF pin-register
    insertion, gen_phys.insertion_binding) and the face flops hang on its output, never on the port; face flops take
    the nearest TYPE tap (pin registers sit on the type grid taps), early core taps (clk_c<k>) drive only their
    contract cell at the core's insertion (the hard core's own tree).  Without it (legacy) every face flop's CLK
    loads the port directly and core taps clock face flops too."""
    t = P.types[tn]
    pins = gen_phys.type_pins(P, tn)
    bits = defaultdict(int)
    for bus, bit, *_ in pins:
        bits[bus] = max(bits[bus], bit + 1)
    ctaps = gen_phys.clock_pins(P, tn)
    cores = gen_phys.core_tap_pins(P, tn)
    taps = ctaps + cores
    tapn = [n for n, _, _ in taps]
    dirs = {b["name"]: b["dir"] for b in t.get("buses", [])}
    for sl in t.get("ft_slots", []) or []:
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "in", "out"
    flop_taps = ctaps if clock_contract and ctaps else taps

    def near(x, y):
        return min(flop_taps, key=lambda q: abs(q[1] - x) + abs(q[2] - y))[0]
    ports = [f"  input {n};" for n in tapn] + ["  input arst_n;"]
    for b in sorted(bits):
        ports.append(f"  {'input' if dirs.get(b) == 'in' else 'output'} [{bits[b] - 1}:0] {b};")
    ckn, ckcells, ckwires = {n: n for n in tapn}, [], []
    if clock_contract:
        ib = gen_phys.insertion_binding(P, tn)
        cins = {r[0]: r[4] for r in gen_phys.core_tap_rows(P, tn)} if cores else {}
        for j, n in enumerate(tapn):
            if n in cins:
                tt = cins[n]
                lat = die_sta.clat_cell(tt, round(gen_phys.FF_TT_INSERTION_RATIO * tt, 1))
            else:
                lat = die_sta.clat_cell(ib["tt"], ib["ff"])
            ckn[n] = f"ck_{n}"
            ckwires.append(f"  wire ck_{n};")
            ckcells.append(f"  {lat} c{j} (.A({n}), .Y(ck_{n}));")
    cells = []
    k = 0
    bh = die_sta.bhold_cell(P.clock["insertion_tol_ps"])
    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        ck = ckn[near(x, y)]
        if dirs.get(bus) == "in" and hold_contract:
            cells.append(f"  {bh} h{k} (.A({bus}[{bit}]), .Y(d{k}));\n  {FLOP} f{k} (.CLK({ck}), .D(d{k}), .QN(q{k}));")
        elif dirs.get(bus) == "in":
            cells.append(f"  {FLOP} f{k} (.CLK({ck}), .D({bus}[{bit}]), .QN(q{k}));")
        else:
            cells.append(f"  {FLOP} f{k} (.CLK({ck}), .D(1'b0), .QN({bus}[{bit}]));")
        k += 1
    names = tapn + ["arst_n"] + sorted(bits)
    v = [f"module {t['module']} ({', '.join(names)});"] + ports + ckwires
    v += [f"  wire q{i};" for i in range(k) if f".QN(q{i})" in cells[i]]
    v += [f"  wire d{i};" for i in range(k) if f".Y(d{i})" in cells[i]]
    v += ckcells + cells + ["endmodule"]
    return "\n".join(v) + "\n", k


_STANDIN_IN = re.compile(r"^(\s*)(" + re.escape(FLOP) + r") f(\d+) \(\.CLK\(([^)]*)\), \.D\(([^)']+)\), \.QN\(q\3\)\);\s*$")


def standin_add_contract(text, tol_ps):
    """an existing bare stand-in netlist (standin_netlist without hold_contract) -> the contract form: every
    `FLOP fK (.CLK(c), .D(<port bit>), .QN(qK));` gets the OT_BHOLD cell between the port bit and D.  Returns
    (text, bits).  Refuses a netlist that is not a pure stand-in (any other cell type) or already has the cell."""
    bh = die_sta.bhold_cell(tol_ps)
    out, n, wires = [], 0, []
    for ln in text.splitlines():
        if "OT_BHOLD_" in ln:
            raise ValueError("stand-in already carries the boundary-hold contract")
        m = _STANDIN_IN.match(ln)
        if m:
            ind, cell, k, ck, d = m.groups()
            out += [f"{ind}{bh} h{k} (.A({d}), .Y(d{k}));", f"{ind}{cell} f{k} (.CLK({ck}), .D(d{k}), .QN(q{k}));"]
            wires.append(f"  wire d{k};")
            n += 1
            continue
        s = ln.strip()
        if s and not re.match(r"(module|input|output|wire|endmodule|\)|//)", s) and not s.startswith(FLOP):
            raise ValueError(f"not a budget stand-in netlist line: {s[:120]}")
        out.append(ln)
    if wires:
        i = next(j for j, ln in enumerate(out) if ln.strip().startswith(FLOP) or ln.strip().startswith(bh))
        out[i:i] = wires
    return "\n".join(out) + "\n", n


# ------------------------------------------------------------------------------------------------------------- kit
def run_sh(step, mem, cpus, cmd):
    return f"""#!/bin/bash
# GENERATED by tools/die_plan/die_trial.py: {step} (heavy: launch through ot-run --mem {mem} --threads {cpus})
D=$(cd $(dirname $0) && pwd)
IMAGE=${{OT_ORFS_IMAGE:-{IMAGE}}}
DK=docker; docker info >/dev/null 2>&1 || DK="sudo docker"
echo "image $IMAGE $($DK image inspect --format '{{{{.Id}}}}' $IMAGE) host $(hostname) start $(date -Is)" > $D/{step}.image.txt
$DK run --rm --name dtrial-{step}-$$ --cpus=${{CPUS:-{cpus}}} --memory=${{MEM:-{mem}}}g --memory-swap=${{MEM:-{mem}}}g -v $D:/work -w /work \\
  -e HUID=$(id -u) -e HGID=$(id -g) $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {cmd}; rc=\\$?; chown -R \\$HUID:\\$HGID /work; exit \\$rc"
rc=$?
echo "end $(date -Is) exit $rc" >> $D/{step}.image.txt
exit $rc
"""


def write_kit(plan_path, out, views=None, leaf_um=600.0, rep_um=450.0, coarse=0.72, density=0.15):
    raw = S.load(plan_path)
    P = S.Plan(raw)
    plan_dir = Path(plan_path).parent
    out = Path(out)
    for d in ("abstracts", "grt", "clock", "psm", "sta/parts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    meta = dict(plan=str(plan_path), plan_sha256=S.sha256_file(plan_path) if hasattr(S, "sha256_file") else None,
                die=P.name, outline_um=[P.W, P.H], area_mm2=round(P.W * P.H * 1e-6, 2), parts=len(P.parts),
                types=len(P.types), ports=len(P.ports), lanes=len(raw.get("lanes", [])), image=IMAGE)
    import hashlib
    meta["plan_sha256"] = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()
    # abstracts
    lefs, ab = [], {}
    type_bits = {}
    for tn, t in sorted(P.types.items()):
        v = Path(views) / tn / f"{t['module']}.lef" if views else None
        if v and v.is_file():
            (out / "abstracts" / v.name).write_text(v.read_text())
            ab[tn] = dict(source="closed view", path=str(v))
        else:
            txt, st = abstract_lef(P, tn)
            (out / "abstracts" / f"{t['module']}.lef").write_text(txt)
            ab[tn] = dict(source="plan abstract", **st)
        lefs.append(f"{t['module']}.lef")
        bits = defaultdict(int)
        for bus, bit, *_ in gen_phys.type_pins(P, tn):
            bits[bus] = max(bits[bus], bit + 1)
        type_bits[tn] = dict(bits)
    meta["abstracts"] = ab
    meta["closed_views"] = sum(1 for a in ab.values() if a["source"] == "closed view")
    meta["hard_cores"] = sum(len(P.types[p["type"]].get("hard_cores", []) or []) for p in P.parts.values())
    meta["hard_cores_with_view"] = sum(ab[p["type"]].get("cores_with_view", 0) for p in P.parts.values())
    # die IO
    io = io_windows(P, plan_dir)
    meta["die_io"] = [dict(name=w["name"], part=w.get("part"), iface=w.get("iface"), rect_um=w["rect_um"],
                           sites=w.get("sites"), signals=w.get("signals"), host=w.get("host", False)) for w in io]
    # clock
    nodes, segs, leaf_legs, cm = clock_kit(P, out / "clock", leaf_um, rep_um)
    (out / "clock" / "make_tracks.tcl").write_text(gen_phys.make_tracks_tcl(P))
    meta["clock_tree"] = cm
    reserve = reserve_rects(segs, leaf_legs, P)
    # grt
    rv, nft = route_netlist(P, type_bits)
    (out / "grt" / "route.v").write_text(rv)
    (out / "grt" / "tracks.tcl").write_text(coarse_tracks(P, coarse))
    ftf = sorted({t.get("ft_track_frac", 0.25) for t in P.types.values()})
    ca = P.layer_budget.get("cut_avail", {"M8": 0.6, "M9": 0.6})
    adjust = [(L, round(1 - ftf[0], 3)) for L in ("M4", "M5", "M6", "M7")] + \
             [(L, round(1 - ca.get(L, 0.6), 3)) for L in ("M8", "M9")]
    (out / "grt" / "grt.tcl").write_text(grt_tcl(P, out / "grt", coarse, lefs, reserve, adjust))
    meta["grt"] = dict(ft_bits=nft, ft_slot_instances=len(ft_nets(P)), reset_taps=len(P.parts),
                       adjust=dict(adjust), coarse_m123_um=coarse, clock_reserve_rects=len(reserve),
                       pg_stripes=len(pg_stripes(P)))
    seam_bits = 0
    chan = 0
    for pid, pr in P.ports.items():
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        seam_bits += S.port_pins_count(pr)
        chan += 1 if P.channel_of(pid) else 0
    meta["grt"]["abutted_seam_bits"] = seam_bits
    meta["grt"]["channel_ports"] = chan
    (out / "run_grt.sh").write_text(run_sh("grt", 256, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                         "/work/grt/grt.tcl > /work/grt/grt.log 2>&1; echo EXIT \\$? >> /work/grt/grt.log"))
    # clock runs (3 corners)
    ck = "; ".join(f"CORNER={c} LIBDIR={PLAT}/lib/NLDM /usr/bin/time -v openroad -no_init -exit /work/clock/ctree.tcl "
                   f"> /work/clock/ctree_{c}.log 2>&1" for c in ("TT", "FF"))
    (out / "run_clock.sh").write_text(run_sh("clock", 32, 4, ck).replace("-v $D:/work", "-v $D:/work"))
    # psm
    power = part_power(P, plan_dir, density)
    pv = [f"module {sv(P.name)}_psm ();"] + [f"  {P.types[p['type']]['module']} {sv(n)} ();" for n, p in sorted(P.parts.items())] + ["endmodule"]
    (out / "psm" / "psm.v").write_text("\n".join(pv) + "\n")
    (out / "psm" / "pdn.tcl").write_text(psm_pdn_tcl(P))
    bumps = bump_grid(P, io)
    (out / "psm" / "bumps.tcl").write_text(bumps_tcl(P, bumps))
    (out / "psm" / "power.tcl").write_text("\n".join(f"set_pdnsim_inst_power -inst {sv(n)} -power {w:.6f}"
                                                     for n, w in sorted(power.items())) + "\n")
    (out / "psm" / "psm.tcl").write_text(psm_tcl(P, lefs, power, bumps))
    (out / "psm" / "power.json").write_text(json.dumps(dict(density_w_mm2=density, total_w=round(sum(power.values()), 3),
                                                            parts=power), indent=0) + "\n")
    meta["psm"] = dict(density_w_mm2=density, total_w=round(sum(power.values()), 2), bumps=len(bumps),
                       bumps_vdd=sum(1 for b in bumps if b[0] == "VDD"), bump_pitch_um=150.0,
                       io_windows=len(io), pg=P.die.get("pg", {}).get("grid"))
    (out / "run_psm.sh").write_text(run_sh("psm", 256, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                         "/work/psm/psm.tcl > /work/psm/psm.log 2>&1"))
    # sta stand-ins
    nff = 0
    for tn, t in sorted(P.types.items()):
        d = out / "sta" / "parts" / t["module"]
        d.mkdir(parents=True, exist_ok=True)
        v, k = standin_netlist(P, tn)
        (d / "6_final.v").write_text(v)
        nff += k * sum(1 for p in P.parts.values() if p["type"] == tn)
    v = gen_rtl.die_top(P, gen_rtl.bus_epochs(P), {})
    plain = "\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", ln) for ln in v.splitlines() if not ln.startswith("`"))
    (out / "sta" / "die_top.v").write_text(plain + "\n")
    meta["sta"] = dict(standin_flops=nff, seam_bits=seam_bits)
    for x in ("run_grt.sh", "run_clock.sh", "run_psm.sh"):
        os.chmod(out / x, 0o755)
    (out / "kit.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


# ---------------------------------------------------------------------------------------------------------- reports
def parse_time_v(text):
    r = {}
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if m:
        r["peak_rss_gb"] = round(int(m.group(1)) / 1048576.0, 2)
    m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", text)
    if m:
        s = 0.0
        for part in m.group(1).split(":"):
            s = s * 60 + float(part)
        r["wall_s"] = round(s, 1)
    return r


def grt_report(d, P):
    import g2
    log = (d / "grt" / "grt.log").read_text(errors="replace") if (d / "grt" / "grt.log").is_file() else ""
    r = g2.parse_grt(log)
    r.update(parse_time_v(log))
    r["marks_s"] = {k: int(v) for k, v in re.findall(r"OT_T (\w+) (\d+)", log)}
    m = re.findall(r"GRT-0\d+\]\s*.*?(\d+)\s*x\s*(\d+)", log)
    gc = re.findall(r"\[INFO GRT-0\d+\] (?:Number of )?(?:gcells|GCells)[^\n]*", log)
    r["grid_lines"] = gc[:4]
    # worst windows from the congestion report (KLayout marker DB): boxes + overflow text
    rpt = d / "grt" / "congestion.rpt"
    wins = []
    if rpt.is_file():
        txt = rpt.read_text(errors="replace")
        for m in re.finditer(r"box: \(([-\d.]+),([-\d.]+);([-\d.]+),([-\d.]+)\)(.*?)</", txt, re.S):
            wins.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)[:200]))
        r["congestion_items"] = len(wins)
        cnt = defaultdict(int)
        for x0, y0, x1, y1, _ in wins:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            for n in P.parts:
                a, b, c, e = P.rect(n)
                if a <= cx < c and b <= cy < e:
                    cnt[n] += 1
                    break
        r["congestion_by_part"] = dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:30])
        r["congestion_sample"] = [dict(box=w[:4], text=re.sub(r"\s+", " ", w[4]).strip()) for w in wins[:20]]
    r["exit"] = (re.findall(r"EXIT (\d+)", log) or [None])[-1]
    return r


def clock_report(d, P):
    tree = json.loads((d / "clock" / "tree.json").read_text())
    nodes = {int(k): v for k, v in tree["nodes"].items()}
    node_buf = {int(k): v for k, v in tree["node_buf"].items()}
    buf_node = {v: k for k, v in node_buf.items()}
    res = dict(meta=tree["meta"], corners={})
    taps = tree["taps"]
    tap_by = {(t["part"], t["tap"]): t for t in taps}
    part_taps = defaultdict(list)
    for t in taps:
        part_taps[t["part"]].append(t)

    def anc(i):
        out = []
        while i is not None:
            out.append(i)
            i = nodes[i]["parent"]
        return out
    # seam pairs: every abutted port -> the launch tap (src part) and capture tap (dst part) nearest the window centre
    pairs = []
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (a, b):
            continue
        pins = P.port_pins(pid)
        cs = [c for _, _, c in pins]
        cmid = (min(cs) + max(cs)) / 2
        ra = P.rect(a)
        f = pr["face"]
        if f in "EW":
            pt = ((ra[2] if f == "E" else ra[0]), cmid)
        else:
            pt = (cmid, (ra[3] if f == "N" else ra[1]))
        ta = min(part_taps[a], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
        tb = min(part_taps[b], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
        pairs.append((pid, ta, tb))
    for corner in ("SS", "TT", "FF"):
        f = d / "clock" / f"arr_{corner}.txt"
        if not f.is_file():
            continue
        tarr, narr = {}, {}
        for ln in f.read_text().splitlines():
            x = ln.split()
            if len(x) < 4:
                continue
            try:
                vmax, vmin = float(x[2]), float(x[3])
            except ValueError:
                continue
            if x[0] == "T":
                tarr[x[1]] = vmax          # max arrival (= period - slack_max)
            elif x[0] == "N":
                narr[buf_node.get(x[1])] = vmax
        if not tarr:
            continue
        ins = sorted(tarr.values())
        cr = dict(insertion_max_ps=round(ins[-1], 1), insertion_min_ps=round(ins[0], 1),
                  global_skew_ps=round(ins[-1] - ins[0], 1), taps=len(ins))
        # per-partition tap spread
        sp = []
        for n, tl in part_taps.items():
            v = [tarr[t["port"]] for t in tl if t["port"] in tarr]
            if v:
                sp.append(max(v) - min(v))
        cr["part_tap_spread_ps_max"] = round(max(sp), 1) if sp else None
        rows = []
        for pid, ta, tb in pairs:
            if ta["port"] not in tarr or tb["port"] not in tarr:
                continue
            A, B = anc(ta["node"]), anc(tb["node"])
            sb = set(B)
            lca = next(i for i in A if i in sb)
            la = narr.get(lca, 0.0)
            # node arrival is at the node buffer OUTPUT; taps below it
            ua, ub = tarr[ta["port"]] - la, tarr[tb["port"]] - la
            nom = tarr[tb["port"]] - tarr[ta["port"]]
            row = dict(port=pid, launch=f"{ta['part']}/{ta['tap']}", capture=f"{tb['part']}/{tb['tap']}",
                       nominal_ps=round(nom, 1), uncommon_launch_ps=round(ua, 1), uncommon_capture_ps=round(ub, 1),
                       lca_level=nodes[lca]["level"])
            for k in OCV:
                row[f"ocv{int(k * 100)}_ps"] = round(max(abs(ub * (1 - k) - ua * (1 + k)), abs(ub * (1 + k) - ua * (1 - k))), 1)
            rows.append(row)
        if rows:
            cr["seam_pairs"] = len(rows)
            cr["seam_nominal_abs_max_ps"] = max(abs(r["nominal_ps"]) for r in rows)
            for k in OCV:
                key = f"ocv{int(k * 100)}_ps"
                v = sorted(r[key] for r in rows)
                cr[f"seam_{key}_max"] = v[-1]
                cr[f"seam_{key}_p90"] = v[int(0.9 * (len(v) - 1))]
                cr[f"seam_{key}_over80"] = sum(1 for x in v if x > 80.0)
            cr["all_seams"] = rows
            cr["worst_seams"] = sorted(rows, key=lambda r: -r[f"ocv{int(OCV[-1] * 100)}_ps"])[:15]
            cr["worst_nominal"] = sorted(rows, key=lambda r: -abs(r["nominal_ps"]))[:10]
        log = d / "clock" / f"ctree_{corner}.log"
        if log.is_file():
            cr.update(parse_time_v(log.read_text(errors="replace")))
        res["corners"][corner] = cr
        # die_sta spine file: per tap offset = arrival - min arrival
        mn = ins[0]
        br = dict(model="trial-htree", corner=corner, parts={})
        for t in taps:
            if t["port"] in tarr:
                br["parts"].setdefault(t["part"], dict(taps={}))["taps"][t["tap"]] = dict(
                    offset_ps=round(tarr[t["port"]] - mn, 2), arrival_ps=round(tarr[t["port"]], 2))
        (d / "sta" / f"spine_{corner}.json").write_text(json.dumps(br) + "\n")
    return res


def psm_report(d):
    log = d / "psm" / "psm.log"
    r = {}
    if not log.is_file():
        return r
    txt = log.read_text(errors="replace")
    r.update(parse_time_v(txt))
    r["marks_s"] = {k: int(v) for k, v in re.findall(r"OT_T (\w+) (\d+)", txt)}
    for k, pat in (("worst_ir_drop_mv", r"Worstcase IR drop\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("avg_ir_drop_mv", r"Average IR drop\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("worst_voltage", r"Worstcase voltage\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("avg_voltage", r"Average voltage\s*:\s*([\d.e+-]+)\s*(\w*V)")):
        m = re.findall(pat, txt)
        if m:
            v, u = m[-1]
            f = dict(V=1.0, mV=1e-3, uV=1e-6).get(u, 1.0)
            r[k] = round(float(v) * f * (1e3 if k.endswith("_mv") else 1.0), 3)
    r["status"] = "OK" if "OT_PSM_OK" in txt else ("FAIL" if "OT_PSM_FAIL" in txt else "NOT RUN")
    r["pg_check"] = re.findall(r"OT_PG_CHECK_(OK|FAIL) (\w+)", txt)
    r["errors"] = sorted(set(re.findall(r"\[ERROR ([A-Z]+-\d+)\]", txt)))
    return r


def cmd_report(a):
    d = Path(a.dir)
    kit = json.loads((d / "kit.json").read_text())
    P = S.Plan(S.load(kit["plan"] if Path(kit["plan"]).is_file() else a.plan))
    res = dict(kit=kit)
    if (d / "grt" / "grt.log").is_file():
        res["grt"] = grt_report(d, P)
    if (d / "clock" / "tree.json").is_file():
        res["clock"] = clock_report(d, P)
    res["psm"] = psm_report(d)
    for c in ("SS", "FF", "TT"):
        f = d / "sta" / f"run_{c}" / "die_sta.json"
        if f.is_file():
            res.setdefault("sta", {})[c] = json.loads(f.read_text())
    (d / "trial.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


# ---------------------------------------------------------------------------------------------------------- renders
def _part_patches(ax, P, alpha=0.25, edge="0.6", label=False):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    types = sorted(P.types)
    cmap = plt.get_cmap("tab20")
    col = {t: cmap(i % 20) for i, t in enumerate(types)}
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, facecolor=col[p["type"]],
                               alpha=alpha, edgecolor=edge, lw=0.3))
        if label:
            ax.text((x0 + x1) / 2000, (y0 + y1) / 2000, n, fontsize=2.5, ha="center", va="center")


def core_rects_die(P):
    """[(layer_top, x0, y0, x1, y1)] every planned hard core in die coordinates."""
    out = []
    for n, p in P.parts.items():
        for x0, y0, x1, y1, tl, _, _ in core_obs(P.types[p["type"]]):
            a = P.to_die(n, (x0, y0))
            b = P.to_die(n, (x1, y1))
            out.append((tl, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    return out


def guide_maps(P, guide, win_um=27.0, adjust=None):
    """per-window routing utilisation from the GRT guides: demand (track x gcell) / capacity (tracks across a gcell
    x (1 - layer adjustment) minus planned hard-core OBS on M4.. and die PG on M8/M9).  -> {layer: 2D array}, meta"""
    import numpy as np
    dbu = 1000.0
    nx, ny = int(math.ceil(P.W / win_um)), int(math.ceil(P.H / win_um))
    dem = {L: np.zeros((ny, nx)) for L in ("M4", "M5", "M6", "M7", "M8", "M9")}
    gc = None
    nets = 0
    with open(guide) as f:
        for ln in f:
            x = ln.split()
            if len(x) == 5:
                L = x[4]
                if L not in dem:
                    continue
                x0, y0, x1, y1 = (int(v) / dbu for v in x[:4])
                if gc is None:
                    gc = min(x1 - x0, y1 - y0)
                hdir = P.layers[L]["dir"] == "H"
                if hdir:
                    a, b, c = x0, x1, (y0 + y1) / 2
                    if b - a <= gc * 1.01:
                        continue        # via-only box (pin access)
                    r = min(int(c / win_um), ny - 1)
                    i0, i1 = int(a / win_um), min(int((b - 1e-6) / win_um), nx - 1)
                    for i in range(i0, i1 + 1):
                        ov = min(b, (i + 1) * win_um) - max(a, i * win_um)
                        dem[L][r, i] += ov / gc
                else:
                    a, b, c = y0, y1, (x0 + x1) / 2
                    if b - a <= gc * 1.01:
                        continue
                    col = min(int(c / win_um), nx - 1)
                    i0, i1 = int(a / win_um), min(int((b - 1e-6) / win_um), ny - 1)
                    for i in range(i0, i1 + 1):
                        ov = min(b, (i + 1) * win_um) - max(a, i * win_um)
                        dem[L][i, col] += ov / gc
            elif len(x) == 1 and x[0] not in "()":
                nets += 1
    gc = gc or 2.7
    gpw = (win_um / gc) ** 2                       # gcells per window
    block = {L: np.zeros((ny, nx)) for L in dem}
    for tl, x0, y0, x1, y1 in core_rects_die(P):
        for L in dem:
            if int(L[1:]) > int(tl[1:]):
                continue
            i0, i1 = int(x0 / win_um), min(int(x1 / win_um), nx - 1)
            j0, j1 = int(y0 / win_um), min(int(y1 / win_um), ny - 1)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    ov = max(0.0, min(x1, (i + 1) * win_um) - max(x0, i * win_um)) * \
                         max(0.0, min(y1, (j + 1) * win_um) - max(y0, j * win_um))
                    block[L][j, i] += ov / win_um ** 2
    util = {}
    pgf = 2 * 0.48 / 8.64
    for L in dem:
        tr = gc / P.layers[L]["pitch_um"] * (1 - (adjust or {}).get(L, 0.0))
        free = np.clip(1 - block[L], 0, 1) * (1 - (pgf if L in ("M8", "M9") else 0.0))
        cap = tr * gpw * free
        with np.errstate(divide="ignore", invalid="ignore"):
            # windows mostly covered by hard-core OBS (< 25 % free) are left out: their gcell-edge demand vs a
            # sliver of capacity is a window-quantisation artefact (GRT itself routes per gcell)
            u = np.where(free >= 0.25, dem[L] / np.maximum(cap, 1e-9), 0.0)
        util[L] = u
    return util, dict(win_um=win_um, gcell_um=gc, nets=nets, nx=nx, ny=ny)


def render_all(d, P, plan_path):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection
    d = Path(d)
    rd = d / "render"
    rd.mkdir(exist_ok=True)
    kit = json.loads((d / "kit.json").read_text())
    W, H = P.W / 1000, P.H / 1000
    figw = 16
    figh = figw * H / W + 1.2
    out = {}
    # (1) floorplan: types, hard cores, die IO windows, ft lane bundles (in-window -> out-window, width ~ bits)
    fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
    _part_patches(ax, P, label=True)
    for tl, x0, y0, x1, y1 in core_rects_die(P):
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, facecolor="0.35",
                               edgecolor="none", alpha=0.6))
    for w in kit.get("die_io", []):
        x0, y0, x1, y1 = w["rect_um"]
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, fill=False,
                               edgecolor="red" if w.get("host") else "magenta", lw=1.2, ls="--"))
        ax.text(x0 / 1000, y1 / 1000, w["name"].replace("io_", "").replace("_u_phy", ""), fontsize=4, color="m")
    segs, lw = [], []
    for n, p in P.parts.items():
        for s in P.types[p["type"]].get("ft_slots", []) or []:
            pins = [q for q in gen_phys.type_pins(P, p["type"]) if q[0] in (s["name"] + "_i", s["name"] + "_o")]
            if not pins:
                continue
            ins = [P.to_die(n, (q[3], q[4])) for q in pins if q[0].endswith("_i")]
            ous = [P.to_die(n, (q[3], q[4])) for q in pins if q[0].endswith("_o")]
            if ins and ous:
                a = (sum(v[0] for v in ins) / len(ins) / 1000, sum(v[1] for v in ins) / len(ins) / 1000)
                b = (sum(v[0] for v in ous) / len(ous) / 1000, sum(v[1] for v in ous) / len(ous) / 1000)
                segs.append([a, b])
                lw.append(0.3 + 2.5 * min(1.0, s["width"] / 2000))
    ax.add_collection(LineCollection(segs, linewidths=lw, colors="tab:blue", alpha=0.7))
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{P.name} trial die: {len(P.parts)} partitions / {len(P.types)} types, hard cores (grey), "
                 f"die IO windows (magenta, red = host), ft slot bundles (blue, width ~ bits)  [mm]", fontsize=9)
    fig.tight_layout(); fig.savefig(rd / "floorplan_ft.png"); plt.close(fig)
    out["floorplan_ft"] = str(rd / "floorplan_ft.png")
    # (2) clock tree: legs by level, taps by SS arrival, seam pairs over 80 ps (3% OCV) in red
    tf = d / "clock" / "tree.json"
    if tf.is_file():
        tree = json.loads(tf.read_text())
        nodes = {int(k): v for k, v in tree["nodes"].items()}
        fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
        _part_patches(ax, P, alpha=0.12)
        segs, cols = [], []
        cm = plt.get_cmap("viridis")
        mx = max(n["level"] for n in nodes.values()) or 1
        for i, n in nodes.items():
            if n["parent"] is not None:
                p = nodes[n["parent"]]
                segs.append([(p["x"] / 1000, p["y"] / 1000), (n["x"] / 1000, n["y"] / 1000)])
                cols.append(cm(n["level"] / mx))
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.8))
        arr = {}
        af = d / "clock" / "arr_SS.txt"
        if af.is_file():
            for ln in af.read_text().splitlines():
                x = ln.split()
                if x and x[0] == "T":
                    arr[x[1]] = float(x[2])
        xs = [t["xy"][0] / 1000 for t in tree["taps"]]
        ys = [t["xy"][1] / 1000 for t in tree["taps"]]
        cs = [arr.get(t["port"], float("nan")) for t in tree["taps"]]
        sc = ax.scatter(xs, ys, c=cs, s=3, cmap="plasma")
        fig.colorbar(sc, ax=ax, fraction=0.025, label="SS tap arrival (ps)")
        cr = None
        tj = d / "trial.json"
        if tj.is_file():
            cr = json.loads(tj.read_text()).get("clock", {}).get("corners", {}).get("SS")
        if cr is None:
            try:
                cr = clock_report(d, P)["corners"].get("SS")
            except Exception:
                cr = None
        tap_xy = {f"{t['part']}/{t['tap']}": t["xy"] for t in tree["taps"]}
        if cr:
            bad = [r for r in cr.get("all_seams", cr.get("worst_seams", [])) if r.get("ocv3_ps", 0) > 80]
            for r in bad:
                a, b = tap_xy[r["launch"]], tap_xy[r["capture"]]
                ax.plot([a[0] / 1000, b[0] / 1000], [a[1] / 1000, b[1] / 1000], color="red", lw=1.5)
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
        ax.set_title(f"{P.name} die clock H-tree ({tree['meta']['taps']} taps, {tree['meta']['repeaters']} repeaters, "
                     f"leaf {tree['meta']['leaf_um']:g} um); red = seam tap pairs > 80 ps skew at 3% OCV  [mm]", fontsize=9)
        fig.tight_layout(); fig.savefig(rd / "clock_tree.png"); plt.close(fig)
        out["clock_tree"] = str(rd / "clock_tree.png")
    # (3) congestion from the GRT guides
    gf = d / "grt" / "route.guide"
    if gf.is_file():
        adj = kit["grt"]["adjust"]
        util, gm = guide_maps(P, gf, adjust=adj)
        np.savez_compressed(rd / "congestion.npz", **util)
        fig, axs = plt.subplots(1, 2, figsize=(figw, figh / 2 + 0.6), dpi=150)
        for ax, Ls, name in ((axs[0], ("M4", "M5", "M6", "M7"), "M4-M7 (ft share 25%)"),
                             (axs[1], ("M8", "M9"), "M8/M9 (60% of PG-free)")):
            m = np.max(np.stack([util[L] for L in Ls]), axis=0)
            im = ax.imshow(m, origin="lower", extent=(0, W, 0, H), cmap="inferno", vmin=0, vmax=1.2)
            _part_patches(ax, P, alpha=0.0, edge="0.5")
            ax.set_title(f"{name}: max window utilisation (win {gm['win_um']:g} um), peak {m.max():.2f}", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.03)
        fig.tight_layout(); fig.savefig(rd / "congestion.png"); plt.close(fig)
        out["congestion"] = str(rd / "congestion.png")
        stats = {}
        for L, u in util.items():
            flat = u[u > 0]
            j, i = np.unravel_index(np.argmax(u), u.shape)
            stats[L] = dict(peak=round(float(u.max()), 3), p99=round(float(np.percentile(flat, 99)), 3) if flat.size else 0,
                            windows_over_1=int((u > 1.0).sum()), windows_over_0p8=int((u > 0.8).sum()),
                            peak_xy_um=[round((i + 0.5) * gm["win_um"], 1), round((j + 0.5) * gm["win_um"], 1)],
                            peak_part=next((n for n in P.parts if P.rect(n)[0] <= (i + .5) * gm["win_um"] < P.rect(n)[2]
                                            and P.rect(n)[1] <= (j + .5) * gm["win_um"] < P.rect(n)[3]), None))
        # worst windows overall (any layer)
        allw = []
        for L, u in util.items():
            idx = np.argsort(u, axis=None)[-12:]
            for k in idx:
                j, i = np.unravel_index(k, u.shape)
                x, y = (i + 0.5) * gm["win_um"], (j + 0.5) * gm["win_um"]
                allw.append(dict(layer=L, util=round(float(u[j, i]), 3), xy_um=[round(x, 1), round(y, 1)],
                                 part=next((n for n in P.parts if P.rect(n)[0] <= x < P.rect(n)[2] and P.rect(n)[1] <= y < P.rect(n)[3]), None)))
        allw.sort(key=lambda r: -r["util"])
        (rd / "congestion.json").write_text(json.dumps(dict(meta=gm, layers=stats, worst=allw[:30]), indent=1) + "\n")
    # (4) IR map
    vf = d / "psm" / "ir_VDD.csv"
    if vf.is_file():
        xs, ys, vs = [], [], []
        for ln in vf.read_text().splitlines()[1:]:
            x = ln.replace(",", " ").split()
            try:
                xs.append(float(x[0])); ys.append(float(x[1])); vs.append(float(x[-1]))
            except (ValueError, IndexError):
                continue
        if vs:
            xs, ys, vs = np.array(xs), np.array(ys), np.array(vs)
            if xs.max() > P.W * 2:        # dbu
                xs, ys = xs / 1000.0, ys / 1000.0
            vdd = float(vs.max()) if vs.max() < 1.5 else 0.7
            nb = 400
            gx = np.clip((xs / P.W * nb).astype(int), 0, nb - 1)
            gy = np.clip((ys / P.H * int(nb * H / W)).astype(int), 0, int(nb * H / W) - 1)
            m = np.full((int(nb * H / W), nb), np.nan)
            drop = (0.7 - vs) * 1000.0
            for a, b, v in zip(gy, gx, drop):
                if np.isnan(m[a, b]) or v > m[a, b]:
                    m[a, b] = v
            fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
            im = ax.imshow(m, origin="lower", extent=(0, W, 0, H), cmap="magma_r")
            _part_patches(ax, P, alpha=0.0, edge="0.6")
            for w in kit.get("die_io", []):
                x0, y0, x1, y1 = w["rect_um"]
                ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, fill=False,
                                       edgecolor="cyan", lw=1.0, ls="--"))
            fig.colorbar(im, ax=ax, fraction=0.025, label="VDD IR drop (mV)")
            ax.set_title(f"{P.name} VDD IR drop (PDNSim, {kit['psm']['density_w_mm2']} W/mm2 uniform = "
                         f"{kit['psm']['total_w']} W, C4 150 um bumps outside IO windows), worst {np.nanmax(m):.1f} mV",
                         fontsize=9)
            fig.tight_layout(); fig.savefig(rd / "ir_vdd.png"); plt.close(fig)
            out["ir"] = str(rd / "ir_vdd.png")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kit")
    k.add_argument("plan")
    k.add_argument("--out", required=True)
    k.add_argument("--views")
    k.add_argument("--leaf-um", type=float, default=600.0)
    k.add_argument("--rep-um", type=float, default=450.0)
    k.add_argument("--coarse-um", type=float, default=0.72)
    k.add_argument("--density", type=float, default=0.15, help="die power density W/mm2 for PDNSim")
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--plan")
    g = sub.add_parser("render")
    g.add_argument("dir")
    g.add_argument("--plan")
    c = sub.add_parser("clock")
    c.add_argument("dir")
    c.add_argument("--plan")
    h = sub.add_parser("standin-contract", help="copy a die_sta PARTS dir of bare stand-ins with the boundary-hold "
                                                "contract cell added (re-time an existing trial without a new kit)")
    h.add_argument("parts")
    h.add_argument("--out", required=True)
    h.add_argument("--tol-ps", type=float, default=float(S.DEFAULT_CLOCK["insertion_tol_ps"]))
    j = sub.add_parser("standins", help="write the die_sta PARTS stand-ins of every plan type (contract form: "
                                         "boundary-hold + clock-latency cells) without a full kit")
    j.add_argument("plan")
    j.add_argument("--out", required=True)
    j.add_argument("--no-clock-contract", action="store_true", help="legacy: face flops load the tap port directly")
    a = ap.parse_args(argv)
    if a.cmd == "standins":
        P = S.Plan(S.load(a.plan))
        tot = {}
        for tn, t in sorted(P.types.items()):
            d = Path(a.out) / t["module"]
            d.mkdir(parents=True, exist_ok=True)
            v, k = standin_netlist(P, tn, clock_contract=not a.no_clock_contract)
            (d / "6_final.v").write_text(v)
            tot[t["module"]] = k
        print(json.dumps(dict(types=len(tot), face_flops=sum(tot.values()),
                              clock_contract=not a.no_clock_contract), indent=1))
        return 0
    if a.cmd == "standin-contract":
        tot = {}
        for v in sorted(Path(a.parts).glob("*/6_final.v")):
            t, n = standin_add_contract(v.read_text(), a.tol_ps)
            d = Path(a.out) / v.parent.name
            d.mkdir(parents=True, exist_ok=True)
            (d / "6_final.v").write_text(t)
            tot[v.parent.name] = n
        print(json.dumps(dict(cell=die_sta.bhold_cell(a.tol_ps), types=len(tot), input_bits=sum(tot.values())), indent=1))
        return 0
    if a.cmd == "kit":
        m = write_kit(a.plan, a.out, a.views, a.leaf_um, a.rep_um, a.coarse_um, a.density)
        print(json.dumps({k: m[k] for k in ("die", "parts", "types", "closed_views", "hard_cores", "clock_tree", "grt",
                                             "psm", "sta")}, indent=1))
    elif a.cmd == "report":
        res = cmd_report(a)
        print(json.dumps({k: v for k, v in res.items() if k != "kit"}, indent=1)[:6000])
    elif a.cmd == "render":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        P = S.Plan(S.load(a.plan or kit["plan"]))
        print(json.dumps(render_all(d, P, a.plan or kit["plan"]), indent=1))
    elif a.cmd == "clock":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        P = S.Plan(S.load(a.plan or kit["plan"]))
        print(json.dumps(clock_report(d, P), indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
