# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
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

read_db /data/ctlm_r6_first_gpl_failed.odb
set b [ord::get_db_block];set units [$b getDbUnitsPerMicron]
source /src/physical/common_flow/assigned_pin_exact.tcl
set f [open /data/ctlm_nativecmd_E_recut_proposal.tcl r];set lines [read $f];close $f
set changed 0
foreach line [split $lines "\n"] {
 if {![string match ot_assigned_pin_exact* $line]} continue
 set name [lindex $line 1];set bt [$b findBTerm $name]
 foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
 eval $line;incr changed
}
if {$changed!=380} {error "reachmodel missingbusbits$changed"}
source /data/ctlm_proposal_audit_pins.tcl
set hard [$b findInst u_hr];set max 0;set worst {}
foreach line [split $lines "\n"] {
 if {![string match ot_assigned_pin_exact* $line]} continue
 set name [lindex $line 1];set it [$hard findITerm $name]
 if {$it eq "NULL"} {error "reachmodel hardportmissing$name"}
 set h [$it getBBox];set bt [$b findBTerm $name];set box [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
 set dx [expr {abs(([$h xMin]+[$h xMax]-[$box xMin]-[$box xMax])/2.0/$units)}]
 set dy [expr {abs(([$h yMin]+[$h yMax]-[$box yMin]-[$box yMax])/2.0/$units)}]
 set d [expr {$dx+$dy}];if {$d>$max} {set max $d;set worst $name}
}
puts "CTLM_NATIVE_CMD_E_GEOMETRY actual_ports=$changed max_fixed_macro_to_parent_pin_manhattan_um=$max worst=$worst hard_orientation=[$hard getOrient] actual_grid_and_PG_audit=PASS no_placement_or_CTS=1 adoption=0"
