
set C FF
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*] { read_liberty $f }
foreach f [glob -nocomplain /x/none] { if {[string match -nocase "*_ff.lib" $f]} { read_liberty $f } }
read_db /b/6_final.odb
read_sdc /o/boundary.sdc
read_spef /b/6_final.spef
set_propagated_clock [all_clocks]
set ck [lindex [all_clocks] 0]
set clkn {}
foreach s [get_property $ck sources] { lappend clkn [get_full_name $s] }
set ins {}
foreach p [all_inputs] { if {[lsearch -exact $clkn [get_full_name $p]] < 0} { lappend ins $p } }
set_input_delay 0 -clock $ck $ins
set_output_delay 0 -clock $ck [all_outputs]
set fo [open /o/window_${C}.tsv w]
set chk [expr {"$C" eq "FF" ? "min" : "max"}]
set prop [expr {"$C" eq "FF" ? "slack_min" : "slack_max"}]
proc ot_sl {p prop} {
  set bt [[ord::get_db_block] findBTerm [get_full_name $p]]
  if {$bt eq "NULL"} { return inf }
  set n [$bt getNet]
  if {$n eq "NULL" || [llength [$n getITerms]] == 0} { return inf }
  return [string tolower [get_property $p $prop]]
}
foreach p $ins { puts $fo "in\t[get_full_name $p]\t[ot_sl $p $prop]" }
foreach p [all_outputs] { puts $fo "out\t[get_full_name $p]\t[ot_sl $p $prop]" }
close $fo
write_timing_model -library_name ot_dsrom_su_norm_ff /o/ot_dsrom_su_norm_ff.lib
set_false_path -from $ins
set_false_path -to [all_outputs]
report_worst_slack -$chk
puts "OT_WINDOW_DONE FF"
