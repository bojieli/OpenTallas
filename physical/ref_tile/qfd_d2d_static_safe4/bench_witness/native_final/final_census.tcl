# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_FF*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w]} {set w [string map {_tt.lib _ff.lib} $w];if {![file exists $w]} {error "missingactualFFlib $w"};read_liberty $w}
  }
}

read_db /data/eclock_control16_sramclk_hold_final_ff.odb

set b [ord::get_db_block]
set u [expr {double([$b getDbUnitsPerMicron])}]
set f [open /data/final_census.tsv w]
puts $f "name\tmaster\tblock\tarea_um2\tx_um\ty_um\tstatus"
foreach i [$b getInsts] {
 set m [$i getMaster];set bb [$i getBBox]
 puts $f "[$i getName]\t[$m getName]\t[$m isBlock]\t[expr {[$m getWidth]*double([$m getHeight])/$u/$u}]\t[expr {[$bb xMin]/$u}]\t[expr {[$bb yMin]/$u}]\t[$i getPlacementStatus]"
}
close $f
if {"final_census" eq "final_census"} {
 set ::env(OT_LAYOUT_OUT) /data/d2d_native_final_placement.json
 set ::env(OT_LAYOUT_TOP) "D2D source-safe prototype; placement RC only; adoption=false"
 set ::env(OT_LAYOUT_CLOCKS) ck
 source /src/tools/ref_tile/layout_dump.tcl
}
exit
