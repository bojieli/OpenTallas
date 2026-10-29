# DIE-HEAD-20: ring clocks of the fwd_buffer hd_tile (DH19 kit lineage), GRT RC SPEF.  = NUMBER-CHECK-HEAD-1 ncmeas.tcl
# (all register CK pins) + DIE-HEAD-18 h18_fwdmeas.tcl (fclk_out_o driver chain), one session per corner.
set c $::env(CORNER)
set pat [expr {$c eq "TT" ? "*RVT_TT*" : "*RVT_FF*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] { read_liberty $l }
foreach l [glob /work/macros/*_[string tolower $c].lib] { read_liberty $l }
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
read_spef $::env(SPEF)
catch {delete_generated_clock [get_clocks fclk_out_o]}
report_worst_slack -max
set out [open /out/$c.ck w]
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || [string match *INF* $a]} { puts $out "NOARR [get_full_name $p]"; continue }
  puts $out "CK [get_full_name $p] $a [get_property $p arrival_min_rise] [get_property [get_cells -of_objects $p] ref_name]"
}
close $out
set out [open /out/fwd_$c.txt w]
foreach pn {clk fclk_in_i fclk_out_o} {
  set bt [[ord::get_db_block] findBTerm $pn]
  set bb [[lindex [$bt getBPins] 0] getBBox]
  puts $out "PORT $pn xy [expr [$bb xMin]/1000.0] [expr [$bb yMin]/1000.0]"
}
proc drv {netname} {
  foreach pp [get_pins -of_objects [get_nets $netname]] { if {[get_property $pp direction] eq "output"} { return $pp } }
  return ""
}
set net fclk_out_o
for {set k 0} {$k < 40} {incr k} {
  set d [drv $net]
  if {$d eq ""} { puts $out "CHAIN end net $net (no driver pin)"; break }
  set cell [get_cells -of_objects $d]
  set loc [[ord::get_db_block] findInst [get_full_name $cell]]
  if {$loc eq "NULL" || $loc eq ""} { set xy {-1000 -1000} } else { set bb [$loc getBBox]; set xy [list [$bb xMin] [$bb yMin]] }
  puts $out "CHAIN $k [get_full_name $d] [get_property $cell ref_name] xy [expr [lindex $xy 0]/1000.0] [expr [lindex $xy 1]/1000.0] out_max [get_property $d arrival_max_rise] out_min [get_property $d arrival_min_rise] net $net npins [llength [get_pins -of_objects [get_nets $net]]]"
  set in [lindex [get_pins -of_objects $cell -filter "direction==input"] 0]
  set net [get_full_name [get_nets -of_objects $in]]
}
foreach pp [get_pins -of_objects [get_nets fclk_out_o]] { puts $out "NETPIN [get_full_name $pp] [get_property $pp direction] amax [get_property $pp arrival_max_rise] amin [get_property $pp arrival_min_rise]" }
close $out
puts "MEAS20 done $c"
