# QC-PHYS 2026-10-25: routed (6_final + RCX spef) FF/TT clock + hold-path + slew dump of qfd_dv_s8_crh_rp1 f56c
set C $::env(OT_CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /ml0/ot_sram_1r1w_1024x256_m2_r2c2_[string tolower $C].lib
read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
set f [open /out/routed_[string tolower $C].tsv w]
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.2f [expr {$v / double($::dbu)}]] }
set die [$blk getDieArea]
puts $f "DIE\t[um [$die xMin]]\t[um [$die yMin]]\t[um [$die xMax]]\t[um [$die yMax]]"
foreach i [$blk getInsts] {
  set m [$i getMaster]; set mn [$m getName]; set bb [$i getBBox]
  set kind std; if {[$m isBlock]} { set kind macro } elseif {[string match "*DFF*" $mn]} { set kind ff } elseif {[string match "ot_c*" [$i getName]] || [string match "clkbuf*" [$i getName]]} { set kind ck } else { continue }
  puts $f "INST\t[$i getName]\t$mn\t$kind\t[um [$bb xMin]]\t[um [$bb yMin]]\t[um [$bb xMax]]\t[um [$bb yMax]]"
}
# tap of a clock pin: walk drivers up to an ot_ctap_*/ot_cleaf_* cell or the port
proc tapof {p} {
  set path {}
  for {set k 0} {$k < 30} {incr k} {
    set n [get_nets -quiet -of_objects [get_pins $p]]; if {$n eq ""} break
    set d [get_pins -quiet -of_objects $n -filter "direction==output"]
    if {$d eq ""} { return [concat $path PORT] }
    set ci [get_full_name [get_cells -of_objects $d]]
    if {[string match "ot_ctap_*" $ci] || [string match "ot_cleaf_*" $ci]} { lappend path $ci }
    if {[string match "ot_ctap_*" $ci]} { return $path }
    set ins [get_pins -quiet -of_objects [get_cells $ci] -filter "direction==input"]
    if {$ins eq ""} break
    set p [get_full_name [lindex $ins 0]]
  }
  return [concat $path ROOT]
}
foreach p [all_registers -clock_pins] { puts $f "CK\t[get_full_name $p]\t[get_property $p arrival_max_rise]\t[get_property $p arrival_min_rise]\t[tapof [get_full_name $p]]" }
foreach pa [find_timing_paths -path_delay min -group_path_count 400 -endpoint_path_count 1 -slack_max 0] {
  set ep [get_full_name [get_property $pa endpoint]]; set sp [get_full_name [get_property $pa startpoint]]
  puts $f "HOLD\t$ep\t$sp\t[get_property $pa slack]"
}
puts $f "WNS\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]\t[sta::time_sta_ui [sta::worst_slack_cmd max]]"
report_check_types -max_slew -violators > /out/slew_[string tolower $C].rpt
foreach n [get_nets *] {
  set d [get_pins -quiet -of_objects $n -filter "direction==output"]; if {$d eq ""} continue
  set s 0; catch {set s [get_property [lindex $d 0] slew_max]}
}
close $f
puts DUMP_DONE
