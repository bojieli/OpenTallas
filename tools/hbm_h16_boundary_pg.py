#!/usr/bin/env python3
"""Emit the measured-checkpoint H16 PG hook; never change a macro or clock."""
import argparse
import json
from pathlib import Path


def hook_tcl(geometry):
    patches = geometry['patches']
    assert len(patches) == 4
    via_names = {p['native_tech_via'] for p in patches}
    assert via_names == {'VIA23'}
    rail_vias = geometry['M1_M2_rail_vias']
    assert len(rail_vias) == 4
    assert all(v['native_block_via'] == 'via1_2_324_18_1_9_36_36' for v in rail_vias)
    rail_x = [round(v['x_um']*1000) for v in rail_vias]
    coords = []
    for p in patches:
        x = round(p['x_um']*1000)
        assert abs(x/1000-p['x_um']) < 1e-9
        coords.append(x)
    return '''# Source AFTER the original H16 pdngen, BEFORE placement/CTS.
# Qualified on retained d42ab0308 pdn_finite_selected.odb, no grid rebuild.
# Original M6 macro feeds, M8/M9, all taps, RTL and clocks remain unchanged.
# Connectivity qualification only: no routed DRC/EM/loaded-IR/timing credit.
if {[info exists ::ot_h16_boundary_vss_applied]} {
  error "H16 VSS stitches already applied in this OpenROAD session"
}
set ot_b [ord::get_db_block]
set ot_t [ord::get_db_tech]
if {[$ot_b getDbUnitsPerMicron] != 1000} {error "H16 PG requires native 1000 DBU/um"}
set ot_c [$ot_b getCoreArea]
if {[$ot_c xMin] != 0 || [$ot_c yMin] != 0 ||
    [$ot_c xMax] != 1349082 || [$ot_c yMax] != 1349730} {
  error "H16 PG hook requires actual qualified 1349.082 x 1349.730 core"
}
set ot_vss [$ot_b findNet VSS]
set ot_m2 [$ot_t findLayer M2]
set ot_m3 [$ot_t findLayer M3]
set ot_v23 [$ot_t findVia VIA23]
if {$ot_vss == "NULL" || $ot_m2 == "NULL" || $ot_m3 == "NULL" || $ot_v23 == "NULL"} {
  error "H16 PG requires actual VSS/M2/M3/VIA23"
}
set ot_v12 [$ot_b findVia via1_2_324_18_1_9_36_36]
if {$ot_v12 == "NULL"} {error "H16 PG requires retained native M1/M2 rail via array"}
set ot_xgrid [[$ot_b findTrackGrid $ot_m3] getGridX]
set ot_stitch_x {'''+' '.join(str(x) for x in coords)+'''}
foreach ot_x $ot_stitch_x {
  if {[lsearch -exact $ot_xgrid $ot_x] < 0} {error "H16 VSS bridge off actual M3 grid"}
}
set ot_sw [odb::dbSWire_create $ot_vss ROUTED]
foreach ot_x $ot_stitch_x {
  # Legal .090-square M2 landing overlaps original ground rail y=-.009..+.009.
  # Upper landing is the existing connected VSS M2 rail at y=.540.
  odb::dbSBox_create $ot_sw $ot_m2 [expr {$ot_x-45}] -9 [expr {$ot_x+45}] 81 STRIPE
  odb::dbSBox_create $ot_sw $ot_m3 [expr {$ot_x-45}] 18 [expr {$ot_x+45}] 558 STRIPE
  odb::dbSBox_create $ot_sw $ot_v23 $ot_x 36 STRIPE
  odb::dbSBox_create $ot_sw $ot_v23 $ot_x 540 STRIPE
}
# Native 9-cut rail array: M1 y=-.009..+.009, M2 same y.
# Reuse the array already used on the connected .540 rail; no outward growth.
foreach ot_x {'''+' '.join(str(x) for x in rail_x)+'''} {
  odb::dbSBox_create $ot_sw $ot_v12 $ot_x 0 STRIPE
}
set ::ot_h16_boundary_vss_applied 1
puts "OT_H16_BOUNDARY_VSS_STITCHES 4; native V1 rail arrays 4 / cuts 36; VIA23 8; M6-M9 unchanged"
'''


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--geometry', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(hook_tcl(json.loads(args.geometry.read_text())))
