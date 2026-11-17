# HOLD-FLOW-R 11-16: endpoint table for hold_eco_internal.py plan.  Source in a routed STA session that has the FF and TT
# modes (ot_mm: set_mode ff / tt) or pass OT_HEI_FF_MODE / OT_HEI_TT_MODE.  Writes OT_HEI_OUT (default ./hold_endpoints.tsv).
# One row per FF hold path end with negative slack: endpoint, startpoint, kinds, FF hold slack, worst TT setup slack of the
# endpoint pin.  Clock-source ports are not data ports.
# Units: a path end slack property is already in the user time unit (ps for ASAP7); no scale factor (HEAD-HW-ECO 11-16:
# the old x1e12 made -15.5 ps read -1.55e13 and the plan put 4 HB4 on every endpoint).
proc ot_hei_dump {} {
  set out [expr {[info exists ::env(OT_HEI_OUT)] ? $::env(OT_HEI_OUT) : "hold_endpoints.tsv"}]
  set ffm [expr {[info exists ::env(OT_HEI_FF_MODE)] ? $::env(OT_HEI_FF_MODE) : "ff"}]
  set ttm [expr {[info exists ::env(OT_HEI_TT_MODE)] ? $::env(OT_HEI_TT_MODE) : "tt"}]
  set entry [sta::cmd_mode_name]
  set_mode $ttm
  set tt [dict create]
  foreach pe [find_timing_paths -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    dict set tt [get_full_name [get_property $pe endpoint]] [get_property $pe slack]
  }
  set_mode $ffm
  set fh [open $out w]
  puts $fh "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps"
  foreach pe [find_timing_paths -path_delay min -slack_max 0 -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    set e [get_property $pe endpoint]; set s [get_property $pe startpoint]
    set en [get_full_name $e]
    set sl [get_property $pe slack]
    set ttv [expr {[dict exists $tt $en] ? [dict get $tt $en] : 1e6}]
    set sk [expr {[llength [get_ports -quiet [get_full_name $s]]] ? "port" : "reg"}]
    set ek [expr {[llength [get_ports -quiet $en]] ? "port" : "reg"}]
    puts $fh "$en\t[get_full_name $s]\t$sk\t$ek\t[format %.3f $sl]\t[format %.3f $ttv]"
  }
  close $fh
  set_mode $entry
}
ot_hei_dump
