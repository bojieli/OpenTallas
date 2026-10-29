#!/usr/bin/env python3
"""QC-MESH-PILOT-1 (2026-10-28): one A0-quad region clock mesh, pilot only (die-local; no shared tool changed, so the
default flow is byte-identical by construction).  Basis: QC-MESH-EST-1 ESTIMATE.md (claude/qc-mesh-est-1-1028@3875bae535)
on plan ev_qc23pg (DIE-QC-23, claude/die-qc23-pg-1028@520b88330) and the trial14 tap map.

Form (c_* A0 quad partition, MX orient; 4 A0 hard cores, glue = edge strips + centre channel + middle band):
  * pre-mesh tree, equal legs BY CONSTRUCTION (no balance detours): R (region root, centre channel x middle band)
    -> A x2 (middle band, half way to the column pairs) -> B x4 (column x middle band) -> rep x8 (+-p) ->
    C x8 (+-2p) -> D x16 (+-p) -> 32 BUFx24 mesh drivers at y = ymid +-p/2, 3p/2, 5p/2, 7p/2 on the 4 glue columns
    (p = 360 um ~ the 374-um tap-row pitch, so every tap row sits 138-194 um from its nearest drivers).
    Every cell sits in glue (columns = the glue tap columns; checked against the hard-core rects).  Legs <= 450 um.
  * mesh: M9 4W (0.16 um) vertical strap per glue column, M8 4W horizontal strap per tap row (7), all in the
    centre of a 4.32-um M8/M9 PG gap; VIA89 at all 28 crossings; one special net ck_mesh.
  * 28 glue taps = mesh loads (dummy BUFx4f at the tap; declared port load 2.3 fF in the MC).
  * 4 early A0 core taps stay OFF the mesh: E0 (root) -> E1 x2 (centre channel at the core-tap rows) -> core taps.
usage: qc_mesh_pilot.py build PLAN TREE_JSON PART OUT_DIR [--adjust 0.4]
       qc_mesh_pilot.py rec OUT_DIR TREE_TXT_DIR REC_JSON      (explicit_mesh_signoff rec schema; mult-1 drivers)
"""
import json
import math
import sys
from pathlib import Path

PITCH_PG = 4.32
SITE_W, ROW_H = 0.054, 0.27
DBU = 1000
STRAP_W = 0.16          # 4W (min width 0.04)
PG_W = {"M8": 0.48, "M9": 0.672}     # ev_qc23pg: M9 0.672 (QC-PG-5), M8 0.48


def snap_gap(v):
    """centre of the nearest PG gap (PG stripe centres at 4.32 k in the partition frame)."""
    return round((math.floor(v / PITCH_PG) * PITCH_PG + PITCH_PG / 2), 4)


def part_geom(plan, part):
    P = json.load(open(plan))
    pa = {p["name"]: p for p in P["partitions"]}[part]
    T = P["partition_types"][pa["type"]]
    W, H = T["outline_um"]
    cores = []
    for c in T["contents"]:
        if "outline_um" in c and "origin_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            if pa["orient"] == "MX":
                y = H - y - h
            elif pa["orient"] != "R0":
                raise SystemExit(f"orient {pa['orient']} not handled")
            cores.append(dict(inst=c["inst"], rect=[round(x, 4), round(y, 4), round(x + w, 4), round(y + h, 4)]))
    return pa, T, W, H, cores


def in_core(x, y, cores, m=0.0):
    return any(r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m for r in (c["rect"] for c in cores))


