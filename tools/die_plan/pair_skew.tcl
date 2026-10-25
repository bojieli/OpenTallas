# pair_skew.tcl -- related launch/capture flop-pair clock skew WITH CPPR credit (owner gate, BRIEFING decision 5).
#
# Sourced inside an OpenSTA / OpenROAD session in which the design, libraries, parasitics and SDC are already loaded
# (signoff.py session, or standalone with OT_PS_OUT set).  Gate: worst related-pair skew <= 80 ps at TT and FF; the
# max-min pin-flop spread is INFORMATION only.
#
# Definitions (ps, same as die_sta.py: capture CK arrival - launch CK arrival, CPPR credited):
#   setup check (max):  s = Cmin + crpr_s - Lmax      (negative = early capture, hurts setup; damage = -s)
#   hold  check (min):  h = Cmax - crpr_h - Lmin      (positive = late capture,  hurts hold;  damage = +h)
# A pair's skew in either direction shows up as damage on one of the two checks, so the gate is
#   max over related pairs of max(-s, h) <= 80.
#
# Related pairs are EXHAUSTIVE (not the worst-slack path per endpoint): for every register data pin (async pins
# excluded) every register in its timing fan-in (get_fanin -startpoints_only, same clock) is a launch register.
# Pass 1 (all pairs, no path search): raw damage from the CK pin rise arrivals without CPPR credit -- an upper bound,
# since CPPR >= 0 only reduces damage.  Pass 2 (per check, descending raw damage): the pair's own timing path
# (find_timing_paths -from launch -to capture data pin) gives the exact credited skew; the search stops as soon as the
# next pair's raw bound is <= the credited worst (the worst is then EXACT), or after OT_PS_CREDIT_MAX searches (the
# worst is then a BOUND: max(credited worst, next raw), flagged bounded=1).
#
# Exact values from a path end (OpenSTA PathEnd::clk_skew = Lsrc - Ctgt - crpr, crpr >= 0 for BOTH checks; verified
# against report_checks on kr_dsdv_svc_sx_hrow_c 2026-10-24 and CP1 r9; uncertainty zeroed first):
#   setup: s = -clk_skew                 crpr_s = data_required - tgt_arrival + margin   (mod period, edge removed)
#   hold : h = -clk_skew - 2 crpr_h      crpr_h = tgt_arrival + margin - data_required   (mod period, edge removed)
# Each credited pair is cross-checked against the CK pin arrivals (Cmin + crpr - Lmax etc.); max |difference| is
# reported as verify_ps (a large value means an edge/arrival mismatch -- treat the measurement as suspect).
#
# OpenSTA pitfall (sta_die.tcl): an arrival query while PathEnd objects are live re-runs the search and frees them.
# All CK arrivals are read BEFORE any path search; path-end values are copied into Tcl values at once.
#
# This script must NOT change the session's SDC beyond the clock uncertainty (ot_ps_zero_unc), which the caller
# runs last-in-session or restores.  It never re-reads an SDC and never touches clock source latency.
#
# env (standalone): OT_PS_OUT (TSV path), CORNER (label), OT_PS_CREDIT_MAX (default 5000).
# TSV: H <key> <value> ; P <max|min> <launch> <capture> <skew_ps> <crpr_ps> <raw_damage_ps>

proc ot_ps_ps {s} { return [expr {$s * 1e12}] }

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

