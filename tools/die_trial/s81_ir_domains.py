#!/usr/bin/env python3
"""S81.IR: window PDNSim over the SerDes windows with the separate PHY supplies of OWNER DECISION 7 (die.pg.domains).

    python3 tools/die_trial/s81_ir_domains.py generate --plan PLAN.json --out DIR --window X0 Y0 X1 Y1 \\
            [--mode base|domains] [--density 0.15] [--phy-w 4.368] [--tile 43.2]
    DIR/run_psm.sh  (docker, openroad/orfs:asap7lock; diagnostic probe, ~1-3 min, <= 16 GB)
    python3 tools/die_trial/s81_ir_domains.py record --out DIR
    python3 tools/die_trial/s81_ir_domains.py render --out DIR

Method = the TRIAL-S81 10-24 window method (tools/die_plan/die_trial.py irwin, claude/trial-s81-1024@c2713abad0) so the
numbers compare: die PG = plan die.pg.grid M8/M9 0.48/8.64 VDD+VSS; partition PG = M7 stripe pins (VDD 4.128 / VSS
4.512 mod 8.64, 0.288) on abstract load tiles; uniform 0.15 W/mm2 core load; die C4 lattice 150 um (VDD/VSS by
parity) minus channels and die IO windows, each source attached to the nearest actual M9 metal of its net; PDNSim
(analyze_power_grid) at 0.7 V.  Additions for decision 7 (--mode domains):
- every die.pg.domains rect is ONE OpenROAD region voltage domain PHY (power VDDPHY, ground VSS): pdngen cuts the core
  M8/M9 grid out of it and lays the domain grid (1.92/8.64) inside; the domain VSS is not strapped to the core VSS
  on die (joined only through the package = conservative).
- domain C4: the plan's dedicated 45-um array over bumps.rect_um, checkerboard VDDPHY / VSS (63.64 um per rail),
  as hbm_b2_ir.py; no core C4 inside a domain rect.
- PHY load on VDDPHY: --phy-w per SerDes window (default 6 x 112 Gb/s x 6.5 pJ/bit = 4.368 W, the TRIAL-HBM sourced
  value, hbm_b2_power.py) uniform over the domain's phy_macro_um (candidate plans) or else its io window rect.
- core load 0.15 W/mm2 on the window area OUTSIDE the domain rects (core cells under a domain rect have no core
  M8/M9 VDD in the plan; reported as uncovered core area, not loaded).
Tiles are cut at every domain / PHY edge so a tile is entirely core or entirely PHY.
Gate (trial): worst drop per supply <= 35 mV (5 % of 0.7 V); VSS bounce and the supply+VSS rail sum are INFO.
"""
import argparse
import json
import math
import re
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
V, GATE_MV, G = 0.7, 35.0, 8.64
PHY_W = 6 * 112e9 * 6.5e-12
VP = 45.0 / math.sqrt(0.5)


def union_boxes(rects):
    """non-overlapping boxes covering the union of rects (x-slabs, merged)."""
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    slabs = []
    for a, b in zip(xs, xs[1:]):
        iv = sorted((r[1], r[3]) for r in rects if r[0] <= a and r[2] >= b)
        m = []
        for y0, y1 in iv:
            if m and y0 <= m[-1][1] + 1e-6:
                m[-1][1] = max(m[-1][1], y1)
            else:
                m.append([y0, y1])
        slabs.append((a, b, [tuple(v) for v in m]))
    out = []
    for a, b, iv in slabs:
        for y0, y1 in iv:
            prev = next((o for o in out if abs(o[2] - a) < 1e-6 and abs(o[1] - y0) < 1e-6 and abs(o[3] - y1) < 1e-6), None)
            if prev:
                prev[2] = b
            else:
                out.append([a, y0, b, y1])
    return [tuple(o) for o in out]


def inside(x, y, r):
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


def cuts(lo, hi, must, T):
    c = []
    for v in sorted({lo, hi} | {round(m, 3) for m in must if lo < m < hi}):
        if not c or v - c[-1] > 0.01:      # float-equal edges (e.g. 1330.56 vs 1330.5600000000002) -> one cut
            c.append(v)
    out = [c[0]]
    for a, b in zip(c, c[1:]):
        n = max(1, round((b - a) / T))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return out