def build(plan, tree_json, part, out, adjust=0.4, pitch=360.0):
    pa, T, W, H, cores = part_geom(plan, part)
    ox, oy = pa["origin_um"]
    tj = json.load(open(tree_json))
    taps = [t for t in tj["taps"] if t["part"] == part]
    glue = [dict(t, lx=round(t["xy"][0] - ox, 4), ly=round(t["xy"][1] - oy, 4)) for t in taps if not t["tap"].startswith("clk_c")]
    core = [dict(t, lx=round(t["xy"][0] - ox, 4), ly=round(t["xy"][1] - oy, 4)) for t in taps if t["tap"].startswith("clk_c")]
    rows = sorted({g["ly"] for g in glue})
    ymid = rows[len(rows) // 2]
    cols = sorted({g["lx"] for g in glue if g["ly"] != ymid})
    assert len(cols) == 4 and len(rows) == 7, (cols, rows)
    rx = (cols[1] + cols[2]) / 2
    cells, nets = {}, {}

    def cell(name, x, y, master="BUFx24_ASAP7_75t_R"):
        assert not in_core(x, y, cores, 0.5), f"{name} at ({x:.1f},{y:.1f}) lands on a hard core"
        cells[name] = dict(master=master, x=x, y=y)

    def net(name, drv, loads, kind="tree"):
        nets[name] = dict(drv=drv, loads=loads, kind=kind)
    cell("R", rx, ymid)
    net("n_root", "port:root", ["R"])
    A = {"L": (cols[0] + cols[1]) / 2, "R": (cols[2] + cols[3]) / 2}
    for s, x in A.items():
        cell(f"A{s}", x, ymid)
    net("n_R", "R", ["AL", "AR"])
    for i, x in enumerate(cols):
        cell(f"B{i}", x, ymid)
    net("n_AL", "AL", ["B0", "B1"]); net("n_AR", "AR", ["B2", "B3"])
    drivers = []
    for i, x in enumerate(cols):
        xs = x + (2.0 if i in (0, 2) else -2.0)       # keep the trunk cells inside the glue strip/channel
        for sgn, s in ((1, "u"), (-1, "d")):
            cell(f"P{i}{s}", xs, ymid + sgn * pitch)        # repeater on the 2p leg (<= 450 um rule)
            cell(f"C{i}{s}", x, ymid + sgn * 2 * pitch)
            Cn = f"C{i}{s}"
            for sg2, s2 in ((1, "u"), (-1, "d")):
                Dn = f"D{i}{s}{s2}"
                cell(Dn, xs, ymid + sgn * 2 * pitch + sg2 * pitch)
                ds = []
                for sg3, s3 in ((1, "u"), (-1, "d")):
                    dn = f"M{i}{s}{s2}{s3}"
                    cell(dn, x, ymid + sgn * 2 * pitch + sg2 * pitch + sg3 * pitch / 2)
                    drivers.append(dn); ds.append(dn)
                net(f"n_{Dn}", Dn, ds)
            net(f"n_{Cn}", Cn, [f"D{i}{s}u", f"D{i}{s}d"])
            net(f"n_P{i}{s}", f"P{i}{s}", [Cn])
        net(f"n_B{i}", f"B{i}", [f"P{i}u", f"P{i}d"])
    # early core-tap branch (off mesh), equal legs by construction: E0 in the centre channel at the y midpoint of the two
    # core-tap rows (fed from the region root port), repeaters Q at the leg midpoints (<= 450 um), E1 at each core-tap row
    ey = sorted({c["ly"] for c in core})
    assert len(ey) == 2, ey
    em = (ey[0] + ey[1]) / 2
    cell("E0", rx, em)
    net("n_root", "port:root", ["R", "E0"])
    e1, qs = [], []
    for j, y in enumerate(ey):
        cell(f"Q{j}", rx + 2.0, (em + y) / 2); qs.append(f"Q{j}")
        cell(f"E1_{j}", rx, y); e1.append(f"E1_{j}")
        net(f"n_Q{j}", f"Q{j}", [f"E1_{j}"])
        loads = []
        for c in core:
            if c["ly"] == y:
                n = "L_" + c["tap"]
                x = c["lx"]       # the core clock pin is on the core edge: its load cell sits just outside, in the channel
                for r in (q["rect"] for q in cores):
                    if r[0] - 0.6 <= x <= r[2] + 0.6 and r[1] <= c["ly"] <= r[3]:
                        x = r[2] + 0.6 if abs(x - r[2]) < abs(x - r[0]) else r[0] - 1.1
                cell(n, x, c["ly"], "BUFx4f_ASAP7_75t_R"); loads.append(n)
        net(f"n_E1_{j}", f"E1_{j}", loads)
    net("n_E0", "E0", qs)
    # mesh
    vx = {i: snap_gap(x) for i, x in enumerate(cols)}
    hy = {y: snap_gap(y) for y in rows}
    ylo = min(min(rows), min(cells[d]["y"] for d in drivers)) - 2
    yhi = max(max(rows), max(cells[d]["y"] for d in drivers)) + 2
    xlo, xhi = min(vx.values()), max(vx.values())
    mesh_loads = []
    for g in glue:
        n = "L_" + g["tap"]; cell(n, g["lx"], g["ly"], "BUFx4f_ASAP7_75t_R"); mesh_loads.append(n)
    for d in drivers:      # put the driver centre under its strap
        i = int(d[1]); cells[d]["x"] = vx[i]
    net("ck_mesh", drivers, mesh_loads, kind="mesh")
    wid = {"BUFx24_ASAP7_75t_R": 1.62, "BUFx4f_ASAP7_75t_R": 0.432}
    for c in cells.values():          # centre -> lower-left on the site grid; legalize overlaps (shift right)
        c["x"] = round(round((c["x"] - wid[c["master"]] / 2) / SITE_W) * SITE_W, 4)
        c["y"] = round(round((c["y"]) / ROW_H) * ROW_H, 4)
    occ = {}
    for n in sorted(cells):
        c = cells[n]
        while any(abs(c["y"] - o["y"]) < 1e-6 and c["x"] < o["x"] + wid[o["master"]] and o["x"] < c["x"] + wid[c["master"]]
                  for o in occ.values()):
            c["x"] = round(c["x"] + SITE_W * 2, 4)
        assert not in_core(c["x"], c["y"], cores, 0.0) and not in_core(c["x"] + wid[c["master"]], c["y"], cores, 0.0), n
        occ[n] = c
    geom = dict(part=part, origin=[ox, oy], W=W, H=H, cores=cores, cols=cols, rows=rows, ymid=ymid, root=[rx, ymid],
                vx=[vx[i] for i in range(4)], hy=[hy[y] for y in rows], y_span=[ylo, yhi], x_span=[xlo, xhi],
                drivers=drivers, mesh_loads=mesh_loads, glue_taps=[g["port"] for g in glue],
                core_taps=[c["port"] for c in core], adjust=adjust, driver_pitch_um=pitch,
                tap_xy={("L_" + g["tap"]): [g["lx"], g["ly"]] for g in glue + core})
    o = Path(out); o.mkdir(parents=True, exist_ok=True)
    json.dump(dict(geom=geom, cells=cells, nets=nets), open(o / "pilot.json", "w"), indent=1)
    write_def(o, geom, cells, nets)
    write_tcl(o, geom)
    print(part, "cells", len(cells), "drivers", len(drivers), "nets", len(nets), "cols", cols, "rows", rows, "root", geom["root"])


def write_def(o, g, cells, nets):
    W, H = g["W"], g["H"]
    u = lambda v: int(round(v * DBU))
    L = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN pilot ;", f"UNITS DISTANCE MICRONS {DBU} ;",
         f"DIEAREA ( 0 0 ) ( {u(W)} {u(H)} ) ;"]
    nrow, nsite = int(H / ROW_H), int(W / SITE_W)
    for r in range(nrow):
        L.append(f"ROW ROW_{r} asap7sc7p5t 0 {u(r * ROW_H)} {'N' if r % 2 == 0 else 'FS'} DO {nsite} BY 1 STEP {u(SITE_W)} 0 ;")
    L.append(f"COMPONENTS {len(cells)} ;")
    for n, c in sorted(cells.items()):
        r = int(round(c["y"] / ROW_H))
        L.append(f"- {n} {c['master']} + FIXED ( {u(c['x'])} {u(c['y'])} ) {'N' if r % 2 == 0 else 'FS'} ;")
    L.append("END COMPONENTS")
    rx, ry = g["root"]
    L += ["PINS 1 ;", f"- root + NET n_root + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -40 -40 ) ( 40 40 ) + FIXED ( {u(snap_gap(rx) + 0.04)} {u(ry)} ) N ;",
          "END PINS"]
    # blockages: hard cores own M1-M7 and placement
    blk = []
    for c in g["cores"]:
        x0, y0, x1, y1 = (u(v) for v in c["rect"])
        for lay in ("M1", "M2", "M3", "M4", "M5", "M6", "M7"):
            blk.append(f"- LAYER {lay} RECT ( {x0} {y0} ) ( {x1} {y1} ) ;")
        blk.append(f"- PLACEMENT RECT ( {x0} {y0} ) ( {x1} {y1} ) ;")
    # die clock on M8/M9 only (12.1a: M1-M7 belong to the partition): M2-M7 blocked everywhere except a +-3 um pin-access
    # window around each clock cell (y-slabs between windows, x-gaps inside a slab)
    win = sorted((u(c["x"] - 3), u(c["y"] - 3), u(c["x"] + 4.7), u(c["y"] + 3.3)) for c in cells.values())
    ys = sorted({0, u(H)} | {w[1] for w in win} | {w[3] for w in win})
    for ya, yb in zip(ys, ys[1:]):
        xs = sorted((w[0], w[2]) for w in win if w[1] < yb and w[3] > ya)
        free, x = [], 0
        for a, b in xs:
            if a > x:
                free.append((x, a))
            x = max(x, b)
        if x < u(W):
            free.append((x, u(W)))
        for xa, xb in free:
            for lay in ("M2", "M3", "M4", "M5", "M6", "M7"):
                blk.append(f"- LAYER {lay} RECT ( {xa} {ya} ) ( {xb} {yb} ) ;")
    L += [f"BLOCKAGES {len(blk)} ;"] + blk + ["END BLOCKAGES"]
    # special nets: PG M8/M9 stripes (alternate VDD/VSS) + mesh
    pg = {"VDD": [], "VSS": []}
    k = 0
    while k * PITCH_PG <= H:
        y = k * PITCH_PG
        if 0 < y < H:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW M8 {u(PG_W['M8'])} + SHAPE STRIPE ( 0 {u(y)} ) ( {u(W)} {u(y)} )")
        k += 1
    k = 0
    while k * PITCH_PG <= W:
        x = k * PITCH_PG
        if 0 < x < W:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW M9 {u(PG_W['M9'])} + SHAPE STRIPE ( {u(x)} 0 ) ( {u(x)} {u(H)} )")
        k += 1
    sn = []
    for nn, segs in pg.items():
        segs[0] = segs[0].replace("NEW ", "", 1)
        sn.append(f"- {nn} + ROUTED " + "\n    ".join(segs) + f" + USE {'POWER' if nn == 'VDD' else 'GROUND'} ;")
    m = nets["ck_mesh"]
    conn = " ".join(f"( {d} Y )" for d in m["drv"]) + " " + " ".join(f"( {l} A )" for l in m["loads"])
    ms = []
    y0, y1 = g["y_span"]
    for x in g["vx"]:
        ms.append(f"M9 {u(STRAP_W)} + SHAPE STRIPE ( {u(x)} {u(y0)} ) ( {u(x)} {u(y1)} )")
    x0, x1 = g["x_span"]
    for y in g["hy"]:
        ms.append(f"M8 {u(STRAP_W)} + SHAPE STRIPE ( {u(x0)} {u(y)} ) ( {u(x1)} {u(y)} )")
        for x in g["vx"]:
            ms.append(f"M8 0 + SHAPE STRIPE ( {u(x)} {u(y)} ) VIA89")
    sn.append(f"- ck_mesh {conn} + ROUTED " + "\n    NEW ".join(ms) + " + USE CLOCK ;")
    L += [f"SPECIALNETS {len(sn)} ;"] + sn + ["END SPECIALNETS"]
    reg = [(n, v) for n, v in nets.items() if v["kind"] == "tree"]
    L.append(f"NETS {len(reg)} ;")
    for n, v in reg:
        d = "( PIN root )" if v["drv"] == "port:root" else f"( {v['drv']} Y )"
        L.append(f"- {n} {d} " + " ".join(f"( {l} A )" for l in v["loads"]) + " + USE CLOCK ;")
    L += ["END NETS", "END DESIGN"]
    (o / "pilot.def").write_text("\n".join(L) + "\n")


