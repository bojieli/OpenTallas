from pathlib import Path
p=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones')
prefix=(p/'d2d_baseline_electrical_ff.tcl').read_text().split('read_db ')[0]
body='''
set b [ord::get_db_block]
set u [expr {double([$b getDbUnitsPerMicron])}]
set f [open /data/CENSUS.tsv w]
puts $f "name\\tmaster\\tblock\\tarea_um2\\tx_um\\ty_um\\tstatus"
foreach i [$b getInsts] {
 set m [$i getMaster];set bb [$i getBBox]
 puts $f "[$i getName]\\t[$m getName]\\t[$m isBlock]\\t[expr {[$m getWidth]*double([$m getHeight])/$u/$u}]\\t[expr {[$bb xMin]/$u}]\\t[expr {[$bb yMin]/$u}]\\t[$i getPlacementStatus]"
}
close $f
if {"CENSUS" eq "final_census"} {
 set ::env(OT_LAYOUT_OUT) /data/d2d_native_final_placement.json
 set ::env(OT_LAYOUT_TOP) "D2D source-safe prototype; placement RC only; adoption=false"
 set ::env(OT_LAYOUT_CLOCKS) ck
 source /src/tools/ref_tile/layout_dump.tcl
}
exit
'''
for name,db in [('original_census','$base/4_1_cts.odb'),('control_baseline_census','/data/eclock_three_stage_ff_hold_repaired.odb'),('final_census','/data/eclock_control16_sramclk_hold_final_ff.odb')]:
 (p/f'{name}.tcl').write_text(prefix+f'read_db {db}\n'+body.replace('CENSUS',name))
