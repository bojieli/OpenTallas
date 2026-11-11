# GENERATED-COPY of tools/die_plan/reset_follow_clock.tcl (VSN2-HOLD 11-11, DIE-HBM-97; opt-in plan
# reset.follow_clock_tap {"types": [...]}, gen_phys.reset_follow_clock_tap).  Sourced by pre_cts.tcl right after the
# post-place reset_taps.tcl leaf check, i.e. after clock_taps.tcl has fixed every clock pin (nearest / cap /
# follower / hop-latch passes), in the same scope (it reads reset_taps.tcl's rt_* tables and procs).
# Why: reset_taps.tcl points each placed control sink (station eq / epoch flops) at its NEAREST tap's reset terminal;
# the CTS clock assignment can hang that flop on another tap port (vsN2 a11: leaf relay u_rrl_9 = rst_n_t7 launches on
# clk_t7, its sink u_ft_L201x2_o_2/eq is clocked by clk_t2: FF removal -19.1 ps).  A cross-port pair is timed with the
# whole plan tap window W (launch early -W, capture late 0, no CRPR across ports), so the removal check needs W of
# path delay.  Here every such sink is re-pointed to the same-polarity net of a terminal whose LAUNCH flop sits on the
# sink's own clock net (same tap port: CRPR credits W; recovery and removal keep the full cycle), when such a terminal
# lies within the leaf reach rt_leaf_reach_um; otherwise the sink is kept and named (timed at sign-off as before).
# The terminals are the equal-depth leaf relays of one partition reset tree (reset_tree.py), so this is the transform
# reset_taps.tcl (2) already makes (same release cycle); clock nets, data nets and cells are unchanged.
proc rfc_clock_net {ins} {
  foreach it [$ins getITerms] {
    if {[[$it getMTerm] getName] in {CLK CLKN} && [$it getNet] ne "NULL"} { return [[$it getNet] getName] }
  }
  return ""
}
if {![info exists rt_cls] || ![info exists rt_rep] || ![info exists rt_role_tables] || [llength $rt_role_tables] != 1} {
  puts "OT_RESET_FOLLOW_CLOCK skipped: needs exactly one reset role from reset_taps.tcl"
} else {
  # launch clock net + launch location of every reset terminal (the relay flop that drives rst_n_t<i>)
  set rfc_lck {}; set rfc_lxy {}
  foreach tp $rt_taps {
    set i [lindex $tp 0]
    set n [rt_tapnet $rt_blk $i]
    if {$n eq "NULL" || $n eq ""} continue
    set src [rt_launch_source $n {}]
    if {[llength $src] != 3} continue
    lassign $src ln lpar lxy
    set li ""
    foreach it [$ln getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set li [$it getInst] } }
    if {$li eq ""} continue
    set cn [rfc_clock_net $li]
    if {$cn eq ""} continue
    dict set rfc_lck $i $cn
    dict set rfc_lxy $i $lxy
  }
  set rfc_moved 0; set rfc_keep 0; set rfc_none {}
  foreach ins [$rt_blk getInsts] {
    if {![string match "*DFF*" [[$ins getMaster] getName]]} continue
    if {[$ins getPlacementStatus] ni {FIRM PLACED LOCKED}} continue
    if {[regexp {(^|[/.])u_rsync_t[0-9]+[/.]} [$ins getName]]} continue
    if {[regexp {(^|[/.])(u_rst_root|u_rst_in|u_run_root|u_run_in|u_[rs]rl_[0-9]+(_[rgb])?)[/.]} [$ins getName]]} continue
    set cn [rfc_clock_net $ins]
    if {$cn eq ""} continue
    lassign [$ins getLocation] x y
    foreach it [$ins getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set net [$it getNet]
      if {$net eq "NULL" || ![dict exists $rt_cls [$net getName]]} continue
      lassign [dict get $rt_cls [$net getName]] k par
      if {[dict exists $rfc_lck $k] && [dict get $rfc_lck $k] eq $cn} { incr rfc_keep; continue }
      set best ""; set bd 0
      dict for {i lc} $rfc_lck {
        if {$lc ne $cn || ![dict exists $rt_rep "$i,$par"]} continue
        lassign [dict get $rfc_lxy $i] lx ly
        set d [expr {abs($x - $lx) + abs($y - $ly)}]
        if {[info exists rt_leaf_reach_um] && $d > $rt_leaf_reach_um * $rt_dbu} continue
        if {$best eq "" || $d < $bd} { set best $i; set bd $d }
      }
      if {$best eq ""} { lappend rfc_none "[$ins getName]/[[$it getMTerm] getName]:$cn"; continue }
      $it disconnect
      $it connect [dict get $rt_rep "$best,$par"]
      incr rfc_moved
    }
  }
  puts "OT_RESET_FOLLOW_CLOCK [dict size $rfc_lck] reset terminals with a launch clock; control sink pins: $rfc_moved re-pointed to a same-clock terminal, $rfc_keep already same-clock, [llength $rfc_none] kept (no same-clock terminal of that polarity within reach): [lrange $rfc_none 0 19]"
}
