# FACEHOLD-S81 (DIE-S81-85 11-10) read-only FF hold census, appended to the row's own signoff FF session.tcl cut just
# before "so_timing STD" (same libs, odb, spef, golden sdc, uncertainty policy, vclk pin_flop_mean reference and the
# in_min -40 / out_min 0 overlay).  No constraint or netlist change.  One line per violating endpoint (worst path), plus
# register-launched violators hidden behind a worse port path; then full_clock_expanded reports of the worst paths of
# each class for the decomposition.
proc fh_kind {pin} {
  if {[$pin is_top_level_port]} { return port }
  return pin
}
set fh_out [open /out/census.tsv w]
puts $fh_out "set\tslack\tstart\tstart_kind\tstart_clock\tend\tend_kind\tend_clock\tgroup"
set fh_all [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0]
foreach pe $fh_all {
  set sl [get_property $pe slack]
  if {$sl >= 0} continue
  set sp [get_property $pe startpoint]; set ep [get_property $pe endpoint]
  set sc [get_property $pe startpoint_clock]; set ec [get_property $pe endpoint_clock]
  set scn [expr {$sc eq "" ? "-" : [get_full_name $sc]}]; set ecn [expr {$ec eq "" ? "-" : [get_full_name $ec]}]
  puts $fh_out "all\t[format %.2f $sl]\t[get_full_name $sp]\t[fh_kind $sp]\t$scn\t[get_full_name $ep]\t[fh_kind $ep]\t$ecn\t-"
}
unset fh_all
set fh_regs [all_registers -clock_pins]
if {[llength $fh_regs]} {
  foreach pe [find_timing_paths -path_delay min -from $fh_regs -group_path_count 200000 -endpoint_path_count 1 -slack_max 0] {
    set sl [get_property $pe slack]
    if {$sl >= 0} continue
    set sp [get_property $pe startpoint]; set ep [get_property $pe endpoint]
    set sc [get_property $pe startpoint_clock]; set ec [get_property $pe endpoint_clock]
    set scn [expr {$sc eq "" ? "-" : [get_full_name $sc]}]; set ecn [expr {$ec eq "" ? "-" : [get_full_name $ec]}]
    puts $fh_out "reg\t[format %.2f $sl]\t[get_full_name $sp]\t[fh_kind $sp]\t$scn\t[get_full_name $ep]\t[fh_kind $ep]\t$ecn\t-"
  }
}
close $fh_out
puts "FH_BEGIN WORST_ALL"
report_checks -path_delay min -group_path_count 6 -endpoint_path_count 1 -format full_clock_expanded -digits 2
puts "FH_END"
puts "FH_BEGIN WORST_REG"
if {[llength $fh_regs]} {
  report_checks -path_delay min -from $fh_regs -group_path_count 12 -endpoint_path_count 1 -format full_clock_expanded -digits 2 -fields {input_pin}
}
puts "FH_END"
puts "FH_BEGIN WORST_TO_OUT"
report_checks -path_delay min -to [all_outputs] -group_path_count 3 -endpoint_path_count 1 -format full_clock_expanded -digits 2
puts "FH_END"
puts "FH_DONE"
