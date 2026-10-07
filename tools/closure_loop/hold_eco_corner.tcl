# closure-loop HOLD-ECO helper: one corner's EFFECTIVE sign-off constraints, built exactly as tools/w18/corner_sta.py
# builds them (that corner's libraries only; read_db, read_sdc, read_spef, set_propagated_clock, then the post-SDCs),
# written out with write_sdc so the multi-corner ECO session sees each corner's own constraints.  Post-SDCs such as
# hbm_accel_die_views/common/vclk_corner_true.sdc are corner-conditional ([get_libs *_FF_*]) and read live latency
# reports: read once into a two-corner session they applied the FF IO model to SS setup too (idxq_b1: ECO saw SS
# vclk setup -414.69 where sign-off read +107.23, so the setup guard was void and 14,557 buffers went in).
# hold_eco_sdc.py merges the two files (SS max side, FF min side) for the ECO session.
# env: OT_CORNER (ss|ff), OT_DB, OT_SDC, OT_SPEF, OT_POST_SDC, OT_MACROS, OT_EFF (output sdc)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc envd {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
set c $::env(OT_CORNER); set C [string toupper $c]
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach m [envd OT_MACROS ""] { read_lef $m/[file tail $m].lef }
foreach l [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz \
             asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib \
             asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty $P/lib/NLDM/$l }
foreach m [envd OT_MACROS ""] { read_liberty $m/[file tail $m]_$c.lib }
read_db $::env(OT_DB)
read_sdc $::env(OT_SDC)
if {[file exists [envd OT_SPEF ""]]} { read_spef $::env(OT_SPEF) }
set_propagated_clock [all_clocks]
foreach s [envd OT_POST_SDC ""] { read_sdc $s }
puts "OT_CORNER_EFF $c ws_max [sta::worst_slack_cmd max] ws_min [sta::worst_slack_cmd min]"
write_sdc -no_timestamp $::env(OT_EFF)
# SS session: data the FF-only ECO session needs to protect setup (hold_eco.tcl OT_SESSION=ff)
#   <eff>.slack : SS setup slack per register D pin and output port ("name slack")
#   <eff>.crit  : nets on SS setup paths under OT_CRIT_PS (dont_touch in the FF-only ECO)
if {$c eq "ss"} {
  set f [open $::env(OT_EFF).slack w]
  # every timing-check data pin: flop D pins AND macro data pins (hfd_cmdproc_n: u_cmem/b_addr_in had no SS slack
  # with */D only, so its hold endpoints were classed infeasible on missing data)
  set ot_dp [concat [get_pins -hierarchical */D] [all_registers -data_pins] [all_outputs]]
  set ot_seen [dict create]
  foreach p $ot_dp {
    set pn [get_full_name $p]; if {[dict exists $ot_seen $pn]} continue; dict set ot_seen $pn 1
    if {[catch {set s [get_property $p slack_max]}]} continue
    if {$s ne "INF" && $s ne ""} { puts $f [list [get_full_name $p] $s] }
  }
  close $f
  set crit [dict create]
  # the PathEnds are read in full before any other query (a later timing query frees them)
  set paths [find_timing_paths -path_delay max -slack_max [envd OT_CRIT_PS 60] -group_path_count 100000 -endpoint_path_count 1]
  foreach pe $paths {
    if {[catch {set pts [get_property $pe points]}]} continue
    foreach pt $pts {
      if {[catch {set pin [get_property $pt pin]}] || $pin eq "NULL" || $pin eq ""} continue
      if {[catch {set net [get_nets -quiet -of_objects $pin]}] || ![llength $net]} continue
      foreach n1 $net { if {![catch {set nn [get_full_name $n1]}]} { dict set crit $nn 1 } }
    }
  }
  set f [open $::env(OT_EFF).crit w]; foreach n [dict keys $crit] { puts $f $n }; close $f
  puts "OT_CORNER_EFF ss_protect [llength $paths] paths under [envd OT_CRIT_PS 60] ps, [dict size $crit] nets"
}
puts "OT_CORNER_EFF done"