TCL = r"""
set t0 [clock seconds]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
create_clock -name dck -period 833.0 [get_ports root]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 $::env(ADJ)
set_global_routing_layer_adjustment M9 $::env(ADJ)
# die clock on M8/M9 only (12.1a: M1-M7 belong to the partition/cores); M2-M7 only for the pin stacks
foreach L {M2 M3 M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.99 }
create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
foreach n [get_nets n_*] { assign_ndr -ndr CK2W2S -net [get_full_name $n] }
global_route -congestion_iterations 50 -allow_congestion -verbose
write_guides /o/route.guide
proc dump {tag corner} {
  set fh [open /o/tree_${tag}_${corner}.txt w]
  foreach c [get_cells *] {
    set n [get_full_name $c]
    if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
    foreach pn $pins {
      set p [get_pins $n/$pn]
      puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
    }
  }
  close $fh
}
proc timing {} {
  create_clock -name vclk -period 833.0
  set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
  set_input_delay 0 -clock vclk [get_ports root]
  foreach c [get_cells M*] { set_disable_timing $c }
}
source $P/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
timing
dump grt TT
puts "OT_T grt [expr {[clock seconds]-$t0}]"
detailed_route -output_drc /o/drc.rpt -verbose 0
puts "OT_T drt [expr {[clock seconds]-$t0}]"
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /o/drt.spef
dump drt TT
write_db /o/drt.odb
write_def /o/drt.def
puts "OT_DONE [expr {[clock seconds]-$t0}]"
"""

