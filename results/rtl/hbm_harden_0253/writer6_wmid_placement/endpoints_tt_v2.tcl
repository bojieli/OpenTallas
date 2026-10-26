set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

foreach c [all_clocks] {
  if {![llength [get_property $c sources]]} continue
  set_clock_latency -source 0 $c
  puts "OT_CK_RAW_SOURCE [get_full_name $c]"
}

set ::ot_ck_act [dict create]
proc ot_ck_active {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return "" }
  set k "[get_property $c ref_name]/[get_property $p lib_pin_name]"
  if {[dict exists $::ot_ck_act $k]} { return [dict get $::ot_ck_act $k] }
  sta::redirect_string_begin
  catch {report_edges -from $p}
  set r [sta::redirect_string_end]
  set on 0; set fr {}
  foreach l [split $r "\n"] {
    if {[regexp {^\S} $l]} { set on [regexp {(Clk|En) to Q} $l]; continue }
    if {$on && [regexp {^\s+([\^v])\s+->} $l -> e]} { if {[lsearch -exact $fr $e] < 0} { lappend fr $e } }
  }
  set a [expr {[llength $fr] == 1 ? ([lindex $fr 0] eq "^" ? "r" : "f") : ""}]
  dict set ::ot_ck_act $k $a
  return $a
}
proc ot_ck_arr {p clk} {
  set half 0.0
  if {![catch {list [$clk waveform] [$clk period] [get_property $clk period]} w]} {
    lassign $w wf ps pu
    if {[llength $wf] >= 2 && $ps > 0} { set half [expr {([lindex $wf 1] - [lindex $wf 0]) * $pu / $ps}] } }
  set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
  set okr [string is double -strict $ar]; set okf [string is double -strict $af]
  if {!($okr && $okf)} { return [expr {$okr ? $ar : ($okf ? $af : "")}] }
  set t [ot_ck_active $p]
  set lo [expr {$ar <= $af ? "r" : "f"}]
  if {$t eq ""} { set t $lo }
  set v [expr {$t eq "r" ? $ar : $af}]
  return [expr {$t eq $lo ? $v : $v - $half}]
}

set bnd {}
set din [all_inputs -no_clocks]
foreach pe [find_timing_paths -path_delay max -from $din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {dict set bnd [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}] 1}
foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {dict set bnd [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}] 1}
set f [open /out/clock_endpoints.tsv w]
puts $f "clock	source	pin	boundary	arrival_ps	x_dbu	y_dbu	master"
foreach c [all_clocks] {
 set src [get_property $c sources]
 if {![llength $src]} continue
 foreach p [all_registers -clock_pins -clock $c] {
  set name [get_full_name $p];set i [regsub {/[^/]+$} $name {}]
  set a [ot_ck_arr $p $c]
  set inst [sta::sta_to_db_inst [lindex [get_cells -of_objects $p] 0]]
  if {$inst eq "NULL"} {error "No instance $i"}
  lassign [$inst getLocation] x y
  puts $f "[get_full_name $c]	[get_full_name [lindex $src 0]]	$name	[dict exists $bnd $i]	$a	$x	$y	[[$inst getMaster] getName]"
 }
}
close $f
puts "CLOCK_ENDPOINT_DIAGNOSTIC_DONE"
exit
