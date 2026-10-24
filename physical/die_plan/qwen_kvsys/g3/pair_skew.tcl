# pair_skew.tcl -- related launch/capture flop-pair clock skew WITH CPPR credit (owner gate 2026-10-23).
#
# Sourced inside an OpenSTA (`sta`) or OpenROAD session in which the design, libraries, parasitics and SDC are already
# loaded.  Gate (tools/die_plan/pair_skew.py gate): worst |pair skew| <= 80 ps at TT and FF, intra-partition pairs and
# seam pairs.  The max-min spread over all (face) flops is REPORTED only.
#
# Definition (ps):  pair skew = effective capture clock arrival - launch clock arrival, CPPR credited:
#   setup (max):  Ccap_min + crpr - Llaunch_max
#   hold  (min):  Ccap_max - crpr - Llaunch_min
# Positive = the capture clock is late (helps setup, hurts hold).
#
# OpenSTA PathEnd::clk_skew (verified on CP1 r9, uncertainty zeroed) = src - tgt - crpr with crpr >= 0 for BOTH checks:
#   setup: clk_skew = Lmax - Cmin - crpr  -> pair = -clk_skew
#   hold : clk_skew = Lmin - Cmax - crpr  -> pair = -clk_skew - 2 crpr   (OpenSTA subtracts the hold credit with the
#          setup sign: e.g. rsync p0->p1 TT: Lmin 191.26, Cmax 199.58, crpr 4.96 -> clk_skew -13.27, pair +3.36)
# so crpr is recovered per path end from the check itself:
#   setup: crpr = data_required - target_clk_path.arrival + margin - capture edge
#   hold : crpr = target_clk_path.arrival + margin - data_required + capture edge
# (margin = library setup / hold time, sign as in the library; the capture edge = target_clk_edge time + whole target
# periods, removed by rounding since crpr << period; clock uncertainty is zeroed first so it enters neither term).
# PathEnd / Path methods return SECONDS; get_property values are in the library unit (ps on ASAP7).
#
# IMPORTANT (OpenSTA pitfall, sta_die.tcl): an arrival query while PathEnd objects are live re-runs the search and frees
# them (segfault).  Every needed value is copied into plain Tcl lists first; CK arrivals are queried afterwards.
#
# env: OT_PS_OUT (TSV path; unset -> procs only), CORNER (label), OT_PS_MAX_PATHS (default 200000),
#      OT_PS_FACE ("[prefix=]file ..." face-flop lists, first tab field = instance name, prefix = hierarchy instance
#      for a die run), OT_PS_VERIFY (N: re-derive the first N pairs per check from CK pin arrivals by name; report max
#      |difference| as an "H verify_*" line), OT_PS_SCOPE (kit: one partition, every pair intra; default die).
# TSV (tab separated):  H <key> <value> ... ;  P <max|min> <launch inst> <capture inst> <skew_ps> <slack_ps> <crpr_ps>
#      (slack with clock uncertainty zeroed) ;  C <inst> <ck_rise_ps> <face 0|1>

proc ot_ps_ps {s} { return [expr {$s * 1e12}] }

proc ot_ps_signoff {} {
  # signoff numbers with the session's own uncertainties (seconds -> ps)
  set r {}
  foreach {k cmd mm} {wns_ps worst_slack_cmd max tns_ps total_negative_slack_cmd max
                      whs_ps worst_slack_cmd min ths_ps total_negative_slack_cmd min} {
    if {[catch {set v [sta::$cmd $mm]}]} { set v NA } else { set v [format %.2f [ot_ps_ps $v]] }
    lappend r $k $v
  }
  return $r
}

proc ot_ps_zero_unc {} {
  set cl [all_clocks]
  if {![llength $cl]} return
  set_clock_uncertainty 0 -setup $cl
  set_clock_uncertainty 0 -hold $cl
  foreach a $cl { foreach b $cl {
    catch {set_clock_uncertainty -from $a -to $b -setup 0}
    catch {set_clock_uncertainty -from $a -to $b -hold 0}
  } }
}

proc ot_ps_inst {pinname} { return [regsub {/[^/]+$} $pinname {}] }

