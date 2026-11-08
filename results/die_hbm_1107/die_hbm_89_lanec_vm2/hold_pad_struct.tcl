# DIE-HBM-89 lanec_vM2 (PRE_GLOBAL_PLACE hook): STRUCTURAL HOLD PAD for short register-to-register paths.
# Measured on lanec_vM1 routed FF sign-off (ed-hbm tools): 78 non-port hold endpoints, all 1-3 cell reg->reg paths
# (delay-line shift registers u_k*.g_r.r, face input -> u_ctl (e_ho->wq_d -15.69, e_qq->yb -9.90), u_ctl.pre_q -> u_bout_e_b,
# u_v*.line rings), passing at the GRT estimate (+0.02) and missing after detail route by GRT->route clock drift.
# Form: before global placement, every flop D pin whose worst min path is launched by a register and has an ideal-clock
# hold slack below OT_HPAD_HOLD_PS (default 52 = every vM1 routed non-port violator, TT ideal 17.4-50.2) gets ONE fixed dont-touch HB4xp67 in front of D (FF ~37 ps), placed by GPL next to
# the flop.  Only where the D pin's ideal setup slack is >= OT_HPAD_SETUP_PS (the pad is on every path into D).
# Function-neutral (buffer); repair_timing/repair_design cannot remove or resize it (dbInst doNotTouch).
if {![info exists ::env(OT_HPAD_PROBE)]} { uplevel #0 [list source /work/face_flops.tcl] }
if {![info exists ::env(OT_HPAD_PROBE)]} {
  source /work/hpad_list_insert.tcl
  uplevel #0 [list ot_hpad_insert_list /work/hpad_list.txt]
  return
}
uplevel #0 {
  set hp_th  [expr {[info exists ::env(OT_HPAD_HOLD_PS)]  ? $::env(OT_HPAD_HOLD_PS)  : 52}]
  set hp_su  [expr {[info exists ::env(OT_HPAD_SETUP_PS)] ? $::env(OT_HPAD_SETUP_PS) : 250}]
  set hp_dry [expr {[info exists ::env(OT_HPAD_DRY)] && $::env(OT_HPAD_DRY) eq "1"}]
  set hp_blk [ord::get_db_block]
  set hp_m [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
  if {$hp_m eq "NULL" || $hp_m eq ""} { error "OT_HPAD no HB4xp67_ASAP7_75t_R master" }
  set hp_cand [dict create]
  foreach pe [find_timing_paths -path_delay min -from [all_registers -clock_pins] -group_path_count 1000000 -endpoint_path_count 1 -slack_max $hp_th] {
    set ep [get_property $pe endpoint]
    set it [sta::sta_to_db_pin $ep]
    if {$it eq "" || $it eq "NULL" || [[$it getMTerm] getName] ne "D"} continue
    if {![string match "*DFF*" [[[$it getInst] getMaster] getName]]} continue
    set epn [get_full_name $ep]
    dict set hp_cand $epn [list [get_property $pe slack] [llength [get_property $pe points]] $it]
  }
  set hp_pins [dict keys $hp_cand]
  set hp_su_of [dict create]
  if {[llength $hp_pins]} {
    foreach pe [find_timing_paths -path_delay max -to [get_pins $hp_pins] -group_path_count 1000000 -endpoint_path_count 1 -slack_max 1e9] {
      dict set hp_su_of [get_full_name [get_property $pe endpoint]] [get_property $pe slack]
    }
  }
  set hp_n 0; set hp_skip 0; set hp_hist [dict create]; set hp_out {}
  foreach epn $hp_pins {
    set su [expr {[dict exists $hp_su_of $epn] ? [dict get $hp_su_of $epn] : 1e9}]
    if {$su < $hp_su} { incr hp_skip; puts "OT_HPAD_SKIP $epn hold [format %.1f [lindex [dict get $hp_cand $epn] 0]] setup [format %.1f $su]"; continue }
    set it [lindex [dict get $hp_cand $epn] 2]
    set k [expr {int([lindex [dict get $hp_cand $epn] 0] / 10) * 10}]; dict incr hp_hist $k
    if {$hp_dry} { incr hp_n; lappend hp_out [[$it getInst] getName]; continue }
    set net [$it getNet]
    set b [odb::dbInst_create $hp_blk $hp_m "ot_hpad_$hp_n"]
    set nn [odb::dbNet_create $hp_blk "ot_hpad_n_$hp_n"]
    $it disconnect; $it connect $nn
    [$b findITerm A] connect $net; [$b findITerm Y] connect $nn
    $b setDoNotTouch 1
    incr hp_n
  }
  if {$hp_dry && [info exists ::env(OT_HPAD_WRITE)]} { set f [open $::env(OT_HPAD_WRITE) w]; puts $f [join $hp_out "\n"]; close $f }
  puts "OT_HPAD candidates [llength $hp_pins] padded $hp_n skipped_setup $hp_skip hold_ps<$hp_th setup_ps>=$hp_su dry $hp_dry hist [lsort -integer -stride 2 $hp_hist]"
}
