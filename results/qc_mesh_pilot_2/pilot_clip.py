#!/usr/bin/env python3
"""QC-MESH-PILOT-2 (2026-10-28): detailed-route (DRT) proof of the QC-MESH-PILOT-1 A0-quad region mesh by CLIPS.
The full 3.23-mm2 region sat > 45 min (twice) in DRT "Init gr pin query"; per the lane brief the region is routed as
slices instead and the routed arrivals are COMPOSED analytically (AGENTS: simulate the minimum component):
  mid  = middle band, full width: root port -> R -> A x2 -> B x4 inputs (+ n_root -> E0)
  c0..c3 = one tap column strip each (+-80 um around the M9 strap), full height: B_i -> P -> C -> D -> 8 mesh drivers
  core = centre channel strip: E0 -> Q -> E1 -> A0 core-tap loads (off-mesh branch)
Every clip carries the mesh straps inside it as FIXED 4W wiring of a REGULAR net (NDR CK4W), so DRT must route each
driver Y / tap A pin stack onto the strap (pin-stack DRC is part of the proof).  Clip entry cells get an M9 port at
the nearest PG gap (the incoming M9 leg's stack).  Clip rects are snapped to 8.64 um so all track/site grids align.
usage: pilot_clip.py build TRIAL_DIR CLIP OUT_DIR ADJ        (TRIAL_DIR = a QC-MESH-PILOT-1 trial: pilot.json, tree_grt_TT.txt)
       pilot_clip.py compose TRIAL_DIR CLIPROOT STAGE CORNER OUT_TREE   (STAGE grt|drt; CLIPROOT/<clip>/tree_STAGE_CORNER.txt)
       pilot_clip.py merge CLIPROOT OUT_DIR      -> OUT_DIR/drt.def (all clip NETS, for pilot_render.py), drc.rpt (all clips),
                                                    drc_summary.json (per clip; markers within 3 um of a clip entry port =
                                                    clip-harness artifacts, the real entry is the incoming M8/M9 leg)
Every number UNCHECKED until NUMBER-CHECK."""
import json
import math
import sys
from pathlib import Path

PITCH_PG = 4.32
SITE_W, ROW_H = 0.054, 0.27
DBU = 1000
STRAP_W = 0.16
PG_W = {"M8": 0.48, "M9": 0.672}
G = 8.64
CLIPS = ["mid", "c0", "c1", "c2", "c3", "core"]
u = lambda v: int(round(v * DBU))
WID = {"BUFx24_ASAP7_75t_R": 1.62, "BUFx4f_ASAP7_75t_R": 0.432}


def snap_gap(v):
    return round((math.floor(v / PITCH_PG) * PITCH_PG + PITCH_PG / 2), 4)


def read_tree(p):
    t = {}
    for ln in open(p):
        f = ln.split()
        if len(f) < 5:
            continue
        try:
            t.setdefault(f[1], {})[f[0]] = tuple(float(x) for x in f[2:5])
        except ValueError:
            continue
    return t


def clip_spec(J, clip):
    g, cells, nets = J["geom"], J["cells"], J["nets"]
    W, H = g["W"], g["H"]
    dn = lambda v: max(0.0, math.floor(v / G) * G)
    up = lambda v, M: min(M, math.ceil(v / G) * G)
    if clip == "mid":
        y0 = min(cells["R"]["y"], cells["E0"]["y"], g["ymid"]) - 40
        rect = [0.0, dn(y0), W, up(g["ymid"] + 60, H)]
        nn = ["n_root", "n_R", "n_AL", "n_AR"]
        entry = None
    elif clip == "core":
        rx = g["root"][0]
        rect = [dn(rx - 90), 0.0, up(rx + 90, W), H]
        nn = ["n_E0"] + [n for n in nets if n.startswith(("n_Q", "n_E1"))]
        entry = "E0"
    else:
        i = int(clip[1])
        x = g["vx"][i]
        rect = [dn(x - 80), 0.0, up(x + 80, W), H]
        nn = [n for n in nets if n == f"n_B{i}" or n.startswith((f"n_P{i}", f"n_C{i}", f"n_D{i}"))]
        entry = f"B{i}"
    return rect, nn, entry


