# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set sm_corner $::env(SM_CORNER)
set sm_upper [string toupper $sm_corner]
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_${sm_upper}*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner $sm_corner
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc ($sm_corner libraries / TT placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}

# Clear DATA annotations from actual clock-source ports for every reference edge.
# Ordinary input/output DATA budgets are untouched; no ordinary-data qualification is inferred.
foreach c [all_clocks] {
 foreach src [get_property $c sources] {
  set sn [get_full_name $src]
  if {![llength [get_ports -quiet $sn]]} continue
  foreach ref [all_clocks] {
   unset_input_delay -clock $ref [get_ports $sn]
   unset_input_delay -clock $ref -clock_fall [get_ports $sn]
  }
  unset_input_delay [get_ports $sn]
 }
 set_clock_latency -source 0 $c
}
# Match the published export's boundary-register mean selection, using actual CTS pins.
set selected [get_clocks core_clk]
set regs {}
foreach p [all_registers -clock_pins -clock $selected] {dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] [get_full_name $p]}
set bnd {}
set din [all_inputs -no_clocks]
foreach pe [find_timing_paths -path_delay max -from $din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
 set i [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}]
 if {[dict exists $regs $i]} {dict set bnd $i 1}
}
foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
 set i [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}]
 if {[dict exists $regs $i]} {dict set bnd $i 1}
}
set vals {}; set bvals {}
dict for {i cp} $regs {
 set a [get_property [get_pins $cp] arrival_max_rise]
 if {![string is double -strict $a]} {error "missing original OWN clock arrival $cp"}
 lappend vals $a
 if {[dict exists $bnd $i]} {lappend bvals $a}
}
if {[llength $vals]!=993 || ![llength $bvals]} {error "wrong actual original OWN register population"}
set sum 0; foreach a $bvals {set sum [expr {$sum+$a}]}
set ownR [expr {$sum/[llength $bvals]}]
puts "SM_NATIVE_GATE_OWN_REF $sm_corner actual_source_snapshot boundary_n=[llength $bvals] original_n=[llength $vals] R=$ownR all_min=[lindex [lsort -real $vals] 0] all_max=[lindex [lsort -real $vals] end]"
foreach clk {core_clk enable_commit enable_commit_aux} {set_clock_latency -source [expr {-$ownR}] [get_clocks $clk]}
foreach pin {u_enable_mirror/CLK u_enable_aux_mirror/CLK} {
 set p [get_pins $pin]
 puts "SM_NATIVE_GATE_COMMIT $sm_corner $pin normalized_arrival=[get_property $p arrival_max_rise] insertion=[expr {[get_property $p arrival_max_rise]+$ownR}] slew=[get_property $p slew_max_rise]"
}
array set childR_0 {tt 180.9 ff 148.0 ss 236.9}
array set childCap_0 {tt 10.6328 ff 10.8898 ss 10.4681}
array set childR_1 {tt 171.4 ff 139.6 ss 225.5}
array set childCap_1 {tt 11.2287 ff 11.4858 ss 11.0641}
array set childR_2 {tt 171.4 ff 139.6 ss 225.5}
array set childCap_2 {tt 11.2287 ff 11.4858 ss 11.0641}
array set childR_3 {tt 175.8 ff 143.1 ss 231.1}
array set childCap_3 {tt 11.3663 ff 11.6234 ss 11.2017}
array set childR_4 {tt 315.0 ff 261.4 ss 402.8}
array set childCap_4 {tt 18.592 ff 19.1062 ss 18.2628}
array set childR_5 {tt 180.9 ff 148.0 ss 236.9}
array set childCap_5 {tt 10.6328 ff 10.8898 ss 10.4681}
array set childR_6 {tt 171.4 ff 139.6 ss 225.5}
array set childCap_6 {tt 11.2287 ff 11.4858 ss 11.0641}
array set childR_7 {tt 171.4 ff 139.6 ss 225.5}
array set childCap_7 {tt 11.2287 ff 11.4858 ss 11.0641}
array set childR_8 {tt 175.8 ff 143.1 ss 231.1}
array set childCap_8 {tt 11.3663 ff 11.6234 ss 11.2017}
array set childR_9 {tt 315.0 ff 261.4 ss 402.8}
array set childCap_9 {tt 18.592 ff 19.1062 ss 18.2628}
array set childR_10 {tt 339.6 ff 281.0 ss 434.8}
array set childCap_10 {tt 18.7557 ff 19.0145 ss 18.5886}
array set childR_11 {tt 429.0 ff 350.8 ss 557.0}
array set childCap_11 {tt 10.99 ff 11.1185 ss 10.9067}
# Existing actual source SDC loads each port with the immutable corresponding CLOSED child clk cap.
# Child external entry wire remains 0 in this own-only placement diagnostic.
for {set i 0} {$i<12} {incr i} {
 set cr [set childR_${i}($sm_corner)]
 set p [get_pins u_child_icg_$i/GCLK]
 set entry [get_property $p arrival_max_rise]
 set fall [expr {[get_property $p arrival_max_fall]-416.6665}]
 set slew [get_property $p slew_max_rise]
 set source [expr {-$cr-$entry}]
 set_clock_latency -source $source [get_clocks child_raw_$i]
 set phi [expr {[get_property $p arrival_max_rise]+$cr}]
 if {abs($phi)>0.03} {error "child boundary phase mismatch $i $phi"}
 puts "SM_NATIVE_GATE_CAL $sm_corner $i childR=$cr cap=[set childCap_${i}($sm_corner)] entry_rise=$entry entry_fall=$fall RAW_source=$source GCLK_slew=$slew phi=$phi"
 # Freeze the actual TT level classification, including measured real local clock insertion.
 if {$sm_corner eq "tt"} {
  set smU($i) [expr {max($ownR,$cr+$entry)>300 ? 210 : 150}]
 } else {
  source /probe/actual_gate_TT_levels.tcl
 }
 foreach launch {enable_commit enable_commit_aux} {
  set_clock_uncertainty -setup $smU($i) -from [get_clocks $launch] -to [get_clocks child_raw_$i]
  set_clock_uncertainty -hold 100 -from [get_clocks $launch] -to [get_clocks child_raw_$i]
 }
}
if {$sm_corner eq "tt"} {
 set f [open /probe/actual_gate_TT_levels.tcl w]
 for {set i 0} {$i<12} {incr i} {puts $f "set smU($i) $smU($i)"}
 close $f
}
for {set i 0} {$i<12} {incr i} {
 set launch [expr {$i in {4 9 10 11} ? "u_enable_mirror/QN" : "u_enable_aux_mirror/QN"}]
 set expected [expr {$i in {4 9 10 11} ? "enable_commit" : "enable_commit_aux"}]
 foreach edge {rise fall} {
  foreach kind {max min} {
   set cmd [list find_timing_paths -from [get_pins $launch] -${edge}_to [get_pins u_child_icg_$i/ENA] -path_delay $kind -group_path_count 1]
   set paths [{*}$cmd]
   if {[llength $paths]!=1} {error "missing actual ENA gating $i $edge $kind"}
   set path [lindex $paths 0]
   set sc [get_full_name [get_property $path startpoint_clock]]
   set ec [get_full_name [get_property $path endpoint_clock]]
   if {$sc ne $expected || $ec ne "child_raw_$i"} {error "wrong actual gating association $i $sc $ec"}
   puts "SM_NATIVE_GATE_PATH $sm_corner $i $edge $kind slack=[get_property $path slack] launch=$sc capture=$ec U=$smU($i) H=100"
  }
 }
}
report_checks -to [get_pins u_child_icg_*/ENA] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 24 -digits 6
report_checks -to [get_pins u_child_icg_*/ENA] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 24 -digits 6
report_check_types -min_pulse_width -verbose
write_sdc /probe/actual_gate_executed_$sm_corner.sdc
puts "SM_NATIVE_GATE_DONE $sm_corner ACTUAL_CTS_OWN_PLACEMENT_RC_CHILD_CLK_CAP_ZERO_EXTERNAL_ENTRY_SOURCE0_CALIBRATION_OPEN"
exit
