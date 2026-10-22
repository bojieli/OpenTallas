# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
source /src/tools/ref_tile/cross_clock_paths.tcl
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner tt
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc (TT placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}

source /audit/clock_graph.tcl
ot_gq_clock_graph 1
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set regions {}
dict for {it tag} $::ot_gq_expected {
  set inst [$it getInst];set box [$inst getBBox]
  set x [expr {0.5*([$box xMin]+[$box xMax])/$dbu}]
  set y [expr {0.5*([$box yMin]+[$box yMax])/$dbu}]
  set col [expr {min(2,int($x/144.0))}];set row [expr {$y>=172.8?1:0}]
  set key r${row}c${col};dict incr regions ${key}_sinks
  if {[lindex $tag 1]} {dict incr regions ${key}_native}
  if {[lindex $tag 0] eq "macro"} {puts "SMH_REGION_MACRO name=[$inst getName] x=$x y=$y region=$key"}
  set n [$inst getName]
  if {[string match {*ra_n*} $n]} {puts "SMH_REGION_RADDR name=$n x=$x y=$y region=$key"}
}
puts "SMH_REGION_COUNTS $regions"
exit
