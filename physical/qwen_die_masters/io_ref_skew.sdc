# Die-context boundary (post-CTS only; OpenROAD 26Q3 crashes on -reference_pin, so it is applied numerically):
# L = propagated clock arrival at a boundary register of this block (OT_REF_GLOB, default *go_q*), measured here.
#   input  max = 166.667 + L_max + skew      min = L_min - hold_skew
#   output max = 166.667 - L_max + skew      min = -L_min - hold_skew
# skew = OT_IO_SKEW (90, same clock region) or OT_IO_SKEW_INTER (150) on the OT_IO_INTER port globs; hold_skew =
# OT_IO_HOLD_SKEW (50).  Margin rule 2026-10-06 (+ clarification: 150 ps only across clock regions).
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
set ot_glob [expr {[info exists ::env(OT_REF_GLOB)] ? $::env(OT_REF_GLOB) : "*go_q*"}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qdm_ref {}
foreach c [get_cells -quiet -hierarchical $ot_glob] {
  set p [get_pins -quiet "[get_full_name $c]/CLK"]
  if {[llength $p]} { set qdm_ref $p; break }
}
if {[llength $qdm_ref] == 0} { set qdm_ref [lindex [all_registers -clock_pins] 0] }
set qdm_w [sta::worst_slack_cmd max]
set qdm_lmax [get_property $qdm_ref arrival_max_rise]
set qdm_lmin [get_property $qdm_ref arrival_min_rise]
puts "QDM reference pin [get_full_name $qdm_ref] clock arrival max $qdm_lmax min $qdm_lmin skew $ot_sk hold $ot_hk"
set_input_delay [expr 166.667 + $qdm_lmax + $ot_sk] -max -clock core_clk [all_inputs -no_clocks]
# RULE H1 (flow-hold 2026-10-07): a die link's hold budget (die clock-arrival term OT_IO_HOLD_SKEW + hold uncertainty) is
# carried ONCE, by the SENDER's output min delay below.  The receiver's input check keeps only its own tree offset from the
# reference register (+ hold time + uncertainty): input min = L_min - OT_IO_IN_HOLD_SKEW (default 0).  Counting the 50 ps on
# both sides demanded ~150 ps of hold delay per link for a 50 ps skew (the FF -30..-45 ps input band of every master).
set ot_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
set_input_delay [expr $qdm_lmin - $ot_hki] -min -clock core_clk [all_inputs -no_clocks]
set_output_delay [expr 166.667 - $qdm_lmax + $ot_sk] -max -clock core_clk [all_outputs]
set_output_delay [expr 0 - $qdm_lmin - $ot_hk] -min -clock core_clk [all_outputs]
if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
  set ot_ski [expr {[info exists ::env(OT_IO_SKEW_INTER)] ? $::env(OT_IO_SKEW_INTER) : 150}]
  set ot_ii {}; set ot_io {}
  foreach g [split $::env(OT_IO_INTER) ","] {
    foreach p [get_ports -quiet $g] { if {[get_property $p direction] eq "input"} { lappend ot_ii $p } else { lappend ot_io $p } }
  }
  if {[llength $ot_ii]} { set_input_delay [expr 166.667 + $qdm_lmax + $ot_ski] -max -clock core_clk $ot_ii }
  if {[llength $ot_io]} { set_output_delay [expr 166.667 - $qdm_lmax + $ot_ski] -max -clock core_clk $ot_io }
  puts "OT_IO_INTER [llength $ot_ii] inputs [llength $ot_io] outputs at $ot_ski ps"
}
if {[llength [get_ports -quiet tile_id*]]} { set_false_path -from [get_ports tile_id*] }
# STRUCT-CLOSE 2026-10-09 (drive-0212 0512, rule H1): OT_REF_GROUPS = "<port glob>=<cell glob>;..." re-references the
# matching ports to the measured clock arrival of THEIR OWN boundary registers (mean over the cells matching the cell
# glob, CLK pins) instead of the one OT_REF_GLOB register: a block whose input stations sit on different tree branches
# (qfd_crom48cl: crom_re -> u_is_re at 837 ps, crom_addr -> u_is_a ~250 ps later) otherwise demands ~250 ps of hold
# delay on the late group (crom48cl_a2: 4_1_cts input-port hold -152, repair stalled).  Same formulas and skews as above
# (INTER ports keep OT_IO_SKEW_INTER on max).  Unset = unchanged.
if {[info exists ::env(OT_REF_GROUPS)] && $::env(OT_REF_GROUPS) ne ""} {
  foreach ot_rg [split $::env(OT_REF_GROUPS) ";"] {
    if {[string trim $ot_rg] eq ""} continue
    lassign [split $ot_rg "="] ot_rg_p ot_rg_c
    # H1 "mean insertion": the mean arrival over every matching register (max and min separately)
    set ot_rg_ref {}; set ot_rg_smax 0.0; set ot_rg_smin 0.0; set ot_rg_k 0
    foreach c [get_cells -quiet -hierarchical $ot_rg_c] {
      set p [get_pins -quiet "[get_full_name $c]/CLK"]
      if {![llength $p]} continue
      set a [get_property $p arrival_max_rise]; set b [get_property $p arrival_min_rise]
      if {$a eq "" || $b eq "" || $a eq "INF" || $b eq "-INF" || $b eq "INF"} continue
      if {![llength $ot_rg_ref]} { set ot_rg_ref $p }
      set ot_rg_smax [expr {$ot_rg_smax + $a}]; set ot_rg_smin [expr {$ot_rg_smin + $b}]; incr ot_rg_k
    }
    if {!$ot_rg_k} { puts "OT_REF_GROUPS $ot_rg_p: no register matches $ot_rg_c (kept the OT_REF_GLOB reference)"; continue }
    set ot_rg_lmax [expr {$ot_rg_smax / $ot_rg_k}]
    set ot_rg_lmin [expr {$ot_rg_smin / $ot_rg_k}]
    set ot_rg_n 0
    foreach p [get_ports -quiet $ot_rg_p] {
      set ot_rg_sk $ot_sk
      if {[info exists ::env(OT_IO_INTER)]} {
        foreach g [split $::env(OT_IO_INTER) ","] { if {$g ne "" && [string match $g [get_full_name $p]]} { set ot_rg_sk $ot_ski } }
      }
      if {[get_property $p direction] eq "input"} {
        set_input_delay [expr 166.667 + $ot_rg_lmax + $ot_rg_sk] -max -clock core_clk $p
        set_input_delay [expr $ot_rg_lmin - $ot_hki] -min -clock core_clk $p
      } else {
        set_output_delay [expr 166.667 - $ot_rg_lmax + $ot_rg_sk] -max -clock core_clk $p
        set_output_delay [expr 0 - $ot_rg_lmin - $ot_hk] -min -clock core_clk $p
      }
      incr ot_rg_n
    }
    puts [format "OT_REF_GROUPS %s -> mean of %d registers (%s ...) arrival max %.1f min %.1f (%d ports)" $ot_rg_p $ot_rg_k [get_full_name $ot_rg_ref] $ot_rg_lmax $ot_rg_lmin $ot_rg_n]
  }
}