def generate(a):
    plan = json.loads(Path(a.plan).read_text())
    die = plan["die"]
    W, H = die["outline_um"]
    io = die.get("io", [])
    doms = die["pg"].get("domains", []) if a.mode == "domains" else []
    grid = die["pg"]["grid"]
    x0, y0, x1, y1 = [round(v / G) * G for v in a.window]
    x1, y1 = min(x1, W), min(y1, H)
    win = (x0, y0, x1, y1)
    clip = lambda r: (max(r[0], x0), max(r[1], y0), min(r[2], x1), min(r[3], y1))
    ok = lambda r: r[2] - r[0] > 1 and r[3] - r[1] > 1
    drects = [clip(d["rect_um"]) for d in doms if ok(clip(d["rect_um"]))]
    dboxes = union_boxes(drects) if drects else []
    if a.phy_box is not None:   # pdngen 26Q3 connects macro loads only in the FIRST region domain: a window with
        k = a.phy_box             # several domain-union boxes is solved once per box (that box first, PHY loads
        dboxes = [dboxes[k]] + dboxes[:k] + dboxes[k + 1:]   # only in it; the other boxes stay cut out of core)
    phys = []
    for d in doms:
        if not ok(clip(d["rect_um"])):
            continue
        pr = d.get("phy_macro_um") or next(w["rect_um"] for w in io if w["name"] == d["io"][0])
        phys.append(dict(dom=d["name"], rect=tuple(pr), w=a.phy_w, clip=clip(pr)))
    # tiles cut at domain / phy edges
    chans = [clip(c["rect_um"]) for c in die.get("channels", []) if ok(clip(c["rect_um"]))]
    mx = [v for r in drects + chans for v in (r[0], r[2])] + [v for p in phys for v in (p["clip"][0], p["clip"][2])]
    my = [v for r in drects + chans for v in (r[1], r[3])] + [v for p in phys for v in (p["clip"][1], p["clip"][3])]
    XC, YC = cuts(x0, x1, mx, a.tile), cuts(y0, y1, my, a.tile)
    tiles = []
    core_area = unc_area = 0.0
    for i, (tx0, tx1) in enumerate(zip(XC, XC[1:])):
        for j, (ty0, ty1) in enumerate(zip(YC, YC[1:])):
            cx, cy, ar = (tx0 + tx1) / 2, (ty0 + ty1) / 2, (tx1 - tx0) * (ty1 - ty0)
            p = next((p for p in phys if inside(cx, cy, p["clip"])), None)
            if p and a.phy_box is not None and not inside(cx, cy, dboxes[0]):
                continue
            if p:
                pa = (p["rect"][2] - p["rect"][0]) * (p["rect"][3] - p["rect"][1])
                tiles.append(dict(n=f"P_{i}_{j}", kind="phy", r=(tx0, ty0, tx1, ty1), w=p["w"] * ar / pa, dom=p["dom"]))
            elif any(inside(cx, cy, r) for r in drects):
                unc_area += ar
            elif any(inside(cx, cy, r) for r in chans):
                continue        # seal ring / corner keep-out channels: no logic (the trial loaded them)
            else:
                core_area += ar
                tiles.append(dict(n=f"C_{i}_{j}", kind="core", r=(tx0, ty0, tx1, ty1), w=a.density * ar * 1e-6))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # LEF: one master per (kind, size, phase)
    masters, lef = {}, ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for t in tiles:
        tx0, ty0, tx1, ty1 = t["r"]
        w, h = round(tx1 - tx0, 3), round(ty1 - ty0, 3)
        # core: partition M7 phase (VDD 4.128 / VSS 4.512); PHY macro pins: VDDPHY under the VDDPHY M9 strap (4.32),
        # VSS under the VSS M9 strap (8.64) -- at 4.128/4.512 pdngen gives the PHY VSS pins no M7-M8 vias (PSM-0069)
        ph = round(((4.128 if t["kind"] == "core" else 4.32) - tx0) % G, 3)
        dvss = 0.384 if t["kind"] == "core" else 4.32
        key = (t["kind"], w, h, ph)
        if key not in masters:
            nm = f"{t['kind'][0].upper()}M{len(masters)}"
            masters[key] = nm
            pw = "VDDPHY" if t["kind"] == "phy" else "VDD"
            lef += [f"MACRO {nm}", " CLASS BLOCK ;", " ORIGIN 0 0 ;", f" SIZE {w:.3f} BY {h:.3f} ;"]
            gw = "VSSPHY" if t["kind"] == "phy" else "VSS"
            for net, o in ((pw, ph), (gw, ph + dvss)):
                lef += [f" PIN {net}", " DIRECTION INOUT ;", f" USE {'GROUND' if net.startswith('VSS') else 'POWER'} ;", " PORT",
                        " LAYER M7 ;"]
                c, k = o % G, 0
                while c + 0.144 < w:
                    if c - 0.144 > 0:
                        lef.append(f"  RECT {c - 0.144:.3f} 0 {c + 0.144:.3f} {h:.3f} ;")
                        k += 1
                    c += G
                if not k:      # narrow tile: one off-phase stripe (M8 is horizontal: it still crosses)
                    cc = w * (0.7 if net.startswith("VSS") else 0.3)
                    lef.append(f"  RECT {cc - 0.144:.3f} 0 {cc + 0.144:.3f} {h:.3f} ;")
                lef += [" END", f" END {net}"]
            lef += [f"END {nm}"]
        t["m"] = masters[key]
    lef.append("END LIBRARY")
    (out / "loads.lef").write_text("\n".join(lef) + "\n")
    ww, hh = x1 - x0, y1 - y0
    d = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', "DESIGN s81ir ;", "UNITS DISTANCE MICRONS 1000 ;",
         f"DIEAREA ( 0 0 ) ( {round(ww * 1000)} {round(hh * 1000)} ) ;", f"COMPONENTS {len(tiles)} ;"]
    d += [f"- {t['n']} {t['m']} + FIXED ( {round((t['r'][0] - x0) * 1000)} {round((t['r'][1] - y0) * 1000)} ) N ;"
          for t in tiles]
    d += ["END COMPONENTS", "NETS 6 ;", "- VDD + USE POWER ;", "- VDDPHY + USE POWER ;", "- VSS + USE GROUND ;", "- VSSPHY + USE GROUND ;", "- VDDPHYO + USE POWER ;", "- VSSPHYO + USE GROUND ;",
          "END NETS", "END DESIGN"]
    (out / "case.def").write_text("\n".join(d) + "\n")
    # bumps (die coordinates): core lattice 150 um minus channels / io windows / domain rects; domain 45-um rows
    keep = [c["rect_um"] for c in die.get("channels", [])] + [w["rect_um"] for w in io] + drects
    if doms and any(d.get("phy_macro_um") for d in doms):
        # candidate split: the serdes io window outside the domain rect is the core strip (core C4 allowed there)
        keep = [c["rect_um"] for c in die.get("channels", [])] + [w["rect_um"] for w in io if w.get("iface") != "serdes"] \
            + [d["rect_um"] for d in doms]
    bumps = []
    nx, ny = int(W // 150.0), int(H // 150.0)
    bx0, by0 = (W - (nx - 1) * 150.0) / 2, (H - (ny - 1) * 150.0) / 2
    reloc = 0
    drs = [d["rect_um"] for d in doms if d.get("core_edge_bumps") == "relocate"]
    for i in range(nx):
        for j in range(ny):
            x, y = bx0 + i * 150.0, by0 + j * 150.0
            if drs and any(inside(x, y, r) for r in drs):
                # candidate: a lattice C4 that falls inside a domain rect within half a pitch of an edge facing core
                # moves 15 um outside that edge (the core cells along the domain keep their bump column / row)
                r = next(r for r in drs if inside(x, y, r))
                for nxy in ((r[0] - 15.0, y), (r[2] + 15.0, y), (x, r[1] - 15.0), (x, r[3] + 15.0)):
                    if abs(nxy[0] - x) + abs(nxy[1] - y) <= 75.0 + 15.0 and 0 < nxy[0] < W and 0 < nxy[1] < H \
                            and not any(inside(nxy[0], nxy[1], q) for q in keep):
                        x, y = nxy
                        reloc += 1
                        break
            if x0 < x < x1 and y0 < y < y1 and not any(inside(x, y, r) for r in keep):
                bumps.append(("VDD" if (i + j) % 2 == 0 else "VSS", x, y))
    nb_core = len(bumps)
    for dm in doms:
        br = dm["bumps"]["rect_um"]
        # --phy-box: PSM traces a net from one island only, so the other boxes' domains get their own nets (unsolved)
        oth = a.phy_box is not None and not inside((br[0] + br[2]) / 2, (br[1] + br[3]) / 2, dboxes[0])
        for net, ph in (("VDDPHYO" if oth else "VDDPHY", VP / 2), ("VSSPHYO" if oth else "VSSPHY", 0.0)):
            for jy in range(math.ceil((br[1] - ph) / VP), math.floor((br[3] - ph) / VP) + 1):
                for ix in range(math.ceil((br[0] - ph) / VP), math.floor((br[2] - ph) / VP) + 1):
                    x, y = ph + ix * VP, ph + jy * VP
                    if x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1:
                        bumps.append((net, x, y))
    bumps = [(n, round(x - x0, 3), round(y - y0, 3)) for n, x, y in bumps]
    (out / "bumps.tcl").write_text(bumps_tcl(bumps))
    # pdn
    s = grid[0]
    t = [f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef", f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef",
         "read_lef /work/loads.lef", "read_def /work/case.def", "set t0 [clock seconds]", "set b [ord::get_db_block]"]
    # pdngen supports one box per region: one region voltage domain PHY<k> per box of the domain-rect union
    for k, r in enumerate(dboxes):
        t += [f"set r [odb::dbRegion_create $b PHYR{k}]",
              f"odb::dbBox_create $r {round((r[0] - x0) * 1000)} {round((r[1] - y0) * 1000)} "
              f"{round((r[2] - x0) * 1000)} {round((r[3] - y0) * 1000)}"]
    t += ["add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power",
          "add_global_connection -net VDDPHY -inst_pattern {.*} -pin_pattern {^VDDPHY$} -power",
          "add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground",
          "add_global_connection -net VSSPHY -inst_pattern {.*} -pin_pattern {^VSSPHY$} -ground", "global_connect",
          "set_voltage_domain -name CORE -power VDD -ground VSS"]
    for k in range(len(dboxes)):
        o = "O" if (a.phy_box is not None and k > 0) else ""
        t.append(f"set_voltage_domain -name PHY{k} -region PHYR{k} -power VDDPHY{o} -ground VSSPHY{o}")
    def stripes(gname, gr):
        L = []
        for st in gr:
            L.append(f"add_pdn_stripe -grid {gname} -layer {st['layer']} -width {st['width_um']:g} -pitch {st['pitch_um']:g} "
                     f"-offset {st['offset_um']:g} -spacing {st['pitch_um'] / 2 - st['width_um']:g} -starts_with POWER")
        L.append(f"add_pdn_connect -grid {gname} -layers {{{gr[0]['layer']} {gr[1]['layer']}}}")
        return L
    t += ["define_pdn_grid -name top -voltage_domains CORE"] + stripes("top", grid)
    cm = sorted(v for k, v in masters.items() if k[0] == "core")
    pm = sorted(v for k, v in masters.items() if k[0] == "phy")
    if cm:
        t += [f"define_pdn_grid -macro -name cload -cells {{{' '.join(cm)}}} -halo {{0 0 0 0}} -voltage_domains CORE",
              f"add_pdn_connect -grid cload -layers {{M7 {grid[0]['layer']}}}"]
    if dboxes:
        dg = doms[0]["grid"]
        for k in range(len(dboxes)):
            t += [f"define_pdn_grid -name phy{k} -voltage_domains PHY{k}"] + stripes(f"phy{k}", dg)
        if pm:     # one macro grid per region domain, by instance (a multi-domain -cells grid leaves the 2nd region bare)
            for k, rb in enumerate(dboxes):
                ins = [t_["n"] for t_ in tiles if t_["kind"] == "phy" and inside((t_["r"][0] + t_["r"][2]) / 2, (t_["r"][1] + t_["r"][3]) / 2, rb)]
                if ins:
                    t += [f"define_pdn_grid -macro -name pload{k} -instances {{{' '.join(ins)}}} -halo {{0 0 0 0}} -voltage_domains PHY{k}",
                          f"add_pdn_connect -grid pload{k} -layers {{M7 {dg[0]['layer']}}}"]
    nets = ["VDD", "VSS"] + (["VDDPHY", "VSSPHY"] if dboxes else [])
    if a.nets:
        nets = [n for n in nets if n in a.nets.split(",")]
    t += ["pdngen -failed_via_report /work/failed_vias.rpt", 'puts "OT_T pdngen [expr {[clock seconds]-$t0}]"',
          "source /work/bumps.tcl", 'puts "OT_T bumps [expr {[clock seconds]-$t0}]"',
          "if {[info exists ::env(OT_CHECK_ONLY)]} { foreach n {VDD VSS VDDPHY VSSPHY} { if {[catch {check_power_grid -net $n} e]} "
          "{ puts \"OT_PG_CHECK_FAIL $n $e\" } else { puts \"OT_PG_CHECK_OK $n\" } }; exit }",
          f"foreach f [glob {PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}", f"source {PLAT}/setRC.tcl",
          "set_cmd_units -power W", "source /work/power.tcl",
          f"foreach n {{{' '.join(nets)}}} {{",
          "  if {[catch {check_power_grid -net $n -error_file /work/pg_err_$n.rpt} e]} { puts \"OT_PG_CHECK_FAIL $n $e\" } else { puts \"OT_PG_CHECK_OK $n\" }",
          f"  set_pdnsim_net_voltage -net $n -voltage [expr {{[string match VSS* $n] ? 0 : {V}}}]",
          "  if {[catch {analyze_power_grid -net $n -error_file /work/psm_$n.rpt -voltage_file /work/ir_$n.csv} e]} "
          "{ puts \"OT_PSM_FAIL $n $e\" } else { puts \"OT_PSM_OK $n\" }",
          "  puts \"OT_T psm_$n [expr {[clock seconds]-$t0}]\"", "}", "puts OT_DONE"]
    (out / "run.tcl").write_text("\n".join(t) + "\n")
    (out / "power.tcl").write_text("".join(f"set_pdnsim_inst_power -inst {t['n']} -power {t['w']:.9g}\n" for t in tiles))
    (out / "run_psm.sh").write_text(f"""#!/bin/bash
# s81_ir_domains.py case (diagnostic window probe): run_psm.sh [THREADS=8] [MEM_GB=16]
D=$(cd $(dirname $0) && pwd); N=${{1:-8}}; M=${{2:-16}}
DK=docker; $DK info >/dev/null 2>&1 || DK="sudo docker"
echo "host $(hostname) start $(date -Is) image $($DK image inspect --format '{{{{.Id}}}}' openroad/orfs:asap7lock)" > $D/run.image.txt
$DK run --rm --name s81ir_$(basename $D) ${{OT_CHECK_ONLY:+-e OT_CHECK_ONLY=1}} --cpus=$N --memory=${{M}}g --memory-swap=${{M}}g -v $D:/work -e HUID=$(id -u) -e HGID=$(id -g) \\
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $N -no_init -exit /work/run.tcl > /work/run.log 2>&1; echo EXIT \\$? >> /work/run.log; chown -R \\$HUID:\\$HGID /work"
echo "end $(date -Is)" >> $D/run.image.txt
grep -E "OT_|Worstcase|Maximum resident|Elapsed|EXIT" $D/run.log | tail -30
""")
    (out / "run_psm.sh").chmod(0o755)
    man = dict(schema="opentallas.s81_ir_domains.case.v1", plan=a.plan, phy_box=a.phy_box, nets=nets,
               die=plan.get("name") or ("s81_head" if "head" in Path(a.plan).name else "s81"), mode=a.mode,
               window_um=list(win), tile_um=a.tile, density_w_mm2=a.density, voltage_v=V, gate_mv=GATE_MV,
               core_grid=grid, domain_grid=doms[0]["grid"] if doms else None,
               domains=[dict(name=dm["name"], io=dm["io"], rect_um=dm["rect_um"], bumps_rect_um=dm["bumps"]["rect_um"],
                             phy_macro_um=dm.get("phy_macro_um"), core_strip_um=dm.get("core_strip_um"))
                        for dm in doms if ok(clip(dm["rect_um"]))],
               region_boxes=[list(r) for r in dboxes],
               phy=[dict(dom=p["dom"], rect_um=list(p["rect"]), w=round(p["w"], 4),
                         w_per_mm2=round(p["w"] / ((p["rect"][2] - p["rect"][0]) * (p["rect"][3] - p["rect"][1]) * 1e-6), 4))
                    for p in phys],
               phy_w_basis="6 lanes x 112 Gb/s x 6.5 pJ/bit (hbm_b2_power.py SERDES_*; hbrom-power.json board_serdes_112g)",
               tiles=dict(core=sum(1 for t in tiles if t["kind"] == "core"), phy=sum(1 for t in tiles if t["kind"] == "phy")),
               core_load_w=round(sum(t["w"] for t in tiles if t["kind"] == "core"), 4),
               phy_load_w=round(sum(t["w"] for t in tiles if t["kind"] == "phy"), 4),
               core_area_mm2=round(core_area * 1e-6, 4), channels_unloaded=[list(c) for c in chans], uncovered_core_area_mm2=round(unc_area * 1e-6, 4),
               bumps=dict(core=nb_core, core_relocated_to_domain_edges=reloc, domain=len(bumps) - nb_core,
                          by_net={n: sum(1 for b in bumps if b[0] == n) for n in ("VDD", "VSS", "VDDPHY", "VSSPHY")}),
               io_in_window=[w["name"] for w in io if w["rect_um"][0] < x1 and w["rect_um"][2] > x0
                             and w["rect_um"][1] < y1 and w["rect_um"][3] > y0])
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    (out / "tiles.json").write_text(json.dumps([dict(n=t["n"], k=t["kind"], r=[round(v, 3) for v in t["r"]],
                                                     dom=t.get("dom")) for t in tiles]) + "\n")
    print(json.dumps({k: man[k] for k in ("mode", "window_um", "tiles", "core_load_w", "phy_load_w", "bumps",
                                          "uncovered_core_area_mm2", "io_in_window")}))


def bumps_tcl(bumps, size=4.0):
    """die_trial.py bumps_tcl (claude/trial-s81-1024): each source on the nearest actual M9 metal of its own net
    (here by x AND y among the columns within one pitch: a shared VSS has core and domain straps)."""
    nets = sorted({n for n, _, _ in bumps})
    t = ["set block [ord::get_db_block]", "set m9 [[ord::get_db_tech] findLayer M9]",
         "set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]", "set bump_shapes {}", "set bump_x_cache {}",
         f"foreach net_name {{{' '.join(nets)}}} {{", "  set shapes {}",
         "  foreach wire [[$block findNet $net_name] getSWires] {", "    foreach shape [$wire getWires] {",
         "      if {[$shape isVia] || [$shape getTechLayer] ne $m9} continue",
         "      lappend shapes [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]", "    }", "  }",
         "  if {![llength $shapes]} { error \"no actual M9 metal for $net_name voltage sources\" }",
         "  dict set bump_shapes $net_name $shapes", "}",
         "proc ot_bump {k net x y} {",
         "  global block m9 bump_dbu bump_shapes bump_x_cache",
         "  set bx [expr {$x*$bump_dbu}]; set by [expr {$y*$bump_dbu}]",
         "  set cache_key [list $net $bx]",
         "  if {![dict exists $bump_x_cache $cache_key]} {",
         "    set nearest {}; set x_distance 1e30",
         "    foreach rect [dict get $bump_shapes $net] {",
         "      lassign $rect x0 y0 x1 y1",
         "      set dx [expr {abs(($x0+$x1)/2.0-$bx)}]",
         "      if {$dx < $x_distance} { set x_distance $dx }",
         "    }",
         "    # all columns within one strap pitch of the nearest: VSS has core AND domain straps (different phases);",
         "    # the nearest-x column alone can be a domain strap that ends far below a core-strip bump",
         "    foreach rect [dict get $bump_shapes $net] {",
         "      lassign $rect x0 y0 x1 y1",
         "      if {abs(($x0+$x1)/2.0-$bx) <= $x_distance + 8.64*$bump_dbu} { lappend nearest $rect }",
         "    }",
         "    dict set bump_x_cache $cache_key $nearest",
         "  }",
         "  set best {}; set best_distance 1e30",
         "  foreach rect [dict get $bump_x_cache $cache_key] {",
         "    lassign $rect x0 y0 x1 y1",
         "    set cx [expr {($x0+$x1)/2.0}]",
         f"    set half [expr {{min({size:g}*$bump_dbu/2.0,($y1-$y0)/2.0)}}]",
         "    set cy [expr {max($y0+$half,min($y1-$half,$by))}]",
         "    set distance [expr {abs($cx-$bx)+abs($cy-$by)}]",
         "    if {$distance < $best_distance} { set best_distance $distance; set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]] }",
         "  }",
         "  set bt [odb::dbBTerm_create [$block findNet $net] ${net}_b$k]; $bt setIoType INOUT",
         "  $bt setSigType [expr {[string match VSS* $net] ? \"GROUND\" : \"POWER\"}]; set bp [odb::dbBPin_create $bt]",
         "  odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM",
         "}"]
    t += [f"ot_bump {k} {n} {x:g} {y:g}" for k, (n, x, y) in enumerate(bumps)]
    t.append(f'puts "OT_BUMPS {len(bumps)} [dict size $bump_x_cache] columns"')
    return "\n".join(t) + "\n"


def load_ir(out, net):
    f = out / f"ir_{net}.csv"
    v = {}
    if not f.exists():
        return v
    for ln in f.read_text().splitlines()[1:]:
        c = ln.split(",")
        if len(c) >= 6:
            try:
                val = float(c[5])
            except ValueError:
                continue
            dv = val if net.startswith("VSS") else (V - val)
            v[c[0]] = max(v.get(c[0], -1.0), dv)
    return v


def record(a):
    out = Path(a.out)
    m = json.loads((out / "manifest.json").read_text())
    tiles = {t["n"]: t for t in json.loads((out / "tiles.json").read_text())}
    log = (out / "run.log").read_text(errors="replace") if (out / "run.log").exists() else ""
    x0, y0 = m["window_um"][:2]
    regs = [r for r in m["region_boxes"]]
    near = 300.0

    def dist_dom(r):
        if not regs:
            ios = []
            return None
        return min(max(rr[0] - r[2], r[0] - rr[2], 0) + max(rr[1] - r[3], r[1] - rr[3], 0) for rr in regs)
    res = dict(manifest=m, done="OT_DONE" in log,
               pg_check={n: s for s, n in re.findall(r"OT_PG_CHECK_(OK|FAIL) (\w+)", log)},
               psm={n: s for s, n in re.findall(r"OT_PSM_(OK|FAIL) (\w+)", log)},
               log_worst={}, rails={})
    for blk in re.findall(r"IR report.*?Worstcase IR drop\s*:\s*([\d.e+-]+)", log, re.S):
        pass
    for net in ("VDD", "VDDPHY", "VSS", "VSSPHY"):
        ir = load_ir(out, net)
        if not ir:
            continue
        rec = {}
        groups = dict(all=lambda t: True, core=lambda t: t["k"] == "core", phy=lambda t: t["k"] == "phy")
        if regs:
            groups["core_near_domain"] = lambda t: t["k"] == "core" and dist_dom(t["r"]) <= near
            groups["core_far"] = lambda t: t["k"] == "core" and dist_dom(t["r"]) > 1000.0
        else:
            ios = [w for w in []]
        for g, f in groups.items():
            best = None
            for n, dv in ir.items():
                t = tiles.get(n)
                if t is None or not f(t):
                    continue
                if best is None or dv > best[0]:
                    best = (dv, n)
            if best:
                r = tiles[best[1]]["r"]
                rec[g] = dict(worst_mv=round(best[0] * 1000, 2), at_um=[round((r[0] + r[2]) / 2, 1), round((r[1] + r[3]) / 2, 1)],
                              tile=best[1])
        if net in ("VDDPHY", "VSSPHY") and m["domains"]:
            W0, Y0, W1, Y1 = m["window_um"]
            for dm in m["domains"]:
                r = dm["rect_um"]
                full = r[0] >= W0 - 1 and r[2] <= W1 + 1 and r[1] >= Y0 - 1 and r[3] <= Y1 + 1
                vals = [(dv, n) for n, dv in ir.items() if tiles.get(n, {}).get("dom") == dm["name"]]
                if vals:
                    dv, n = max(vals)
                    rec.setdefault("per_domain", {})[dm["name"]] = dict(worst_mv=round(dv * 1000, 2), whole_in_window=full)
        res["rails"][net] = rec
    R = res["rails"]
    sup = {}
    if "VDD" in R and "all" in R["VDD"]:
        sup["VDD"] = R["VDD"]["all"]["worst_mv"]
    if "VDDPHY" in R and "phy" in R["VDDPHY"]:
        pd = {k: v["worst_mv"] for k, v in R["VDDPHY"].get("per_domain", {}).items() if v["whole_in_window"]}
        sup["VDDPHY"] = max(pd.values()) if pd else R["VDDPHY"]["phy"]["worst_mv"]
    res["gate_mv"] = GATE_MV
    res["supply_worst_mv"] = sup
    res["vss_worst_mv"] = {g: R["VSS"][g]["worst_mv"] for g in R.get("VSS", {}) if g != "per_domain"}
    if "VSSPHY" in R and "phy" in R["VSSPHY"]:
        pd = {k: v["worst_mv"] for k, v in R["VSSPHY"].get("per_domain", {}).items() if v["whole_in_window"]}
        res["vss_worst_mv"]["phy_domain"] = max(pd.values()) if pd else R["VSSPHY"]["phy"]["worst_mv"]
    res["verdict"] = ("NOT RUN" if not sup or not res["done"] else
                      "PASS" if all(v <= GATE_MV for v in sup.values()) else "FAIL")
    (out / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("done", "pg_check", "psm", "supply_worst_mv", "vss_worst_mv", "verdict")}))


