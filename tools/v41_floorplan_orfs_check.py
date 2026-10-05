#!/usr/bin/env python3
"""OpenROAD floorplan-only legality run for the packed V4.1 layer die.

Builds a blackbox netlist instantiating every hard macro of
tools/v41_floorplan_pack.py, initialises the 815 mm2 ASAP7 floorplan (rows on
the asap7sc7p5t site, platform make_tracks), applies the generated placement
(MACRO_PLACEMENT_TCL), then checks in OpenROAD itself:

* every macro inside the die, FIRM, on the placement site/row grid;
* no macro/macro overlap (odb bounding boxes, bucketed);
* every catalog macro signal pin centre on its routing track (odb pins vs the
  platform tracks);
* the platform macro PDN (BLOCKS_grid_strategy.tcl: M1/M2 followpins, M5/M6
  straps and rings, M5-M6 element grid over every macro) generates without
  error, and ``check_power_grid`` connectivity for VDD and VSS when requested.

Standard cells, tapcells, routing and timing are out of scope (the die has no
netlist yet).  The run happens in the pinned ORFS docker image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_pack as PK  # noqa: E402

IMAGE = "openroad/orfs:latest"
FLOW = "/OpenROAD-flow-scripts/flow"
PLAT = f"{FLOW}/platforms/asap7"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
CORE_MARGIN = 10.8   # 0.054*200 = 0.27*40: core origin keeps the joint grid


def assumed_lef(name: str, w: float, h: float) -> str:
    return "\n".join([
        "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', f"MACRO {name}", "  CLASS BLOCK ;",
        f"  FOREIGN {name} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;",
        "  OBS", *[f"    LAYER {l} ;\n    RECT 0 0 {w:.3f} {h:.3f} ;" for l in ("M1", "M2", "M3", "M4")],
        "  END", f"END {name}", "END LIBRARY", ""])


def crop(B: dict, window: list[float]) -> dict:
    """Keep the macros wholly inside a joint-grid-aligned window, re-origined to (0, 0)."""
    x0, y0, x1, y1 = window
    x0, y0 = PK.snap_dn(x0, PK.X_STEP), PK.snap_dn(y0, PK.Y_STEP)
    x1, y1 = PK.snap_dn(x1, PK.X_STEP), PK.snap_dn(y1, PK.Y_STEP)
    P = PK.Plan()
    for m in B["P"].hard:
        if m["x"] >= x0 and m["y"] >= y0 and m["x"] + m["w"] <= x1 and m["y"] + m["h"] <= y1:
            P.add_hard(m["name"], m["master"], m["x"] - x0, m["y"] - y0, m["w"], m["h"], m["orient"], m["group"])
    g = dict(B["geometry"], die_w_um=round(x1 - x0, 3), die_h_um=round(y1 - y0, 3), window=[x0, y0, x1, y1])
    return dict(B, P=P, geometry=g)


def prepare(variant: str, run: Path, pdn: bool, psm: bool, exclude: str = "", window=None,
            tapcell: bool = False, pdn_tcl: str = f"{PLAT}/openRoad/pdn/BLOCKS_grid_strategy.tcl") -> dict:
    B = PK.build(variant)
    if window:
        B = crop(B, window)
    P = B["P"]
    g = B["geometry"]
    run.mkdir(parents=True, exist_ok=True)
    PK.write_tcl(B, run / "macros.tcl")
    masters = sorted({m["master"] for m in P.hard})
    lefs = []
    for m in masters:
        if m.startswith("ot_"):
            lefs.append(f"/work/macros/{m}/{m}.lef")
        else:
            w = next(x["w"] for x in P.hard if x["master"] == m)
            h = next(x["h"] for x in P.hard if x["master"] == m)
            (run / f"{m}.lef").write_text(assumed_lef(m, w, h))
            lefs.append(f"/run/{m}.lef")
    die_w, die_h = g["die_w_um"], g["die_h_um"]
    # Unplaced DEF components: read_def creates the block; macros.tcl then places them.
    d = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', "DESIGN ot_v41_rom_layer_die_fp ;",
         "UNITS DISTANCE MICRONS 1000 ;",
         f"DIEAREA ( 0 0 ) ( {round(die_w * 1000)} {round(die_h * 1000)} ) ;",
         f"COMPONENTS {len(P.hard)} ;"]
    d += [f"- {n['name']} {n['master']} ;" for n in P.hard]
    d += ["END COMPONENTS", "END DESIGN", ""]
    (run / "top.def").write_text("\n".join(d))
    cx1 = PK.snap_dn(die_w - CORE_MARGIN, 0.054 * 8)
    cy1 = PK.snap_dn(die_h - CORE_MARGIN, 0.27 * 8)
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{chr(10).join('read_lef ' + l for l in lefs)}
read_def /run/top.def
initialize_floorplan -die_area {{0 0 {die_w:.3f} {die_h:.3f}}} -core_area {{{CORE_MARGIN} {CORE_MARGIN} {cx1:.3f} {cy1:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
source /run/macros.tcl
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
puts "OT_STAT dbu=$dbu insts=[llength [$block getInsts]] rows=[llength [$block getRows]]"
set row0 [lindex [$block getRows] 0]
set ro [$row0 getOrigin]
set sw [[$row0 getSite] getWidth]
set sh [[$row0 getSite] getHeight]
puts "OT_STAT row_origin=$ro site=${{sw}}x${{sh}}"
# ---- containment, status and grid ----
set die [$block getDieArea]
set bad_die 0; set bad_grid 0; set bad_status 0; set n 0
set buckets [dict create]
set B [expr {{500 * $dbu}}]
foreach inst [$block getInsts] {{
  incr n
  set bb [$inst getBBox]
  set x0 [$bb xMin]; set y0 [$bb yMin]; set x1 [$bb xMax]; set y1 [$bb yMax]
  if {{$x0 < [$die xMin] || $y0 < [$die yMin] || $x1 > [$die xMax] || $y1 > [$die yMax]}} {{ incr bad_die }}
  if {{[$inst getPlacementStatus] ne "FIRM"}} {{ incr bad_status }}
  set name [[$inst getMaster] getName]
  if {{[string match ot_rom* $name] || [string match ot_sram* $name]}} {{
    if {{(($x0 - [lindex $ro 0]) % $sw) != 0 || (($y0 - [lindex $ro 1]) % $sh) != 0}} {{ incr bad_grid }}
  }}
  for {{set gx [expr {{$x0 / $B}}]}} {{$gx <= [expr {{$x1 / $B}}]}} {{incr gx}} {{
    for {{set gy [expr {{$y0 / $B}}]}} {{$gy <= [expr {{$y1 / $B}}]}} {{incr gy}} {{
      dict lappend buckets "$gx,$gy" [list $x0 $y0 $x1 $y1 [$inst getName]]
    }}
  }}
}}
set overlaps 0
set seen [dict create]
dict for {{k lst}} $buckets {{
  set m [llength $lst]
  for {{set i 0}} {{$i < $m}} {{incr i}} {{
    lassign [lindex $lst $i] ax0 ay0 ax1 ay1 an
    for {{set j [expr {{$i+1}}]}} {{$j < $m}} {{incr j}} {{
      lassign [lindex $lst $j] bx0 by0 bx1 by1 bn
      if {{$ax0 < $bx1 && $bx0 < $ax1 && $ay0 < $by1 && $by0 < $ay1}} {{
        set key [lsort [list $an $bn]]
        if {{![dict exists $seen $key]}} {{ dict set seen $key 1; incr overlaps; if {{$overlaps <= 10}} {{ puts "OT_OVERLAP $an $bn" }} }}
      }}
    }}
  }}
}}
puts "OT_CHECK insts=$n outside_die=$bad_die not_firm=$bad_status off_site_grid=$bad_grid overlaps=$overlaps"
# ---- pin-on-track (odb, per placed instance class) ----
proc on_track {{v off pitch}} {{ return [expr {{(($v - $off) % $pitch) == 0}}] }}
set m4off [expr {{round(0.012*$dbu)}}]; set m4p [expr {{round(0.048*$dbu)}}]
set m5off [expr {{round(0.012*$dbu)}}]; set m5p [expr {{round(0.048*$dbu)}}]
set classes [dict create]
set pins_checked 0; set pins_off 0; set off_by_master [dict create]
foreach inst [$block getInsts] {{
  set master [[$inst getMaster] getName]
  if {{![string match ot_* $master]}} {{ continue }}
  set o [$inst getOrigin]
  set key "$master,[$inst getOrient],[expr {{[lindex $o 0] % $m5p}}],[expr {{[lindex $o 1] % $m4p}}]"
  if {{[dict exists $classes $key]}} {{ continue }}
  dict set classes $key 1
  set bb [$inst getBBox]
  set bx0 [$bb xMin]; set by0 [$bb yMin]
  set W [[$inst getMaster] getWidth]; set H [[$inst getMaster] getHeight]
  set orient [$inst getOrient]
  foreach mt [[$inst getMaster] getMTerms] {{
    if {{[$mt getSigType] eq "POWER" || [$mt getSigType] eq "GROUND"}} {{ continue }}
    foreach mp [$mt getMPins] {{
      foreach box [$mp getGeometry] {{
        set lay [[$box getTechLayer] getName]
        set px [expr {{([$box xMin] + [$box xMax]) / 2}}]
        set py [expr {{([$box yMin] + [$box yMax]) / 2}}]
        switch $orient {{
          R0 {{ set xc [expr {{$bx0 + $px}}]; set yc [expr {{$by0 + $py}}] }}
          MY {{ set xc [expr {{$bx0 + $W - $px}}]; set yc [expr {{$by0 + $py}}] }}
          MX {{ set xc [expr {{$bx0 + $px}}]; set yc [expr {{$by0 + $H - $py}}] }}
          default {{ set xc [expr {{$bx0 + $W - $px}}]; set yc [expr {{$by0 + $H - $py}}] }}
        }}
        incr pins_checked
        set ok 1
        if {{$lay eq "M4"}} {{ set ok [on_track $yc $m4off $m4p] }}
        if {{$lay eq "M5"}} {{ set ok [on_track $xc $m5off $m5p] }}
        if {{!$ok}} {{ incr pins_off; dict incr off_by_master $master }}
      }}
    }}
  }}
}}
puts "OT_PINS classes=[dict size $classes] checked=$pins_checked off_track=$pins_off by_master=$off_by_master"
puts "OT_TIME check_s=[expr {{[clock seconds]-$t0}}]"
"""
    if tapcell:
        tcl += f"""
set ::env(TAP_CELL_NAME) TAPCELL_ASAP7_75t_R
set ::env(MACRO_ROWS_HALO_X) 2
set ::env(MACRO_ROWS_HALO_Y) 2
if {{[catch {{source {PLAT}/openRoad/tapcell.tcl}} err]}} {{ puts "OT_TAPCELL status=FAIL err=$err" }} else {{
  set nt 0; foreach i [$block getInsts] {{ if {{[string match TAPCELL* [[$i getMaster] getName]]}} {{ incr nt }} }}
  puts "OT_TAPCELL status=PASS taps=$nt rows=[llength [$block getRows]]" }}
if {{[catch {{check_placement -verbose}} err]}} {{ puts "OT_DPLCHECK status=FAIL err=$err" }} else {{ puts "OT_DPLCHECK status=PASS" }}
"""
    if pdn:
        tcl += f"""
set ::env(SCRIPTS_DIR) {FLOW}/scripts
set ::env(REPORTS_DIR) /run
set ::env(RESULTS_DIR) /run
set ::env(LOG_DIR) /run
set ::env(OBJECTS_DIR) /run
set ::env(MACRO_ROWS_HALO_X) 2
set ::env(MACRO_ROWS_HALO_Y) 2
# Rows are cut around macros with the platform halo, as ORFS tapcell does.
if {{!__TAPPED__ && [catch {{cut_rows -halo_width_x 2 -halo_width_y 2}} err]}} {{ puts "OT_CUTROWS status=FAIL err=$err" }} else {{ puts "OT_CUTROWS status=PASS rows=[llength [$block getRows]]" }}
# Platform BLOCKS_grid_strategy.tcl, verbatim except that the macro element grid may exclude
# masters (--pdn-exclude): the HBM PHY abstract's M4 power pins sit under its own M5 OBS (PDN-0006).
set ot_exclude {{__EXCLUDE__}}
proc ot_find_macros_filtered {{}} {{
  global ot_exclude
  set out {{}}
  foreach m [find_macros] {{
    set keep 1
    foreach pat $ot_exclude {{ if {{[string match $pat [[$m getMaster] getName]]}} {{ set keep 0 }} }}
    if {{$keep}} {{ lappend out $m }}
  }}
  return $out
}}
set pdn_src [read [open __PDNTCL__]]
set pdn_src [string map {{"[find_macros]" "[ot_find_macros_filtered]"}} $pdn_src]
if {{[catch {{eval $pdn_src; pdngen}} err]}} {{
  puts "OT_PDN status=FAIL err=$err"
}} else {{
  set nsw 0
  foreach net [$block getNets] {{ foreach sw [$net getSWires] {{ incr nsw [llength [$sw getWires]] }} }}
  puts "OT_PDN status=PASS special_wire_shapes=$nsw"
}}
puts "OT_TIME pdn_s=[expr {{[clock seconds]-$t0}}]"
"""
        if psm:
            tcl += """
foreach net {VDD VSS} {
  if {[catch {check_power_grid -net $net} err]} { puts "OT_PSM net=$net status=FAIL err=$err" } else { puts "OT_PSM net=$net status=PASS" }
}
puts "OT_TIME psm_s=[expr {[clock seconds]-$t0}]"
"""
    tcl = tcl.replace("__EXCLUDE__", exclude).replace("__TAPPED__", "1" if tapcell else "0").replace("__PDNTCL__", pdn_tcl)
    tcl += "exit\n"
    (run / "check.tcl").write_text(tcl)
    return B


