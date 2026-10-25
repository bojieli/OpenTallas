"""TRIAL-HBM step 2: build the die H-tree clock of a die plan in OpenROAD and measure insertion / tap skew.

Inputs: the die plan (die_plan.json) and its H-tree plan (clock_htree.json, physical/die_plan/hbm_arch/clock_htree.py).

    python3 tools/die_trial/htree_clock.py gen    PLAN HTREE --out DIR [--scope full|rib] [--rep-um 400]
                                                   [--local-rep-um 300] [--taps-cache taps.json] [--mem 96]
    (cd DIR && bash run.sh)                        # GRT + parasitics (grt.tcl), then STA per corner (sta_SS/TT/FF.tcl)
    python3 tools/die_trial/htree_clock.py report  DIR --plan PLAN --res RESDIR

Model (all on the die layers M8/M9; the partitions own M1-M7):
  * clk port at gen_phys.die_root_pins (M9) -> root buffer at the H-tree root.
  * H-tree: one BUFx24 at every branch node; each segment of length L is cut into ceil(L / rep_um) equal pieces with a
    BUFx24 repeater at each cut (all segments of a level have the same length, so every symmetric branch has the
    identical repeater count).  Segment nets carry NDR 2W2S (+ VSS shields modelled as spacing: 5 tracks per wire).
  * leaves: the level-8 node buffers are the 256 tap drivers.
  * taps: every partition clock tap of the plan (exactly as g2.py die_probe: tap 0 + R4 grid taps + declared taps, in
    die coordinates) is the input A of a BUFx24 tap buffer placed at the tap.  Each tap is fed from its nearest leaf
    (Manhattan) by its own repeater chain along an x-then-y L route, with the SAME number of stages K for every tap
    (K = ceil(max leaf->tap distance / local_rep_um); stage spacing = d / K), i.e. a delay-balanced local star.
  * placement: cells are placed at their coordinates (snapped to the site grid), FIRM, without legalization (die-size
    DPL grids are prohibitive; overlaps do not affect GRT / STA).  No M1-M7 obstructions (buffer pins are M1; the
    nets are restricted to M8-M9 by set_routing_layers, GRT adds the pin via stacks).  Die PG stripes = M8/M9
    obstructions.
  * GRT (-allow_congestion), estimate_parasitics -global_routing -> SPEF; STA per corner (SS/TT/FF RVT NLDM, the same
    RC), set_propagated_clock, period 833.333 ps; arrivals at every buffer pin.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
LIB = PLAT + "/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz"
CORNERS = ("SS", "TT", "FF")
NODEBUF = "BUFx24_ASAP7_75t_R"
REPBUF = "BUFx24_ASAP7_75t_R"
LEAFBUF = "BUFx24_ASAP7_75t_R"
CHAINBUF = "BUFx12f_ASAP7_75t_R"
TAPBUF = "BUFx24_ASAP7_75t_R"
CELL_W = {"BUFx24_ASAP7_75t_R": 1.62, "BUFx12f_ASAP7_75t_R": 0.972}
GCELL = 15 * 0.64          # GRT gcell = 15 x the (coarse) M3 track pitch
SITE_W, ROW_H = 0.054, 0.27
PERIOD = 833.333


def snap(x, y, W, H):
    x = min(max(x, 0.5), W - 3.0)
    y = min(max(y, 0.5), H - 1.0)
    return round(round(x / SITE_W) * SITE_W, 4), round(round(y / ROW_H) * ROW_H, 4)


def plan_taps(P, cache=None):
    """[(part, tap name, x, y)] die frame, exactly as g2.py die_probe (slow on hard-core types: cache it)."""
    if cache and Path(cache).exists():
        return [tuple(t) for t in json.load(open(cache))]
    out = []
    for n, p in sorted(P.parts.items()):
        t = P.ptype(n)
        if t.get("hard"):
            # A hard macro's clock terminal is fixed by its physical view.  It
            # may be inside a domain keepout: that forbids standard cells, not
            # the macro's own terminal.  Never turn it into a legalized grid.
            xy = t.get("clock", {}).get("tap_um")
            if not isinstance(xy, (list, tuple)) or len(xy) != 2:
                raise ValueError(f"hard type {p['type']} requires an explicit clock.tap_um")
            x, y = map(float, xy)
            w, h = map(float, t["outline_um"])
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= w and 0 <= y <= h):
                raise ValueError(f"hard type {p['type']} has an invalid clock.tap_um: {xy}")
            out.append((n, "clk", *P.to_die(n, (x, y))))
            continue
        ck, _ = gen_phys.tap_points(P, p["type"])
        out.append((n, "clk", *P.to_die(n, ck)))
        for tnm, tx, ty in gen_phys.clock_pins(P, p["type"])[1:]:
            out.append((n, tnm, *P.to_die(n, (tx, ty))))
        for i, tap in enumerate(P.ptype(n).get("clock", {}).get("taps", [])):
            out.append((n, f"declared_{i}", *P.to_die(n, tap["xy"])))
    if cache:
        json.dump(out, open(cache, "w"))
    return out


def build_tree(H):
    """nodes {id: dict(xy, level, parent, seg)} from the DFS-ordered segment list; node 0 = root."""
    root = tuple(H["root_um"])
    nodes = {0: dict(xy=root, level=0, parent=None, seg=None, kids=[])}
    at = {(root, 0): 0}
    for si, s in enumerate(H["segments"]):
        x0, y0, x1, y1 = s["xy"]
        lev = s["level"]
        par = at.get(((x0, y0), lev - 1))
        if par is None:
            raise ValueError(f"segment {si} start {x0, y0} level {lev}: no parent node")
        nid = len(nodes)
        nodes[nid] = dict(xy=(x1, y1), level=lev, parent=par, seg=si, kids=[],
                          length=abs(x1 - x0) + abs(y1 - y0), layer=s["layer"])
        nodes[par]["kids"].append(nid)
        if ((x1, y1), lev) in at:
            raise ValueError(f"duplicate node {x1, y1} level {lev}")
        at[((x1, y1), lev)] = nid
    return nodes


def gen(P, H, out, scope="full", rep_um=400.0, local_rep_um=300.0, taps_cache=None, mem=96, cpus=8, local_match=True):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    W, Hd = P.W, P.H
    nodes = build_tree(H)
    # gcell-congruent geometry: GRT grid origin puts the root at a gcell centre; every node offset and repeater offset
    # is a whole number of gcells, so mirror branches see identical pin-to-gcell stubs in estimate_parasitics
    # (with the plan's raw coordinates the stubs drift by up to ~0.1 kohm per stage and fake ~35 ps H-tree skew).
    G = GCELL
    # (GRT -grid_origin is honoured by the router but the parasitic estimate's pin stubs then grow to ~3 um: keep the
    # default origin and move the root to the nearest gcell centre instead, <= 4.8 um)
    origin = (0.0, 0.0)
    plan_xy = {i: tuple(n["xy"]) for i, n in nodes.items()}
    rx, ry = nodes[0]["xy"]
    nodes[0]["xy"] = ((math.floor(rx / G) + 0.5) * G, (math.floor(ry / G) + 0.5) * G)
    for i in sorted(nodes):
        n = nodes[i]
        if n["parent"] is None:
            continue
        (px, py), (x1, y1) = plan_xy[n["parent"]], plan_xy[i]
        q = round(n["length"] / G) * G
        qx, qy = nodes[n["parent"]]["xy"]
        n["xy"] = (qx + math.copysign(q, x1 - px), qy) if abs(x1 - px) > abs(y1 - py) else (qx, qy + math.copysign(q, y1 - py))
        n["length"] = q
    node_disp = max(abs(nodes[i]["xy"][0] - plan_xy[i][0]) + abs(nodes[i]["xy"][1] - plan_xy[i][1]) for i in nodes)

    def gc(x, y):
        return (origin[0] + (math.floor((x - origin[0]) / G) + 0.5) * G,
                origin[1] + (math.floor((y - origin[1]) / G) + 0.5) * G)
    maxlev = max(n["level"] for n in nodes.values())
    leaves = [i for i, n in nodes.items() if not n["kids"]]
    lv_xy = sorted(tuple(nodes[i]["xy"]) for i in leaves)
    if sorted(plan_xy[i] for i in leaves) != sorted(tuple(l) for l in H["leaves"]):
        raise ValueError("tree leaves != clock_htree.json leaves")
    taps = plan_taps(P, taps_cache)
    # tap -> nearest leaf
    assign = {}
    for k, (part, tn, x, y) in enumerate(taps):
        assign[k] = min(leaves, key=lambda i: (abs(nodes[i]["xy"][0] - x) + abs(nodes[i]["xy"][1] - y), i))
    dist = {k: abs(nodes[assign[k]]["xy"][0] - t[2]) + abs(nodes[assign[k]]["xy"][1] - t[3]) for k, t in enumerate(taps)}
    K = max(1, math.ceil(max(dist.values()) / local_rep_um))
    # scope: full die, or one rib-side subtree (the west rib of the lowest rib node) for a fast test
    keep = set(nodes)
    top = 0
    if scope == "rib":
        top = min((i for i, n in nodes.items() if n["level"] == 3), key=lambda i: (nodes[i]["xy"][1], nodes[i]["xy"][0]))
        keep, st = set(), [top]
        while st:
            i = st.pop()
            keep.add(i)
            st += nodes[i]["kids"]
        top = nodes[top]["parent"]       # the rib node drives the rib segment
        keep.add(top)
    tkeep = [k for k in range(len(taps)) if assign[k] in keep]
    cells, nets, place, ndr_nets = [], set(), [], []
    pins = dict(leaf_in={}, tap_in={}, div={})
    rp = {n: (x, y) for n, _, x, y in gen_phys.die_root_pins(P)}["clk"] if scope == "full" else nodes[top]["xy"]

    def inst(cell, name, a, y, xy, orient="R0"):
        cells.append(f"  {cell} {name} (.A({a}){', .Y(' + y + ')' if y else ''});")
        w = CELL_W.get(cell, 1.62)
        place.append((name, *snap(xy[0] - w / 2, xy[1] - ROW_H / 2, W, Hd), orient))
        if y:
            nets.add(y)

    def orient_of(a, b):
        """mirror cells of west / south going branches so that A->Y runs along the branch on both sides
        (otherwise the unmirrored A/Y pin offsets make W/E (S/N) mirror branches differ by ~1 um per stage)."""
        if abs(b[0] - a[0]) > abs(b[1] - a[1]):
            return "MY" if b[0] < a[0] else "R0"
        return "MX" if b[1] < a[1] else "R0"
    # root (or rib node) buffer -> net ni_top; at every internal node one buffer per child (point-to-point nets)
    inst(NODEBUF, "ht_root", "clk", f"ni_{top}", nodes[top]["xy"])
    ndr_nets.append(f"ni_{top}")
    pins["div"][top] = "ht_root/Y"
    nrep = {}
    order = [top]
    for i in order:
        order += [k for k in nodes[i]["kids"] if k in keep]
    for i in order[1:]:
        n = nodes[i]
        par = n["parent"]
        (x0, y0), (x1, y1) = nodes[par]["xy"], n["xy"]
        ori = orient_of((x0, y0), (x1, y1))
        pcs = max(1, math.ceil(n["length"] / rep_um - 1e-9))
        nrep[n["level"]] = pcs - 1
        inst(NODEBUF, f"hb_{i}", f"ni_{par}", f"ns_{i}_0", (x0, y0), ori)
        ndr_nets.append(f"ns_{i}_0")
        drv, dpin = f"ns_{i}_0", f"hb_{i}/Y"
        for j in range(1, pcs):
            f = round(j / pcs * n["length"] / G) * G / n["length"]
            nm = f"rp_{i}_{j}"
            out_net = f"ns_{i}_{j}" if j < pcs - 1 else f"ni_{i}"
            inst(REPBUF, nm, drv, out_net, (x0 + f * (x1 - x0), y0 + f * (y1 - y0)), ori)
            ndr_nets.append(out_net)
            drv, dpin = out_net, f"{nm}/Y"
        if pcs == 1:                      # no repeater: the child buffer drives the node net directly
            cells[-1] = cells[-1].replace(f".Y(ns_{i}_0)", f".Y(ni_{i})")
            nets.discard(f"ns_{i}_0"); nets.add(f"ni_{i}")
            ndr_nets[-1] = f"ni_{i}"
        pins["div"][i] = dpin
        if not n["kids"]:
            inst(LEAFBUF, f"lf_{i}", f"ni_{i}", f"nl_{i}", n["xy"])
            pins["leaf_in"][i] = f"lf_{i}/A"
    # local stars: leaf driver -> K-stage chain -> tap buffer.  With --local-match every chain is length-matched to
    # the die-wide max leaf->tap distance D by a detour (out by e = (D - d) / 2 away from the tap, across, back), so
    # every tap sees the same wire length and stage count.  Leaves are padded with dummy chain heads to equal fanout.
    D = max(dist.values())
    heads = defaultdict(int)
    for k in tkeep:
        heads[assign[k]] += 1
    maxheads = max(heads.values()) if heads else 0
    for k in tkeep:
        part, tn, tx, ty = taps[k]
        lx, ly = nodes[assign[k]]["xy"]
        d = dist[k]
        e = (D - d) / 2.0 if local_match else 0.0
        s_ = -1.0 if ty > ly else 1.0
        if not (1.0 < ly + s_ * e < Hd - 1.0):
            s_ = -s_
        if local_match and not (1.0 < ly + s_ * e < Hd - 1.0):   # cannot detour in y: detour in x instead
            sx = -1.0 if tx > lx else 1.0
            if not (1.0 < lx + sx * e < W - 3.0):
                sx = -sx
            poly = [(lx, ly), (lx + sx * e, ly), (lx + sx * e, ty), (tx, ty)]
        else:
            poly = [(lx, ly), (lx, ly + s_ * e), (tx, ly + s_ * e), (tx, ty)]
        segl = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(poly, poly[1:])]
        tot = sum(segl)

        def at(sv):
            for (a, b), L in zip(zip(poly, poly[1:]), segl):
                if sv <= L + 1e-9 and L > 0:
                    f = sv / L
                    return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
                sv -= L
            return poly[-1]
        drv = f"nl_{assign[k]}"
        for j in range(K):
            nm = f"ch_{k}_{j}"
            inst(CHAINBUF, nm, drv, f"nc_{k}_{j}", gc(*at(tot * j / K)) if j else (lx, ly))
            drv = f"nc_{k}_{j}"
        inst(TAPBUF, f"tb_{k}", drv, None, (tx, ty))
        pins["tap_in"][k] = f"tb_{k}/A"
    ndum = 0
    if local_match:
        for i in pins["leaf_in"]:
            for j in range(maxheads - heads.get(i, 0)):
                inst(CHAINBUF, f"dm_{i}_{j}", f"nl_{i}", None, nodes[i]["xy"])
                ndum += 1
    v = ["module htree_clock (clk);", "  input clk;"] + [f"  wire {n};" for n in sorted(nets)] + cells + ["endmodule"]
    (out / "case.v").write_text("\n".join(v) + "\n")

    # ---- grt.tcl
    t = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"] + \
        [f"read_liberty {LIB.format(c='TT')}", "read_verilog /work/case.v", "link_design htree_clock",
         f"initialize_floorplan -die_area {{0 0 {W:g} {Hd:g}}} -core_area {{0 0 {W:g} {Hd:g}}} -site asap7sc7p5t"]
    for i in range(1, 10):
        L = P.layers.get(f"M{i}")
        if f"M{i}" in ("M8", "M9"):
            t.append(f"make_tracks M{i} -x_offset {L['offset_um']:g} -x_pitch {L['pitch_um']:g} "
                     f"-y_offset {L['offset_um']:g} -y_pitch {L['pitch_um']:g}")
        else:
            t.append(f"make_tracks M{i} -x_offset 0.32 -x_pitch 0.64 -y_offset 0.32 -y_pitch 0.64")
    t += [f"source {PLAT}/setRC.tcl", "set block [ord::get_db_block]"]
    sz = "{0.04 0.32}"
    t.append(f"place_pin -pin_name clk -layer M9 -location {{{rp[0]:.4f} {rp[1]:.4f}}} -pin_size {sz}")
    (out / "place.tcl").write_text("\n".join(
        f"place_inst -name {c} -location {{{x:.4f} {y:.4f}}} -orientation {o} -status FIRM" for c, x, y, o in place) + "\n")
    t.append("source /work/place.tcl")
    nst = 0
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = Hd if L["dir"] == "V" else W
        span = W if L["dir"] == "V" else Hd
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                r = (a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)
                t.append(f"create_obstruction -region {{{r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f}}} -layer {g['layer']}")
                nst += 1
            pos += g["pitch_um"]
    # NDR 2W2S + VSS shield each side = 5 tracks per wire: width 2W (0.08), spacing 0.32 so (w + s) / pitch = 5
    t.append("create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}")
    (out / "ndr.tcl").write_text("\n".join(f"assign_ndr -ndr CK2W2S -net {n}" for n in ndr_nets) + "\n")
    t.append("source /work/ndr.tcl")
    t += ["set_routing_layers -signal M8-M9 -clock M8-M9",
          "set t0 [clock seconds]",
          "global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt",
          'puts "OT_GRT_S [expr {[clock seconds]-$t0}]"',
          "estimate_parasitics -global_routing -spef_file /work/case.spef",
          "if {[catch {report_wire_length -summary -global_route -net *} e]} { puts \"OT_WL_ERR $e\" }",
          "write_db /work/case.odb", "puts OT_GRT_DONE"]
    (out / "grt.tcl").write_text("\n".join(t) + "\n")
    # ---- sta per corner: arrivals + slews of every buffer pin
    for c in CORNERS:
        s = [f"read_liberty {LIB.format(c=c)}", "read_db /work/case.odb", "read_spef /work/case.spef",
             f"create_clock -name clk -period {PERIOD} [get_ports clk]", "set_input_transition 20 [get_ports clk]",
             "set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]",
             "set_propagated_clock [all_clocks]", "report_worst_slack",
             f"set f [open /work/arr_{c}.txt w]",
             "foreach p [get_pins -hierarchical */*] {",
             "  set a [get_property $p arrival_max_rise]",
             "  set s [get_property $p slew_max_rise]",
             "  puts $f \"[get_full_name $p] $a $s\"", "}", "close $f",
             f"report_check_types -max_slew -max_capacitance -max_fanout -violators > /work/viol_{c}.rpt",
             f"report_check_types -max_slew -max_capacitance > /work/checks_{c}.rpt",
             "puts OT_STA_DONE"]
        (out / f"sta_{c}.tcl").write_text("\n".join(s) + "\n")
    name = f"htclk{os.getpid()}"
    (out / "run.sh").write_text(f"""#!/bin/bash