def render(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import PatchCollection
    out = Path(a.out)
    m = json.loads((out / "manifest.json").read_text())
    tiles = json.loads((out / "tiles.json").read_text())
    nets = [n for n in ("VDD", "VDDPHY", "VSS", "VSSPHY") if (out / f"ir_{n}.csv").exists()]
    x0, y0, x1, y1 = m["window_um"]
    asp = (y1 - y0) / (x1 - x0)
    fig, axs = plt.subplots(len(nets), 1, figsize=(16, max(3.0, 16 * asp) * len(nets) + 1.2), squeeze=False)
    vmax = a.vmax
    for ax, net in zip(axs[:, 0], nets):
        ir = load_ir(out, net)
        ps, cs = [], []
        for t in tiles:
            if t["n"] in ir:
                r = t["r"]
                ps.append(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1]))
                cs.append(ir[t["n"]] * 1000)
        pc = PatchCollection(ps, cmap="inferno_r" if False else "viridis", linewidths=0)
        pc.set_array(cs)
        pc.set_clim(0, vmax or max(cs))
        ax.add_collection(pc)
        for rr in m["region_boxes"]:
            ax.add_patch(Rectangle((rr[0], rr[1]), rr[2] - rr[0], rr[3] - rr[1], fill=False, ec="red", lw=1.2, ls="--"))
        for d in m["domains"]:
            b = d["bumps_rect_um"]
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="orange", lw=0.8))
            ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, d["name"], ha="center", va="center", fontsize=8, color="w")
        for p in m["phy"]:
            r = p["rect_um"]
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="cyan", lw=0.6, ls=":"))
        worst = max(cs)
        k = cs.index(worst)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title(f"{out.name} ({m['die']}, {m['mode']}) {net}: worst {worst:.1f} mV (gate {GATE_MV:g} mV supply)  "
                     f"core {m['density_w_mm2']} W/mm2, PHY {m['phy'][0]['w'] if m['phy'] else 0} W/window", fontsize=10)
        fig.colorbar(pc, ax=ax, label=f"{net} drop mV", fraction=0.02)
    fig.tight_layout()
    f = out / f"ir_map_{out.name}.png"
    fig.savefig(f, dpi=a.dpi)
    print(f)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["generate", "record", "render"])
    p.add_argument("--plan")
    p.add_argument("--out", required=True)
    p.add_argument("--window", type=float, nargs=4)
    p.add_argument("--mode", choices=["base", "domains"], default="domains")
    p.add_argument("--density", type=float, default=0.15)
    p.add_argument("--phy-w", type=float, default=PHY_W)
    p.add_argument("--tile", type=float, default=43.2)
    p.add_argument("--vmax", type=float, default=None)
    p.add_argument("--phy-box", type=int, default=None)
    p.add_argument("--nets", default=None, help="comma list of nets to analyse (default all)")
    p.add_argument("--dpi", type=int, default=110)
    a = p.parse_args()
    dict(generate=generate, record=record, render=render)[a.cmd](a)