def parse(log: str) -> dict:
    out = {}
    for line in log.splitlines():
        if line.startswith("OT_"):
            tag, _, rest = line.partition(" ")
            out.setdefault(tag, []).append(rest)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="expanded_woa")
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--pdn", action="store_true")
    ap.add_argument("--psm", action="store_true")
    ap.add_argument("--memory-gb", type=int, default=60)
    ap.add_argument("--window", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                    help="check only the macros inside this window (um), with tapcells")
    ap.add_argument("--tapcell", action="store_true")
    ap.add_argument("--pdn-tcl", default=f"{PLAT}/openRoad/pdn/BLOCKS_grid_strategy.tcl",
                    help="PDN script (container path); repo scripts are mounted at /src/tools/chip_assembly/tcl")
    ap.add_argument("--pdn-exclude", default="", help="space-separated master globs left out of the macro element grid")
    ap.add_argument("--refit", type=Path, help="a re-fit record (tools/v41_floorplan_refit.py): check that floorplan")
    ap.add_argument("--hbm-phy", default=None, help="HBM PHY view to place (W18: the legal v2 abstract)")
    a = ap.parse_args()
    if a.hbm_phy:
        PK.HBM_PHY = a.hbm_phy
    if a.refit:
        PK.REFIT = json.loads(a.refit.read_text())["geometry"]["refit"]
    run = a.run_dir.resolve()
    prepare(a.variant, run, a.pdn, a.psm, a.pdn_exclude, a.window, a.tapcell, a.pdn_tcl)
    img = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"], capture_output=True,
                         text=True, check=True).stdout.strip()
    cmd = ["docker", "run", "--rm", f"--memory={a.memory_gb}g", "--name", f"ot_w1_fpcheck_{os.getpid()}",
           "-v", f"{run}:/run", "-v", f"{PK.MACRO_DIR}:/work/macros:ro",
           "-v", f"{ROOT / 'tools/chip_assembly/tcl'}:/src/tools/chip_assembly/tcl:ro", IMAGE,
           "bash", "-c", f"/usr/bin/time -v {OPENROAD} -exit -no_init /run/check.tcl > /run/openroad.log 2>&1; echo rc=$?"]
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    log = (run / "openroad.log").read_text() if (run / "openroad.log").exists() else ""
    tags = parse(log)
    peak = next((l.split(":")[1].strip() for l in log.splitlines() if "Maximum resident set size" in l), None)
    check = dict(kv.split("=") for kv in tags.get("OT_CHECK", [""])[0].split() if "=" in kv)
    pins = tags.get("OT_PINS", [""])[0]
    pdn = tags.get("OT_PDN", [None])[0]
    psm = tags.get("OT_PSM", [])
    rec = dict(schema="opentallas.v41.floorplan_orfs_check.v1", variant=a.variant,
               refit=(str(a.refit), hashlib.sha256(a.refit.read_bytes()).hexdigest()) if a.refit else None,
               hbm_phy=PK.HBM_PHY, pdn_exclude=a.pdn_exclude, pdn_tcl=a.pdn_tcl, window=a.window, tapcell=a.tapcell,
               tapcell_result=None,
               image=IMAGE, image_id=img, openroad=OPENROAD, wall_s=round(time.time() - t, 1),
               peak_rss_kb=peak, docker_rc=r.returncode, stdout_tail=r.stdout[-200:],
               inputs_sha256={n: hashlib.sha256((run / n).read_bytes()).hexdigest()
                              for n in ("check.tcl", "macros.tcl", "top.def")},
               source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__).resolve(), Path(PK.__file__).resolve())},
               check={k: int(v) for k, v in check.items()}, overlaps_listed=tags.get("OT_OVERLAP", []),
               pins=pins, pdn=pdn, psm=psm, stats=tags.get("OT_STAT", []), times=tags.get("OT_TIME", []),
               errors=[l for l in log.splitlines() if l.startswith("[ERROR")][:20],
               scope="floorplan-only: macros, rows, tracks, platform macro PDN; no std cells, tapcells, route")
    c = rec["check"]
    rec["placement_legal"] = bool(c) and c.get("outside_die") == 0 and c.get("overlaps") == 0 and \
        c.get("not_firm") == 0 and c.get("off_site_grid") == 0
    rec["tapcell_result"] = tags.get("OT_TAPCELL", [None])[0]
    rec["dpl_check"] = tags.get("OT_DPLCHECK", [None])[0]
    rec["cut_rows"] = tags.get("OT_CUTROWS", [None])[0]
    rec["pdn_generated"] = bool(pdn and pdn.startswith("status=PASS"))
    rec["power_grid_connected"] = bool(psm) and all("status=PASS" in x for x in psm)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("check", "pins", "pdn", "psm", "placement_legal", "pdn_generated", "power_grid_connected", "peak_rss_kb", "wall_s", "errors")}, indent=1))


if __name__ == "__main__":
    main()