TCL_FF = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $::env(LIBDIR)/*RVT_FF_nldm*.lib*] { read_liberty $f }
read_db /o/drt.odb
read_spef /o/drt.spef
create_clock -name vclk -period 833.0
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
foreach c [get_cells M*] { set_disable_timing $c }
set fh [open /o/tree_drt_FF.txt w]
foreach c [get_cells *] {
  set n [get_full_name $c]
  if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
  foreach pn $pins {
    set p [get_pins $n/$pn]
    puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
  }
}
close $fh
puts OT_FF_DONE
"""


def write_tcl(o, g):
    (o / "run.tcl").write_text(TCL)
    (o / "run_ff.tcl").write_text(TCL_FF)
    (o / "run.sh").write_text(f"""#!/bin/bash
O=$(cd $(dirname $0) && pwd)
docker run --rm --name qcmp-$(basename $O)-$$ --memory=64g --memory-swap=64g --cpus=16 -e ADJ={g['adjust']} -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/o openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -threads 16 -exit /o/run.tcl > /o/run.log 2>&1; rc=$?; echo "EXIT $rc" >> /o/run.log
[ $rc = 0 ] && {{ openroad -no_init -exit /o/run_ff.tcl > /o/run_ff.log 2>&1; echo "EXIT $?" >> /o/run_ff.log; }}
chown -R {_uid()} /o'
""")


def _uid():
    import os
    return f"{os.getuid()}:{os.getgid()}"


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        adj = float(a[a.index("--adjust") + 1]) if "--adjust" in a else 0.4
        build(a[1], a[2], a[3], a[4], adj, float(a[a.index("--pitch") + 1]) if "--pitch" in a else 360.0)
    else:
        raise SystemExit(__doc__)