def inside(rect, x, y, w=0.0):
    return rect[0] <= x and x + w <= rect[2] and rect[1] <= y and y + ROW_H <= rect[3]


def build(trial, clip, out, adj):
    T = Path(trial)
    J = json.load(open(T / "pilot.json"))
    g, cells, nets = J["geom"], J["cells"], J["nets"]
    rect, nn, entry = clip_spec(J, clip)
    sel = {}
    for n in nn:
        v = nets[n]
        ld = [l for l in v["loads"]]
        if clip == "mid" and n == "n_root":
            ld = ["R", "E0"]
        sel[n] = dict(drv=v["drv"], loads=ld)
    if entry:
        sel["n_in"] = dict(drv="port:root", loads=[entry])
    used = set()
    for v in sel.values():
        if v["drv"] != "port:root":
            used.add(v["drv"])
        used |= set(v["loads"])
    # mesh inside the rect
    mdrv = [d for d in g["drivers"] if inside(rect, cells[d]["x"], cells[d]["y"], WID[cells[d]["master"]])]
    mtap = [l for l in g["mesh_loads"] if inside(rect, cells[l]["x"], cells[l]["y"], WID[cells[l]["master"]])]
    used |= set(mdrv) | set(mtap)
    for c in used:
        assert inside(rect, cells[c]["x"], cells[c]["y"], WID[cells[c]["master"]]), (clip, c, cells[c], rect)
    # entry port position: the region root port for mid, else an M9 stack at the entry cell (nearest PG gap)
    if entry:
        px, py = snap_gap(cells[entry]["x"] + WID[cells[entry]["master"]] / 2) + 0.04, cells[entry]["y"]
    else:
        px, py = snap_gap(g["root"][0]) + 0.04, g["root"][1]
    X0, Y0, X1, Y1 = rect
    L = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN pilot ;", f"UNITS DISTANCE MICRONS {DBU} ;",
         f"DIEAREA ( {u(X0)} {u(Y0)} ) ( {u(X1)} {u(Y1)} ) ;"]
    r0, r1 = int(round(Y0 / ROW_H)), int(round(Y1 / ROW_H))
    nsite = int(round((X1 - X0) / SITE_W))
    for r in range(r0, r1):
        L.append(f"ROW ROW_{r} asap7sc7p5t {u(X0)} {u(r * ROW_H)} {'N' if r % 2 == 0 else 'FS'} DO {nsite} BY 1 STEP {u(SITE_W)} 0 ;")
    L.append(f"COMPONENTS {len(used)} ;")
    for n in sorted(used):
        c = cells[n]
        r = int(round(c["y"] / ROW_H))
        L.append(f"- {n} {c['master']} + FIXED ( {u(c['x'])} {u(c['y'])} ) {'N' if r % 2 == 0 else 'FS'} ;")
    L.append("END COMPONENTS")
    L += ["PINS 1 ;", f"- root + NET {'n_in' if entry else 'n_root'} + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -40 -40 ) ( 40 40 ) "
          f"+ FIXED ( {u(px)} {u(py)} ) N ;", "END PINS"]
    cr = lambda a: [max(a[0], X0), max(a[1], Y0), min(a[2], X1), min(a[3], Y1)]
    blk = []
    for c in g["cores"]:
        x0, y0, x1, y1 = cr(c["rect"])
        if x0 >= x1 or y0 >= y1:
            continue
        for lay in ("M1", "M2", "M3", "M4", "M5", "M6", "M7"):
            blk.append(f"- LAYER {lay} RECT ( {u(x0)} {u(y0)} ) ( {u(x1)} {u(y1)} ) ;")
        blk.append(f"- PLACEMENT RECT ( {u(x0)} {u(y0)} ) ( {u(x1)} {u(y1)} ) ;")
    win = sorted(tuple(u(v) for v in cr([cells[c]["x"] - 3, cells[c]["y"] - 3, cells[c]["x"] + 4.7, cells[c]["y"] + 3.3])) for c in used)
    win.append(tuple(u(v) for v in cr([px - 3, py - 3, px + 3, py + 3])))
    ys = sorted({u(Y0), u(Y1)} | {w[1] for w in win} | {w[3] for w in win})
    for ya, yb in zip(ys, ys[1:]):
        xs = sorted((w[0], w[2]) for w in win if w[1] < yb and w[3] > ya)
        free, x = [], u(X0)
        for a, b in xs:
            if a > x:
                free.append((x, a))
            x = max(x, b)
        if x < u(X1):
            free.append((x, u(X1)))
        for xa, xb in free:
            for lay in ("M2", "M3", "M4", "M5", "M6", "M7"):
                blk.append(f"- LAYER {lay} RECT ( {xa} {ya} ) ( {xb} {yb} ) ;")
    L += [f"BLOCKAGES {len(blk)} ;"] + blk + ["END BLOCKAGES"]
    pg = {"VDD": [], "VSS": []}
    k = 0
    while k * PITCH_PG <= g["H"]:
        y = k * PITCH_PG
        if Y0 < y < Y1:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW M8 {u(PG_W['M8'])} + SHAPE STRIPE ( {u(X0)} {u(y)} ) ( {u(X1)} {u(y)} )")
        k += 1
    k = 0
    while k * PITCH_PG <= g["W"]:
        x = k * PITCH_PG
        if X0 < x < X1:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW M9 {u(PG_W['M9'])} + SHAPE STRIPE ( {u(x)} {u(Y0)} ) ( {u(x)} {u(Y1)} )")
        k += 1
    sn = []
    for nm, segs in pg.items():
        if not segs:
            continue
        segs[0] = segs[0].replace("NEW ", "", 1)
        sn.append(f"- {nm} + ROUTED " + "\n    ".join(segs) + f" + USE {'POWER' if nm == 'VDD' else 'GROUND'} ;")
    L += [f"SPECIALNETS {len(sn)} ;"] + sn + ["END SPECIALNETS"]
    # mesh straps inside the rect as FIXED wiring of a regular net (4W NDR) so DRT routes the pin stacks onto them
    y0, y1 = max(g["y_span"][0], Y0 + 0.2), min(g["y_span"][1], Y1 - 0.2)
    x0, x1 = max(g["x_span"][0], X0 + 0.2), min(g["x_span"][1], X1 - 0.2)
    vxs = [x for x in g["vx"] if X0 + 0.2 <= x <= X1 - 0.2]
    hys = [y for y in g["hy"] if Y0 + 0.2 <= y <= Y1 - 0.2]
    ws = [f"M9 ( {u(x)} {u(y0)} ) ( * {u(y1)} )" for x in vxs if y1 > y0]
    ws += [f"M8 ( {u(x0)} {u(y)} ) ( {u(x1)} * )" for y in hys if x1 > x0]
    ws += [f"M8 ( {u(x)} {u(y)} ) VIA89" for y in hys for x in vxs if x0 <= x <= x1]
    nets_out = []
    for n, v in sel.items():
        d = "( PIN root )" if v["drv"] == "port:root" else f"( {v['drv']} Y )"
        nets_out.append(f"- {n} {d} " + " ".join(f"( {l} A )" for l in v["loads"]) + " + USE CLOCK ;")
    if (mdrv or mtap) and ws:
        conn = " ".join(f"( {d} Y )" for d in mdrv) + " " + " ".join(f"( {l} A )" for l in mtap)
        nets_out.append(f"- ck_mesh {conn} + USE CLOCK + NONDEFAULTRULE CK4W\n  + FIXED " + "\n    NEW ".join(ws) + " ;")
    ndr = ["NONDEFAULTRULES 1 ;", "- CK4W " + " ".join(f"+ LAYER {l} WIDTH {w} SPACING {w}" for l, w in (("M1", 18), ("M2", 18), ("M3", 18), ("M4", 24), ("M5", 24), ("M6", 32), ("M7", 32)))
           + f" + LAYER M8 WIDTH {u(STRAP_W)} SPACING {u(0.32)} + LAYER M9 WIDTH {u(STRAP_W)} SPACING {u(0.32)} ;",
           "END NONDEFAULTRULES"]
    L = L[:6] + ndr + L[6:]
    L += [f"NETS {len(nets_out)} ;"] + nets_out + ["END NETS", "END DESIGN"]
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "clip.def").write_text("\n".join(L) + "\n")
    # entry slew from the full-region GRT run (composition reference); the drt compose re-times with the mid-clip slew
    full = read_tree(T / "tree_grt_TT.txt")
    slew = full[entry]["A"][2] if entry else 0.0
    spec = dict(trial=str(T.resolve()), clip=clip, rect=rect, nets=sorted(sel), entry=entry, port=[px, py], cells=sorted(used),
                mesh_drivers=mdrv, mesh_taps=mtap, mesh_wires=len(ws), adj=adj, entry_slew_grt_TT=slew, checked="UNCHECKED")
    (o / "clip.json").write_text(json.dumps(spec, indent=1))
    (o / "run.tcl").write_text(TCL)
    (o / "sta.tcl").write_text(STA)
    (o / "run.sh").write_text(RUNSH.format(adj=adj, slew=slew, mid=1 if not entry else 0))
    print(clip, "rect", rect, "cells", len(used), "nets", len(sel), "mesh drv/taps/wires", len(mdrv), len(mtap), len(ws), "entry", entry, "slew", slew)