proc ot_ps_ckarr {pin clk which} {
  # propagated CLOCK arrival (ps, latency from the launching clock edge) of a register clock pin, min or max, from the
  # pin's "(clock prop)" path tags of that clock only.  get_property arrival_*_rise is NOT used by default: it is the
  # max/min over every tag on the pin, so a data arrival riding the clock net (10-24 routed smoke, qkd_ctrl_kc: an
  # input delay on the hclk port gave CK arrival_max_rise 391 ps vs a 48 ps clock arrival) corrupts it.  NO T/2 fold.
  # -> value, or "" if the pin has no unique clock arrival; falls back to arrival_*_rise when the tag API is missing
  # (::ot_ps_method records which; the per-pair path cross-check then guards the fallback).
  set cn [get_full_name $clk]
  if {$::ot_ps_method eq "tag"} {
    set vals {}
    if {![catch {
      set wf {}
      foreach t [$clk waveform] { lappend wf [expr {$t * 1e12}] }
      foreach v [$pin vertices] {
        if {$v eq "NULL"} continue
        set it [$v path_iterator rise $which]
        while {[$it has_next]} {
          set pa [$it next]; set tag [$pa tag]; set e [lindex $tag 4]
          if {[lindex $tag 3] ne $cn || $e ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
          set x [expr {[$pa arrival] * 1e12 - [lindex $wf [expr {$e eq "^" ? 0 : 1}]]}]
          if {[lsearch -real $vals $x] < 0} { lappend vals $x }
        }
        $it finish
      }
    } err]} {
      if {[llength $vals] == 1} { return [lindex $vals 0] }
      return ""
    }
    set ::ot_ps_method "property"
    puts "OT_PS_WARN clock-tag arrival API unavailable ($err); falling back to arrival_${which}_rise"
  }
  if {[catch {set a [get_property $pin arrival_${which}_rise]}] || $a eq "" || [string match *INF* $a]} { return "" }
  return $a
}

proc ot_ps_regs {} {
  # inst -> {ckpin clock late early} for every register clock pin with exactly one clock and a unique clock arrival
  set R {}; set ::ot_ps_noarr 0
  foreach p [all_registers -clock_pins] {
    set cl [get_property $p clocks]
    if {[llength $cl] != 1} continue
    set a [ot_ps_ckarr $p [lindex $cl 0] max]; set b [ot_ps_ckarr $p [lindex $cl 0] min]
    if {$a eq "" || $b eq ""} { incr ::ot_ps_noarr; continue }
    dict set R [ot_ps_inst [get_full_name $p]] [list [get_full_name $p] [get_full_name [lindex $cl 0]] $a $b]
  }
  return $R
}

proc ot_ps_related {R} {
  # exhaustive related pairs: {launch capture capture_data_pin raw_setup_damage raw_hold_damage}, unique per pair
  # (worst raw over the capture register's data pins) + counters {pairs inter_clock data_pins}
  set async {}
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  set P {}; set nx 0; set nd 0
  foreach d [all_registers -data_pins] {
    set dn [get_full_name $d]
    if {[dict exists $async $dn]} continue
    set c [ot_ps_inst $dn]
    if {![dict exists $R $c]} continue
    incr nd
    lassign [dict get $R $c] cck cclk clate cearly
    foreach s [get_fanin -to $d -startpoints_only -flat] {
      set l [ot_ps_inst [get_full_name $s]]
      if {![dict exists $R $l]} continue
      lassign [dict get $R $l] lck lclk llate learly
      if {$lclk ne $cclk} { incr nx; continue }
      set ds [expr {$llate - $cearly}]
      set dh [expr {$clate - $learly}]
      set k "$l\t$c"
      if {[dict exists $P $k]} {
        lassign [dict get $P $k] - - - os oh
        if {$ds <= $os && $dh <= $oh} continue
        set ds [expr {max($ds, $os)}]; set dh [expr {max($dh, $oh)}]
      }
      dict set P $k [list $l $c $dn $ds $dh]
    }
  }
  return [list $P [dict size $P] $nx $nd]
}

proc ot_ps_path {l dn dly} {
  # exact credited skew of one pair and check: {skew_ps crpr_ps} or {} when no constrained reg->reg path exists
  set lck [get_pins -quiet "[lindex [dict get $::ot_ps_R $l] 0]"]
  if {![llength $lck] || [catch {set pes [find_timing_paths -from $lck -to [get_pins $dn] -path_delay $dly \
                                              -group_path_count 1 -endpoint_path_count 1]}] || ![llength $pes]} { return {} }
  set pe [lindex $pes 0]
  if {![$pe is_check] || [$pe is_latch_check]} { return {} }
  set role [$pe check_role]
  set tp [$pe target_clk_path]
  if {$tp eq "NULL" || $tp eq ""} { return {} }
  set per [expr {[get_property [$pe target_clk] period] * 1e-12}]
  set sk [$pe clk_skew]; set req [$pe data_required_time]; set tarr [$tp arrival]; set mg [$pe margin]
  set et [[$pe target_clk_edge] time]
  unset pes pe tp
  if {$role eq "setup"} {
    set x [expr {$req - $tarr + $mg - $et}]
    set crpr [expr {$x - $per * round($x / $per)}]
    set sk [expr {-$sk}]
  } elseif {$role eq "hold"} {
    set x [expr {$req - $tarr - $mg - $et}]
    set crpr [expr {-($x - $per * round($x / $per))}]
    set sk [expr {-$sk - 2.0 * $crpr}]
  } else { return {} }
  return [list [ot_ps_ps $sk] [ot_ps_ps $crpr]]
}

proc ot_ps_p99 {v} {
  set n [llength $v]; if {!$n} { return NA }
  set s [lsort -real $v]
  return [format %.2f [lindex $s [expr {max(0, int(ceil(0.99 * $n)) - 1)}]]]
}

proc ot_ps_measure {{credit_max 5000}} {
  # -> dict: pairs inter_clock data_pins ; per check (max|min): n worst bounded signed launch capture crpr p99_raw
  #    searched nopath verify rows ({launch capture skew crpr raw})
  set ::ot_ps_method tag
  # complete timing update BEFORE any arrival / path-tag query (sta_die.tcl: arrival-first segfaults be771a0)
  sta::worst_slack_cmd max; sta::worst_slack_cmd min
  set ::ot_ps_R [ot_ps_regs]
  lassign [ot_ps_related $::ot_ps_R] P np nx nd
  set out [dict create pairs $np inter_clock $nx data_pins $nd regs [dict size $::ot_ps_R] no_clock_arrival \
             $::ot_ps_noarr method $::ot_ps_method]
  foreach dly {max min} {
    set idx [expr {$dly eq "max" ? 3 : 4}]
    set raw {}
    dict for {k v} $P { lappend raw [list [lindex $v $idx] [lindex $v 0] [lindex $v 1] [lindex $v 2]] }
    set raw [lsort -real -decreasing -index 0 $raw]
    set worst ""; set wrow {}; set rows {}; set ns 0; set nnp 0; set vfy 0.0; set bounded 0; set next ""
    foreach r $raw {
      lassign $r rd l c dn
      if {$worst ne "" && $rd <= $worst} { set next ""; break }
      if {$ns >= $credit_max} { set bounded 1; set next $rd; break }
      incr ns
      set e [ot_ps_path $l $dn $dly]
      if {![llength $e]} { incr nnp; continue }
      lassign $e sk cr
      set dmg [expr {$dly eq "max" ? -$sk : $sk}]
      # cross-check vs the CK pin arrivals: damage = raw - crpr
      set d [expr {abs(($rd - $cr) - $dmg)}]
      if {$d > $vfy} { set vfy $d }
      lappend rows [list $l $c [format %.2f $sk] [format %.2f $cr] [format %.2f $rd]]
      if {$worst eq "" || $dmg > $worst} { set worst $dmg; set wrow [list $l $c $sk $cr] }
    }
    if {$bounded && $worst ne "" && $next > $worst} { set worst $next }
    set p99 [ot_ps_p99 [lmap r $raw {lindex $r 0}]]
    lassign $wrow wl wc wsk wcr
    dict set out $dly [dict create n [llength $raw] worst [expr {$worst eq "" ? "NA" : [format %.2f $worst]}] \
      bounded $bounded signed [expr {$wsk eq "" ? "NA" : [format %.2f $wsk]}] launch $wl capture $wc \
      crpr [expr {$wcr eq "" ? "NA" : [format %.2f $wcr]}] p99_raw $p99 searched $ns nopath $nnp \
      verify [format %.3f $vfy] rows $rows]
  }
  return $out
}

proc ot_ps_write {M fn corner} {
  set fh [open $fn w]
  puts $fh "H\tcorner\t$corner"
  foreach k {regs no_clock_arrival method data_pins pairs inter_clock} { puts $fh "H\t$k\t[dict get $M $k]" }
  puts $fh "H\tcrpr\t[sta::crpr_enabled] [sta::crpr_mode]"
  foreach dly {max min} {
    set m [dict get $M $dly]
    foreach k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} {
      puts $fh "H\t${dly}_$k\t[dict get $m $k]"
    }
    foreach r [dict get $m rows] { puts $fh "P\t$dly\t[join $r \t]" }
  }
  close $fh
}

proc ot_ps_main {} {
  set corner [expr {[info exists ::env(CORNER)] ? $::env(CORNER) : "NA"}]
  set cm [expr {[info exists ::env(OT_PS_CREDIT_MAX)] ? $::env(OT_PS_CREDIT_MAX) : 5000}]
  set t0 [clock seconds]
  set_propagated_clock [all_clocks]
  ot_ps_zero_unc
  set M [ot_ps_measure $cm]
  ot_ps_write $M $::env(OT_PS_OUT) $corner
  foreach dly {max min} {
    set m [dict get $M $dly]
    puts "OT_PS $corner $dly n [dict get $m n] worst [dict get $m worst] bounded [dict get $m bounded] signed [dict get $m signed] [dict get $m launch] -> [dict get $m capture] crpr [dict get $m crpr] p99_raw [dict get $m p99_raw] verify [dict get $m verify]"
  }
  puts "OT_PS_DONE $corner [expr {[clock seconds] - $t0}] s"
}

if {![info exists ::ot_ps_lib_only] && [info exists ::env(OT_PS_OUT)]} { ot_ps_main }