# TRIAL-HBM die H-tree clock: GRT + parasitics, then STA per corner.  docker --memory = --memory-swap = {mem}G
D=$(cd $(dirname $0) && pwd)
DK="docker"; $DK ps >/dev/null 2>&1 || DK="sudo docker"
run() {{ $DK run --rm --name {name}-$1-$$ --cpus={cpus} --memory={mem}g --memory-swap={mem}g -v $D:/work -w /work {IMAGE} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads {cpus} -exit /work/$1.tcl > /work/$1.log 2>&1; echo EXIT \\$? > /work/$1.exit; chmod -R a+rwX /work"; cat $D/$1.exit; }}
date; run grt
for c in SS TT FF; do run sta_$c & done; wait; date
""")
    os.chmod(out / "run.sh", 0o755)
    meta = dict(scope=scope, rep_um=rep_um, local_rep_um=local_rep_um, local_stages=K, top=top, gcell_um=G, grt_origin=list(origin), node_snap_max_um=round(node_disp, 3), local_match=local_match,
                local_match_len_um=round(max(dist.values()), 3) if local_match else None, dummy_heads=ndum,
                max_heads_per_leaf=maxheads, div_pins=pins["div"],
                cells=dict(node=NODEBUF, rep=REPBUF, leaf=LEAFBUF, chain=CHAINBUF, tap=TAPBUF),
                ncells=len(cells), nnets=len(nets), ndr_nets=len(ndr_nets), pg_stripes=nst, root_pin=list(rp),
                reps_per_segment_by_level=nrep, max_level=maxlev,
                nodes={i: dict(xy=list(n["xy"]), level=n["level"], parent=n["parent"], length=n.get("length"))
                       for i, n in nodes.items() if i in keep},
                taps=[dict(id=k, part=taps[k][0], name=taps[k][1], xy=[taps[k][2], taps[k][3]], leaf=assign[k],
                           dist_um=round(dist[k], 3)) for k in tkeep],
                all_tap_count=len(taps), max_leaf_tap_um=max(dist.values()))
    (out / "meta.json").write_text(json.dumps(meta) + "\n")
    return meta


# ----------------------------------------------------------------------------------------------- report
GRT_ROW = re.compile(r"^\s*(M\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")


def parse_grt(text):
    tables, cur = [], None
    for ln in text.splitlines():
        m = GRT_ROW.match(ln)
        if m:
            if cur is None:
                cur = {}
                tables.append(cur)
            cur[m.group(1)] = dict(resource=int(m.group(2)), demand=int(m.group(3)), usage_pct=float(m.group(4)),
                                   overflow=int(m.group(7)))
        elif cur is not None and ln.strip() and not ln.strip().startswith("-"):
            cur = None
    res = dict(layers=tables[-1] if tables else {})
    m = re.findall(r"Total wirelength:\s*([\d.]+)\s*um", text)
    res["wirelength_um"] = float(m[-1]) if m else None
    res["wirelength_by_layer_um"] = {l: float(v) for l, v in re.findall(r"^(M\d+)\s+([\d.]+)um\s+\d+%", text, re.M)}
    res["errors"] = sorted(set(re.findall(r"\[ERROR ([A-Z]+-\d+)\]", text)))
    res["warnings"] = sorted(set(re.findall(r"\[WARNING ([A-Z]+-\d+)\]", text)))
    m = re.search(r"OT_GRT_S (\d+)", text)
    res["grt_s"] = int(m.group(1)) if m else None
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    res["peak_rss_gb"] = round(int(m.group(1)) / 1e6, 2) if m else None
    m = re.search(r"Elapsed \(wall clock\) time.*: (\S+)", text)
    res["wall"] = m.group(1) if m else None
    res["done"] = "OT_GRT_DONE" in text
    return res


def stats(v):
    v = list(v)
    return dict(n=len(v), min=round(min(v), 2), max=round(max(v), 2), mean=round(sum(v) / len(v), 2),
                spread=round(max(v) - min(v), 2)) if v else None


OCV = 0.05      # +/-5 % derate on the non-common clock path (late +5 %, early -5 %)


def _group(rows, key):
    g = defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            g[r[key]].append(r)
    return g


def adjacency(P):
    """abutted partition pairs sharing a face: [(a, b, orient 'V'|'H', overlap_um)]."""
    R = {n: P.rect(n) for n in P.parts}
    out = []
    ns = sorted(R)
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            A, B = R[a], R[b]
            if abs(A[2] - B[0]) < 0.01 or abs(B[2] - A[0]) < 0.01:
                ov = min(A[3], B[3]) - max(A[1], B[1])
                if ov > 1.0:
                    out.append((a, b, "V", round(ov, 2)))
            if abs(A[3] - B[1]) < 0.01 or abs(B[3] - A[1]) < 0.01:
                ov = min(A[2], B[2]) - max(A[0], B[0])
                if ov > 1.0:
                    out.append((a, b, "H", round(ov, 2)))
    return out


def report(d, plan, res):
    d, res = Path(d), Path(res)
    res.mkdir(parents=True, exist_ok=True)
    P = S.Plan(S.load(plan))
    meta = json.loads((d / "meta.json").read_text())
    nodes = {int(k): v for k, v in meta["nodes"].items()}
    taps = meta["taps"]
    grt = parse_grt((d / "grt.log").read_text(errors="replace"))
    wl = defaultdict(float)
    arr, slew = {}, {}
    for c in CORNERS:
        a, s = {}, {}
        f = d / f"arr_{c}.txt"
        if not f.exists():
            continue
        for ln in f.read_text().splitlines():
            p = ln.split()
            if len(p) >= 3:
                try:
                    a[p[0]] = float(p[1])
                    s[p[0]] = float(p[2])
                except ValueError:
                    pass
        arr[c], slew[c] = a, s
    top = meta["top"]
    leaves = [i for i, n in nodes.items() if not any(m["parent"] == i for m in nodes.values())]
    anc = {}

    def path(i):
        if i not in anc:
            anc[i] = [i] if i == top or nodes[i]["parent"] is None else path(nodes[i]["parent"]) + [i]
        return anc[i]
    adj = adjacency(P)
    out = dict(case_dir=str(d), scope=meta["scope"], rep_um=meta["rep_um"], local_rep_um=meta["local_rep_um"],
               local_stages=meta["local_stages"], cells=meta["cells"], ncells=meta["ncells"], ndr_nets=meta["ndr_nets"],
               reps_per_segment_by_level=meta["reps_per_segment_by_level"], depth_levels=meta["max_level"],
               taps=len(taps), all_plan_taps=meta["all_tap_count"], max_leaf_tap_um=meta["max_leaf_tap_um"],
               grt=grt, corners={},
               htree_geometric_wirelength_um=round(sum(n["length"] or 0 for n in nodes.values()), 1),
               local_leaf_tap_manhattan_sum_um=round(sum(t["dist_um"] for t in taps), 1),
               local_matched_wirelength_um=round(len(taps) * (meta.get("local_match_len_um") or 0), 1),
               leaves_without_taps=sum(1 for i in leaves if not any(t["leaf"] == i for t in taps)),
               taps_per_leaf_max=max(sum(1 for t in taps if t["leaf"] == i) for i in leaves),
               leaf_tap_dist_um=stats(t["dist_um"] for t in taps),
               node_snap_max_um=meta.get("node_snap_max_um"))
    sta_logs = {c: (d / f"sta_{c}.log").read_text(errors="replace") if (d / f"sta_{c}.log").exists() else "" for c in CORNERS}
    lat = dict(corners={}, partition_mean={})
    for c in arr:
        A, Sl = arr[c], slew[c]
        tin = {t["id"]: A.get(f"tb_{t['id']}/A") for t in taps}
        lin = {i: A.get(f"lf_{i}/A") for i in leaves}
        nout = {int(i): A.get(p) for i, p in meta["div_pins"].items()}
        miss = [k for k, v in tin.items() if v is None] + [i for i, v in lin.items() if v is None]
        loc = [tin[t["id"]] - lin[t["leaf"]] for t in taps if tin[t["id"]] is not None]
        per_leaf = defaultdict(list)
        for t in taps:
            per_leaf[t["leaf"]].append(tin[t["id"]])
        leaf_imb = max(max(v) - min(v) for v in per_leaf.values())
        # seam skew over abutted pairs: every tap of A vs every tap of B (worst) and nearest-across-face pairs
        by_part = defaultdict(list)
        for t in taps:
            by_part[t["part"]].append(t)
        seams = []
        def pair(ta, tb):
            xa, xb = tin[ta["id"]], tin[tb["id"]]
            pa, pb = path(ta["leaf"]), path(tb["leaf"])
            j = 0
            while j < min(len(pa), len(pb)) and pa[j] == pb[j]:
                j += 1
            lca = pa[j - 1]
            # divergence: same leaf -> the leaf driver output; else the net at the LCA node (driver = div pin)
            cp = A.get(f"lf_{lca}/Y") if ta["leaf"] == tb["leaf"] else nout[lca]
            return dict(skew=abs(xa - xb), ocv=abs(xa - xb) + OCV * (xa + xb),
                        ocv_cppr=abs(xa - xb) + OCV * ((xa - cp) + (xb - cp)), common_ps=cp, lca_level=nodes[lca]["level"],
                        noncommon_ps=(xa - cp) + (xb - cp), taps=[ta["name"], tb["name"]])

        def face_taps(part, other, o):
            """taps of `part` in the tap row / column facing `other` (within one tap pitch of the nearest row)."""
            ra, rb = P.rect(part), P.rect(other)
            if o == "V":
                xf = ra[2] if abs(ra[2] - rb[0]) < 0.01 else ra[0]
                lo, hi = max(ra[1], rb[1]) - 200, min(ra[3], rb[3]) + 200
                dd = [(abs(t["xy"][0] - xf), t) for t in by_part[part] if lo <= t["xy"][1] <= hi]
            else:
                yf = ra[3] if abs(ra[3] - rb[1]) < 0.01 else ra[1]
                lo, hi = max(ra[0], rb[0]) - 200, min(ra[2], rb[2]) + 200
                dd = [(abs(t["xy"][1] - yf), t) for t in by_part[part] if lo <= t["xy"][0] <= hi]
            if not dd:          # e.g. a hard core's single central tap: it is the partition's only clock entry
                return list(by_part[part])
            m0 = min(x for x, _ in dd)
            return [t for x, t in dd if x <= m0 + 400.0]
        seams = []
        for a, b, o, ov in adj:
            if a not in by_part or b not in by_part:
                continue
            allp = [pair(ta, tb) for ta in by_part[a] for tb in by_part[b]]
            fa, fb = face_taps(a, b, o), face_taps(b, a, o)
            fp = []
            for x, ys in ((fa, fb), (fb, fa)):
                for t in x:
                    if ys:
                        u = min(ys, key=lambda q: (q["xy"][0] - t["xy"][0]) ** 2 + (q["xy"][1] - t["xy"][1]) ** 2)
                        fp.append(pair(t, u))
            wf = max(fp, key=lambda r: r["ocv_cppr"]) if fp else None
            wa = max(allp, key=lambda r: r["ocv_cppr"])
            seams.append(dict(a=a, b=b, face=o, overlap_um=ov,
                              max_skew_ps=round(max(r["skew"] for r in allp), 2),
                              worst_ocv_cppr_ps=round(wa["ocv_cppr"], 2), worst_ocv_nocppr_ps=round(max(r["ocv"] for r in allp), 2),
                              common_path_ps=round(wa["common_ps"], 2), lca_level=wa["lca_level"],
                              face_pairs=len(fp),
                              face_max_skew_ps=round(max(r["skew"] for r in fp), 2) if fp else None,
                              face_worst_ocv_cppr_ps=round(wf["ocv_cppr"], 2) if fp else None,
                              face_worst_ocv_nocppr_ps=round(max(r["ocv"] for r in fp), 2) if fp else None,
                              face_common_path_ps=round(wf["common_ps"], 2) if fp else None,
                              face_lca_level=wf["lca_level"] if fp else None,
                              face_noncommon_ps=round(wf["noncommon_ps"], 1) if fp else None,
                              face_tolerable_derate_pct=round(100 * max(0.0, 80 - max(r["skew"] for r in fp))
                                                              / wf["noncommon_ps"], 3) if fp and wf["noncommon_ps"] else None,
                              face_taps=wf["taps"] if fp else None))
        seams.sort(key=lambda r: -(r["face_worst_ocv_cppr_ps"] or 0))
        intra = []
        for part, ts in by_part.items():
            pr = [pair(x, y) for i, x in enumerate(ts) for y in ts[i + 1:]]
            if not pr:
                continue
            w = max(pr, key=lambda r: r["ocv_cppr"])
            intra.append(dict(part=part, taps=len(ts), leaves=len(set(t["leaf"] for t in ts)),
                              spread_ps=round(max(tin[t["id"]] for t in ts) - min(tin[t["id"]] for t in ts), 2),
                              worst_ocv_cppr_ps=round(w["ocv_cppr"], 2), worst_lca_level=w["lca_level"]))
        intra.sort(key=lambda r: -r["worst_ocv_cppr_ps"])
        hs = [Sl[p] for p in Sl if p.startswith(("ht_", "hb_", "rp_", "lf_"))]
        ls = [Sl[p] for p in Sl if p.startswith(("ch_", "tb_"))]
        viol = (d / f"viol_{c}.rpt").read_text(errors="replace") if (d / f"viol_{c}.rpt").exists() else ""
        out["corners"][c] = dict(
            sta_done="OT_STA_DONE" in sta_logs[c], missing_pins=len(miss),
            root_to_leaf_driver_in=stats(v for v in lin.values() if v is not None),
            root_to_tap=stats(v for v in tin.values() if v is not None),
            leaf_to_tap_local=stats(loc), local_imbalance_within_leaf_ps=round(leaf_imb, 2),
            htree_leaf_skew_ps=stats(v for v in lin.values() if v is not None)["spread"],
            global_tap_skew_ps=stats(v for v in tin.values() if v is not None)["spread"],
            max_slew_htree_ps=round(max(hs), 1) if hs else None, max_slew_local_ps=round(max(ls), 1) if ls else None,
            slew_cap_violations=len(re.findall(r"\(VIOLATED\)", viol)),
            seam_pairs=len(seams), seam_worst=seams[:10],
            intra_partition_worst=intra[:8], intra_partition_max_spread_ps=max(r["spread_ps"] for r in intra),
            intra_partitions_split_above_leaf=sum(1 for r in intra if r["worst_lca_level"] < 8),
            intra_partitions_ocv_cppr_le_80=sum(1 for r in intra if r["worst_ocv_cppr_ps"] <= 80),
            intra_partitions=len(intra),
            seam_max_skew_ps=max((r["max_skew_ps"] for r in seams), default=None),
            seam_max_ocv_cppr_ps=max((r["worst_ocv_cppr_ps"] for r in seams), default=None),
            seam_max_ocv_nocppr_ps=max((r["worst_ocv_nocppr_ps"] for r in seams), default=None),
            face_seam_max_skew_ps=max((r["face_max_skew_ps"] or 0 for r in seams), default=None),
            face_seam_max_ocv_cppr_ps=max((r["face_worst_ocv_cppr_ps"] or 0 for r in seams), default=None),
            face_seam_max_ocv_nocppr_ps=max((r["face_worst_ocv_nocppr_ps"] or 0 for r in seams), default=None),
            face_seam_min_ocv_cppr_ps=min((r["face_worst_ocv_cppr_ps"] for r in seams if r["face_worst_ocv_cppr_ps"]), default=None),
            face_seams_by_lca_level={str(l): dict(pairs=len(g), max_skew_ps=max(r["face_max_skew_ps"] for r in g),
                                                  max_ocv_cppr_ps=max(r["face_worst_ocv_cppr_ps"] for r in g),
                                                  min_ocv_cppr_ps=min(r["face_worst_ocv_cppr_ps"] for r in g))
                                     for l, g in sorted(_group(seams, "face_lca_level").items())},
            face_seams_pass_80ps_with_ocv=sum(1 for r in seams if r["face_worst_ocv_cppr_ps"] is not None
                                              and r["face_worst_ocv_cppr_ps"] <= 80),
            face_seams_pass_80ps_no_ocv=sum(1 for r in seams if r["face_max_skew_ps"] is not None
                                            and r["face_max_skew_ps"] <= 80))
        out.setdefault("seams_all", {})[c] = seams
        lc, pm = defaultdict(dict), defaultdict(list)
        for t in taps:
            lc[t["part"]][t["name"]] = round(tin[t["id"]], 2)
            pm[t["part"]].append(tin[t["id"]])
        lat["corners"][c] = dict(lc)
        lat["partition_mean"][c] = {p: round(sum(v) / len(v), 2) for p, v in pm.items()}
    (res / "htree_clock.json").write_text(json.dumps(out, indent=1) + "\n")
    lat["note"] = ("die H-tree insertion root(clk port) -> partition clock tap pin (tap buffer input) in ps, per corner, "
                   "GRT parasitics (estimate_parasitics -global_routing); apply as source latency of each tap")
    (res / "tap_latency.json").write_text(json.dumps(lat, indent=1) + "\n")
    return out


def render(d, plan, res):
    """PNG renders for the visual review: (1) the built tree, (2) tap-latency heat maps SS / FF with worst seams."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    d, res = Path(d), Path(res)
    P = S.Plan(S.load(plan))
    meta = json.loads((d / "meta.json").read_text())
    rep = json.loads((res / "htree_clock.json").read_text())
    nodes = {int(k): v for k, v in meta["nodes"].items()}
    cells = {}
    for ln in (d / "place.tcl").read_text().splitlines():
        p = ln.split()
        cells[p[2]] = (float(p[4].strip("{")), float(p[5].strip("}")))

    def outlines(ax):
        for n in P.parts:
            x0, y0, x1, y1 = P.rect(n)
            hard = P.ptype(n).get("hard")
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#e4e4e4" if hard else "#f7f7f7", ec="#999", lw=0.5))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, n, ha="center", va="center", fontsize=4, color="#777")
        ax.set_xlim(-200, P.W + 200)
        ax.set_ylim(-200, P.H + 200)
        ax.set_aspect("equal")
    fig, ax = plt.subplots(figsize=(15, 15 * P.H / P.W + 0.8))
    outlines(ax)
    cmap = plt.get_cmap("viridis")
    maxl = max(n["level"] for n in nodes.values())
    taps = meta["taps"]
    for t in taps:
        lx, ly = nodes[t["leaf"]]["xy"]
        ax.plot([lx, t["xy"][0]], [ly, t["xy"][1]], color="#e67e22", lw=0.3, alpha=0.6)
    for i, n in nodes.items():
        if n["parent"] is None or n["parent"] not in nodes:
            continue
        (x0, y0), (x1, y1) = nodes[n["parent"]]["xy"], n["xy"]
        ax.plot([x0, x1], [y0, y1], color=cmap((n["level"] - 1) / max(maxl - 1, 1)), lw=3.0 - 2.2 * (n["level"] - 1) / maxl,
                solid_capstyle="butt")
    rx = [v for k, v in cells.items() if k.startswith(("rp_", "hb_"))]
    ax.scatter([v[0] for v in rx], [v[1] for v in rx], s=2, c="k", zorder=4, label=f"H-tree buffers ({len(rx)})")
    lf = [v for k, v in cells.items() if k.startswith("lf_")]
    ax.scatter([v[0] for v in lf], [v[1] for v in lf], s=14, marker="s", c="#c0392b", zorder=5, label=f"leaf drivers ({len(lf)})")
    ax.scatter([t["xy"][0] for t in taps], [t["xy"][1] for t in taps], s=3, c="#2471a3", zorder=5,
               label=f"partition taps ({len(taps)})")
    ax.plot([], [], color="#e67e22", lw=1, label="local net leaf->tap (straight line; built as length-matched chain)")
    for l in range(1, maxl + 1):
        ax.plot([], [], color=cmap((l - 1) / max(maxl - 1, 1)), lw=2, label=f"level {l}")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.04), fontsize=6, framealpha=0.9, ncol=4)
    ax.set_title(f"{P.name}: built die H-tree (OpenROAD case {d.name}), M8 H / M9 V, NDR 2W2S", fontsize=9)
    fig.savefig(res / "htree_built.png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    lat = json.loads((res / "tap_latency.json").read_text())
    cs = [c for c in ("SS", "FF") if c in lat["corners"]]
    fig, axs = plt.subplots(len(cs), 1, figsize=(13, len(cs) * (13 * P.H / P.W + 0.8)))
    axs = [axs] if len(cs) == 1 else axs
    cent = {n: ((P.rect(n)[0] + P.rect(n)[2]) / 2, (P.rect(n)[1] + P.rect(n)[3]) / 2) for n in P.parts}
    for ax, c in zip(axs, cs):
        outlines(ax)
        v = [lat["corners"][c][t["part"]][t["name"]] for t in taps]
        sc = ax.scatter([t["xy"][0] for t in taps], [t["xy"][1] for t in taps], c=v, s=9, cmap="plasma", zorder=5)
        cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01)
        cb.set_label(f"{c} root->tap insertion (ps)", fontsize=7)
        seams = sorted(rep["seams_all"][c], key=lambda r: -(r["face_max_skew_ps"] or 0))[:6]
        for r in seams:
            (xa, ya), (xb, yb) = cent[r["a"]], cent[r["b"]]
            ax.plot([xa, xb], [ya, yb], color="r", lw=1.2, zorder=6)
            ax.text((xa + xb) / 2, (ya + yb) / 2, f"{r['face_max_skew_ps']:.0f} / {r['face_worst_ocv_cppr_ps']:.0f}",
                    fontsize=5.5, color="r", zorder=7, ha="center", bbox=dict(fc="w", ec="none", alpha=0.7, pad=0.5))
        st = rep["corners"][c]["root_to_tap"]
        ax.set_title(f"{c}: tap insertion {st['min']:.0f}..{st['max']:.0f} ps (spread {st['spread']:.0f}); red = 6 worst seam pairs "
                     "(facing taps): |skew| / |skew| + 5% OCV on the non-common path after CPPR (ps)", fontsize=8)
    fig.savefig(res / "tap_latency_heatmap.png", dpi=85, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("plan")
    g.add_argument("htree")
    g.add_argument("--out", required=True)
    g.add_argument("--scope", default="full", choices=["full", "rib"])
    g.add_argument("--rep-um", type=float, default=400.0)
    g.add_argument("--local-rep-um", type=float, default=300.0)
    g.add_argument("--taps-cache")
    g.add_argument("--mem", type=int, default=96)
    g.add_argument("--cpus", type=int, default=8)
    g.add_argument("--no-local-match", action="store_true")
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--plan", required=True)
    r.add_argument("--res", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "gen":
        P = S.Plan(S.load(a.plan))
        H = json.load(open(a.htree))
        m = gen(P, H, a.out, a.scope, a.rep_um, a.local_rep_um, a.taps_cache, a.mem, a.cpus, not a.no_local_match)
        print(json.dumps({k: v for k, v in m.items() if k not in ("nodes", "taps")}))
    else:
        o = report(a.dir, a.plan, a.res)
        render(a.dir, a.plan, a.res)
        print(json.dumps({k: v for k, v in o.items() if k not in ("seams_all",)}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