TCL = r"""
set t0 [clock seconds]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/clip.def
source $P/openRoad/make_tracks.tcl
create_clock -name dck -period 833.0 [get_ports root]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 $::env(ADJ)
set_global_routing_layer_adjustment M9 $::env(ADJ)
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
  if {$::env(MID)} { set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root] } else { set_input_transition $::env(SLEW) [get_ports root] }
  set_input_delay 0 -clock vclk [get_ports root]
  foreach c [get_cells M*] { set_disable_timing $c }
}
source $P/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
timing
dump grt TT
puts "OT_T grt [expr {[clock seconds]-$t0}]"
detailed_route -output_drc /o/drc.rpt -verbose 1
puts "OT_T drt [expr {[clock seconds]-$t0}]"
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /o/drt.spef
dump drt TT
write_db /o/drt.odb
write_def /o/drt.def
puts "OT_DONE [expr {[clock seconds]-$t0}]"
"""

STA = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /o/drt.odb
read_spef /o/drt.spef
create_clock -name vclk -period 833.0
if {$::env(MID)} { set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root] } else { set_input_transition $::env(SLEW) [get_ports root] }
set_input_delay 0 -clock vclk [get_ports root]
foreach c [get_cells M*] { set_disable_timing $c }
set fh [open /o/tree_drt_$::env(CORNER)$::env(TAG).txt w]
foreach c [get_cells *] {
  set n [get_full_name $c]
  if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
  foreach pn $pins {
    set p [get_pins $n/$pn]
    puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
  }
}
close $fh
puts OT_STA_DONE
"""

RUNSH = """#!/bin/bash
# clip GRT + DRT + RCX (TT dump); sta.tcl re-times TT/FF with the composed entry slew (pilot_clip.py sta)
O=$(cd $(dirname $0) && pwd)
docker run --rm --name qcmp2-$(basename $(dirname $O))-$(basename $O)-$$ --memory=24g --memory-swap=24g --cpus=8 -e ADJ={adj} -e SLEW={slew} -e MID={mid} -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/o openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -threads 8 -exit /o/run.tcl > /o/run.log 2>&1; echo "EXIT $?" >> /o/run.log
chown -R 1000:1000 /o'
"""


def compose(trial, root, stage, corner, out):
    """full-region tree file from clip arrivals: arrival(c) = arrival(entry A, from its parent clip) + clip(c) - clip(entry A).
    mid clip is absolute (same root port/driving cell as the full run)."""
    T = Path(trial)
    R = Path(root)
    suf = lambda c: R / c / f"tree_{stage}_{corner}.txt"
    mid = read_tree(suf("mid"))
    full = {}
    for c, v in mid.items():
        if c in ("R", "AL", "AR", "E0") or (c.startswith("B") and "A" in v):
            full[c] = dict(v) if c[0] != "B" and c != "E0" else {"A": v["A"]}
    for clip in ("c0", "c1", "c2", "c3", "core"):
        spec = json.load(open(R / clip / "clip.json"))
        e = spec["entry"]
        t = read_tree(suf(clip))
        off_l = full[e]["A"][0] - t[e]["A"][0]
        off_e = full[e]["A"][1] - t[e]["A"][1]
        for c, v in t.items():
            if c.startswith("M") and (clip == "core" or c not in spec["mesh_drivers"]):
                continue
            for pn, (a, b, s) in v.items():
                if c == e and pn == "A":
                    continue
                if c.startswith("L_") and not c.startswith("L_clk_c"):
                    continue
                full.setdefault(c, {})[pn] = (a + off_l, b + off_e, s)
    with open(out, "w") as fh:
        for c in sorted(full):
            for pn in sorted(full[c]):
                a, b, s = full[c][pn]
                fh.write(f"{pn} {c} {a:.6f} {b:.6f} {s:.6f}\n")
    ref = T / f"tree_grt_{corner}.txt"
    if ref.exists():
        F = read_tree(ref)
        d = [(full[c][p][0] - F[c][p][0], c, p) for c in full for p in full[c] if c in F and p in F[c]]
        d.sort()
        print(stage, corner, "pins", len(d), "vs full-region GRT late: min", [round(d[0][0], 2)] + list(d[0][1:]),
              "max", [round(d[-1][0], 2)] + list(d[-1][1:]))
    print("wrote", out, "cells", len(full))


def merge(root, out):
    import re
    R, O = Path(root), Path(out)
    O.mkdir(parents=True, exist_ok=True)
    nets, drc, summ = [], [], {}
    for clip in CLIPS:
        spec = json.load(open(R / clip / "clip.json"))
        if not (R / clip / "drt.def").exists():
            summ[clip] = dict(pending=True)
            continue
        txt = (R / clip / "drt.def").read_text()
        nets += re.split(r"\n\s*- ", txt[txt.index("\nNETS "):txt.index("END NETS")])[1:]
        px, py = spec["port"]
        rows, harness = [], 0
        blk = (R / clip / "drc.rpt").read_text().split("violation type: ")[1:]
        for b in blk:
            m = re.search(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)", b)
            x, y = (float(m.group(1)) + float(m.group(3))) / 2, (float(m.group(2)) + float(m.group(4))) / 2
            h = abs(x - px) < 3 and abs(y - py) < 3
            harness += h
            rows.append(dict(type=b.split("\n")[0].strip(), srcs=b.split("\n")[1].strip(), xy=[x, y], layer=m.group(5), harness=h))
        drc.append(f"# clip {clip}\n" + "".join("violation type: " + b for b in blk))
        log = (R / clip / "run.log").read_text()
        it = len(re.findall("Number of violations", log))
        t = re.search(r"OT_T drt (\d+)", log)
        summ[clip] = dict(violations=len(rows), harness_entry_port=harness, design=len(rows) - harness, drt_iterations=it,
                          drt_s=int(t.group(1)) if t else None, markers=[r for r in rows if not r["harness"]][:40])
    (O / "drt.def").write_text("\nNETS 0 ;\n- " + "\n- ".join(nets) + "\nEND NETS\n")
    (O / "drc.rpt").write_text("".join(drc))
    done = [v for v in summ.values() if not v.get("pending")]
    tot = dict(violations=sum(v["violations"] for v in done), design=sum(v["design"] for v in done), clips_done=len(done))
    (O / "drc_summary.json").write_text(json.dumps(dict(clips=summ, total=tot, checked="UNCHECKED"), indent=1))
    print(root, {c: "pending" if v.get("pending") else (v["violations"], v["design"], v["drt_iterations"]) for c, v in summ.items()}, tot)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2], a[3], float(a[4]))
    elif a[0] == "merge":
        merge(a[1], a[2])
    elif a[0] == "compose":
        compose(*a[1:6])
    else:
        raise SystemExit(__doc__)
