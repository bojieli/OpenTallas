# prebuild_gate.sh STA step: TT setup, ideal clocks at the planned insertion latency (GATE_CLK_LAT, the kit's OT_VCLK_TT,
# so IO paths see the same budget as after CTS), placement parasitics from the kit RC (none on the synth fallback).
foreach l $::env(GATE_LIBS) { read_liberty $l }
read_db $::env(GATE_ODB)
read_sdc $::env(GATE_SDC)
set stage $::env(GATE_STAGE)
if {$stage ne "synth_zero_wire"} {
  if {$::env(GATE_RC) ne "" && [file exists $::env(GATE_RC)]} { source $::env(GATE_RC) }
  estimate_parasitics -placement
}
foreach c [all_clocks] {
  if {[llength [get_property $c sources]]} { set_clock_latency $::env(GATE_CLK_LAT) $c }
}
set blk [ord::get_db_block]
set n 0; set nm 0; set a 0.0
foreach i [$blk getInsts] {
  set m [$i getMaster]
  if {[$m getType] eq "BLOCK"} { incr nm } else { incr n; set a [expr {$a + [$m getWidth]*[$m getHeight]}] }
}
set dbu [$blk getDbUnitsPerMicron]
puts "GATE cells $n macros $nm stdcell_area_um2 [format %.1f [expr {$a/$dbu/$dbu}]] stage $stage"
proc worst {tag args} {
  set p [find_timing_paths -path_delay max -group_path_count 1 {*}$args]
  if {[llength $p] == 0} { puts "GATE group $tag none"; return }
  set x [lindex $p 0]
  puts "GATE group $tag slack [format %.1f [get_property $x slack]] start [get_full_name [get_property $x startpoint]] end [get_full_name [get_property $x endpoint]]"
}
puts "GATE period [get_property [lindex [all_clocks] 0] period]"
worst r2r -from [all_registers -clock_pins] -to [all_registers -data_pins]
worst in2reg -from [all_inputs] -to [all_registers -data_pins]
worst reg2out -from [all_registers -clock_pins] -to [all_outputs]
worst in2out -from [all_inputs] -to [all_outputs]
set over [find_timing_paths -path_delay max -group_path_count 200000 -endpoint_path_count 1 -slack_max 250.0 \
  -from [all_registers -clock_pins] -to [all_registers -data_pins]]
puts "GATE r2r_endpoints_stage_over_583 [llength $over]"
puts "GATE_TOP_BEGIN"
report_checks -path_delay max -group_path_count 25 -endpoint_path_count 1 -format end
puts "GATE_TOP_END"
puts "GATE_WORST_BEGIN"
report_checks -path_delay max -fields {fanout} -digits 1
puts "GATE_WORST_END"