proc ot_ps_pairs {dly {maxp 200000}} {
  # reg->reg setup (max) / hold (min) path ends, worst per endpoint -> {launch capture skew_ps slack_ps crpr_ps}
  set pes [find_timing_paths -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay $dly \
             -group_path_count $maxp -endpoint_path_count 1 -unique_paths_to_endpoint]
  set raw {}; set per {}
  foreach pe $pes {
    if {![$pe is_check] || [$pe is_gated_clock] || [$pe is_latch_check]} continue
    set role [$pe check_role]
    if {$role ne "setup" && $role ne "hold"} continue
    set tp [$pe target_clk_path]
    if {$tp eq "NULL" || $tp eq ""} continue
    set ck [$pe target_clk]
    if {![dict exists $per $ck]} { dict set per $ck [expr {[get_property $ck period] * 1e-12}] }
    lappend raw [list [get_full_name [get_property $pe startpoint]] [get_full_name [get_property $pe endpoint]] \
                   $role [$pe clk_skew] [$pe data_required_time] [$tp arrival] [$pe margin] [$pe slack] \
                   [[$pe target_clk_edge] time] [dict get $per $ck]]
  }
  unset pes
  set rows {}
  foreach r $raw {
    lassign $r sp ep role sk req tarr mg sl et per
    # required = capture edge (waveform time et + whole periods) + tarr +/- crpr -/+ margin; remove the edge
    if {$role eq "setup"} {
      set x [expr {$req - $tarr + $mg - $et}]
      set crpr [expr {$x - $per * round($x / $per)}]
      set pair [expr {-$sk}]
    } else {
      set x [expr {$req - $tarr - $mg - $et}]
      set crpr [expr {-($x - $per * round($x / $per))}]
      set pair [expr {-$sk - 2.0 * $crpr}]
    }
    lappend rows [list [ot_ps_inst $sp] [ot_ps_inst $ep] [format %.2f [ot_ps_ps $pair]] [format %.2f [ot_ps_ps $sl]] \
                    [format %.2f [ot_ps_ps $crpr]]]
  }
  return $rows
}

proc ot_ps_rise {pin} {
  # rise-edge clock arrival (tap_balance.tcl tb_rise): arrival_max_rise can be the falling edge (+T/2)
  if {[catch {set a [get_property $pin arrival_max_rise]}] || $a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  set c [get_property $pin clocks]
  if {![llength $c]} { return "" }
  set half [expr {[get_property [lindex $c 0] period] / 2.0}]
  if {$a >= $half} { set a [expr {$a - $half}] }
  return $a
}

proc ot_ps_ck {} {
  # {inst ck_rise_ps} for every register clock pin
  set out {}
  foreach p [all_registers -clock_pins] {
    set a [ot_ps_rise $p]
    if {$a eq ""} continue
    lappend out [list [ot_ps_inst [get_full_name $p]] [format %.2f $a]]
  }
  return $out
}

proc ot_ps_ckpin {inst} {
  foreach c {CLK CK clk} { set q [get_pins -quiet "$inst/$c"]; if {[llength $q]} { return $q } }
  return ""
}

proc ot_ps_verify {rows dly n} {
  # re-derive pair skew from the CK pins' max/min rise arrivals by name, crpr taken from the row: max |difference| ps
  # (setup checks the clk_skew decomposition and crpr; hold checks the sign-corrected crpr credit)
  set worst 0.0; set k 0
  foreach r [lrange $rows 0 [expr {$n - 1}]] {
    lassign $r l c sk sl crpr
    set lp [ot_ps_ckpin $l]; set cp [ot_ps_ckpin $c]
    if {$lp eq "" || $cp eq ""} continue
    if {$dly eq "max"} {
      set la [get_property $lp arrival_max_rise]; set ca [get_property $cp arrival_min_rise]
      set ref [expr {$ca + $crpr - $la}]
    } else {
      set la [get_property $lp arrival_min_rise]; set ca [get_property $cp arrival_max_rise]
      set ref [expr {$ca - $crpr - $la}]
    }
    # arrival_*_rise can be the falling-edge arrival (+T/2: tb_rise); compare modulo T/2
    set half [expr {[get_property [lindex [get_property $cp clocks] 0] period] / 2.0}]
    set d [expr {$ref - $sk}]
    set d [expr {abs($d - $half * round($d / $half))}]
    if {$d > $worst} { set worst $d }
    incr k
  }
  return [list $k [format %.3f $worst]]
}

proc ot_ps_faces {spec} {
  set f {}
  foreach item $spec {
    set pre ""; set file $item
    if {[regexp {^([^=]+)=(.+)$} $item -> pre file]} { set pre "$pre/" }
    if {![file exists $file]} { puts "OT_PS_WARN face list $file missing"; continue }
    set fh [open $file r]
    while {[gets $fh line] >= 0} {
      set n [string map {\\ {}} [lindex [split $line \t] 0]]
      if {$n ne ""} { dict set f "$pre$n" 1 }
    }
    close $fh
  }
  return $f
}

proc ot_ps_summary {rows} {
  # {n worst_abs worst_signed p99_abs launch capture} over rows
  if {![llength $rows]} { return {0 NA NA NA {} {}} }
  set ab {}; set w -1; set ws 0; set wl ""; set wc ""
  foreach r $rows {
    set s [lindex $r 2]; set a [expr {abs($s)}]; lappend ab $a
    if {$a > $w} { set w $a; set ws $s; set wl [lindex $r 0]; set wc [lindex $r 1] }
  }
  set ab [lsort -real $ab]
  set i [expr {int(ceil(0.99 * [llength $ab])) - 1}]
  if {$i < 0} { set i 0 }
  return [list [llength $rows] [format %.2f $w] $ws [format %.2f [lindex $ab $i]] $wl $wc]
}

proc ot_ps_main {} {
  set out $::env(OT_PS_OUT)
  set corner [expr {[info exists ::env(CORNER)] ? $::env(CORNER) : "NA"}]
  set maxp [expr {[info exists ::env(OT_PS_MAX_PATHS)] ? $::env(OT_PS_MAX_PATHS) : 200000}]
  set t0 [clock seconds]
  set_propagated_clock [all_clocks]
  set so [ot_ps_signoff]
  puts "OT_PS_SIGNOFF $corner $so"
  ot_ps_zero_unc
  set P {}
  foreach dly {max min} { dict set P $dly [ot_ps_pairs $dly $maxp] }
  set V {}
  if {[info exists ::env(OT_PS_VERIFY)] && $::env(OT_PS_VERIFY) > 0} {
    foreach dly {max min} { dict set V $dly [ot_ps_verify [dict get $P $dly] $dly $::env(OT_PS_VERIFY)] }
  }
  set ck [ot_ps_ck]
  set face [expr {[info exists ::env(OT_PS_FACE)] ? [ot_ps_faces $::env(OT_PS_FACE)] : {}}]
  set fh [open $out w]
  puts $fh "H\tcorner\t$corner"
  puts $fh "H\tscope\t[expr {[info exists ::env(OT_PS_SCOPE)] ? $::env(OT_PS_SCOPE) : {die}}]"
  foreach {k v} $so { puts $fh "H\t$k\t$v" }
  puts $fh "H\tcrpr\t[sta::crpr_enabled] [sta::crpr_mode]"
  puts $fh "H\tmax_paths\t$maxp"
  puts $fh "H\tface_list\t[dict size $face]"
  dict for {dly v} $V { puts $fh "H\tverify_$dly\t$v" }
  foreach dly {max min} {
    foreach r [dict get $P $dly] { puts $fh "P\t$dly\t[join $r \t]" }
  }
  foreach r $ck {
    lassign $r i a
    puts $fh "C\t$i\t$a\t[expr {[dict exists $face $i] ? 1 : 0}]"
  }
  close $fh
  foreach dly {max min} {
    puts "OT_PS $corner $dly [ot_ps_summary [dict get $P $dly]]"
    if {[dict exists $V $dly]} { puts "OT_PS_VERIFY $corner $dly [dict get $V $dly]" }
  }
  puts "OT_PS_DONE $corner $out [expr {[clock seconds] - $t0}] s"
}

if {![info exists ::ot_ps_lib_only] && [info exists ::env(OT_PS_OUT)]} { ot_ps_main }
