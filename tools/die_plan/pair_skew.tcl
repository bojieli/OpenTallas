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
# Pass 1 (all pairs, no path search): raw damage from the CK pin ACTIVE-EDGE arrivals without CPPR credit -- an upper bound,
# since CPPR >= 0 only reduces damage.  Pass 2 (per check, descending raw damage): the pair's own timing path
# (find_timing_paths -from launch -to capture data pin) gives the exact credited skew; the search stops as soon as the
# next pair's raw bound is <= the credited worst (the worst is then EXACT), or after OT_PS_CREDIT_MAX searches (the
# worst is then a BOUND: max(credited worst, next raw), flagged bounded=1).
#
# Exact values from a path end (OpenSTA PathEnd::clk_skew = Lsrc - Ctgt - crpr, crpr >= 0 for BOTH checks; verified
# against report_checks on kr_dsdv_svc_sx_hrow_c 2026-10-24 and CP1 r9; uncertainty zeroed first):
#   setup: s = -clk_skew - launch_insertion      crpr_s = data_required - tgt_arrival + margin   (mod period)
#   hold : h = -clk_skew - launch_insertion - 2 crpr_h   crpr_h = tgt_arrival + margin - data_required   (mod period)
# data_required and the target clock path arrival BOTH carry the capture edge time, so the difference is CPPR plus a
# whole number of periods: no edge term is subtracted (subtracting target_clk_edge time was a no-op on the rising edge
# at 0 but put T/2 into the CPPR of a falling-edge capture -- H0 TT P->N hold read crpr -414.95, verify 416.5 ps).
# OpenSTA removes launch source insertion in clk_skew but retains capture insertion; restore it using
# the signed source-port clock arrival measured before path searches. This matters for early hard-core taps.
# Each credited pair is cross-checked against the CK pin arrivals (Cmin + crpr - Lmax etc.); max |difference| is
# reported as verify_ps (a large value means an edge/arrival mismatch -- treat the measurement as suspect).
#
# ACTIVE EDGE (FLOW-CLOCK-R4 10-29, DIE-S81-28 H0 verify 14.75/7.79 ps): each register CK arrival is read on the
# transition the register actually samples on (ot_ps_edge: the Liberty Clk-to-Q arc edge, same rule as clock_family.tcl
# ot_cf_active), i.e. the FALL arrival for a negedge (DFF_N) register, and a fall-edge launch restores the clock source's
# fall insertion.  Rise-only reads compared a fall-edge launch path with rise CK arrivals (tree rise/fall delay
# difference = false verify mismatch).  A cell without one unique Clk-to-Q edge keeps the rise read (previous behaviour);
# rising-edge registers are unchanged.
#
# ARC CLOCK ROLES (HEAD LEP dual-clock SRAM): capture setup/hold pins and edges
# come from the checked DATA pin's timing arcs; launch clocks come from Clk-to-Q.
# An instance may have multiple clocks, and a write-only SRAM WCLK need not be
# returned by all_registers -clock_pins. Such clocks are added on discovery, with
# separate clock/edge records and exact clock-pin target offsets. Ambiguous or
# incomplete check roles fail closed rather than borrowing another instance pin.
#
# OpenSTA pitfall (sta_die.tcl): an arrival query while PathEnd objects are live re-runs the search and frees them.
# All CK arrivals are read BEFORE any path search; path-end values are copied into Tcl values at once.
#
# This script must NOT change the session's SDC beyond the clock uncertainty (ot_ps_zero_unc), which the caller
# runs last-in-session or restores.  It never re-reads an SDC and never touches clock source latency.
#
# TARGET-RELATIVE SKEW (opt-in, COORD 2026-10-28 21:33 rule 2: "the skew report must measure arrival minus planned
# target"; same definition as die_sta_related kit_offset / DIE-S81-17 D = (lc + latB) - (ea + latA) - cr).  A hard core
# with a signed internal clock latency L is planned EARLY: its clock pin target is T - L (tap_balance.tcl CP2 core pass:
# EFFECTIVE arrival = pin arrival + internal latency).  With a target file loaded (ot_ps_load_targets, the kit's
# core_latency.txt at TT / core_latency_ff.txt at FF: `inst pin L_ps ...`), every clock sink is measured relative to its
# planned target: effective arrival = pin arrival + L (L = 0 for ordinary registers), so with d = L_capture - L_launch
#   setup: s_t = s + d   (damage -s_t = -s - d)        hold: h_t = h + d   (damage +h_t = h + d)
# CPPR credit is unchanged (d is a per-pair constant, so the raw bound, the early stop and the verify cross-check carry
# over).  The pin-arrival measurement (all keys above, meaning unchanged) is still written; the target-relative one is
# added as ${dly}_tgt_* keys + PT rows, and gate_basis target_relative says the gate reads the tgt keys.  No file
# loaded: no extra key, output byte-identical.
#
# env (standalone): OT_PS_OUT (TSV path), CORNER (label), OT_PS_CREDIT_MAX (default 5000), OT_PS_TARGETS (target file).
# OT_PS_CORNER: explicit OpenSTA corner name for a multi-corner diagnostic session;
# filters BOTH raw clock tags and credited path searches. Unset retains single-corner behavior.
# TSV: H <key> <value> ; P <max|min> <launch> <capture> <skew_ps> <crpr_ps> <raw_damage_ps> ; PT (same, target-relative)

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

proc ot_ps_load_targets {fn} {
  # planned clock-pin earliness L (ps) per `inst pin L ...` line (gen_phys core_latency*.txt; '#' comments skipped)
  set ::ot_ps_tfile $fn
  set ::ot_ps_tpin {}
  set fh [open $fn]
  foreach l [split [read $fh] "\n"] {
    if {[string match "#*" [string trim $l]] || [llength $l] < 3} continue
    lassign $l i p v
    if {![string is double -strict $v]} { close $fh; error "ot_ps_load_targets: $fn: bad latency in '$l'" }
    dict set ::ot_ps_tpin "$i/$p" [expr {double($v)}]
  }
  close $fh
}

proc ot_ps_off {inst} {
  # planned earliness L of a register instance's clock pin (0 = ordinary register / no target file)
  if {[info exists ::ot_ps_toff] && [dict exists $::ot_ps_toff $inst]} { return [dict get $::ot_ps_toff $inst] }
  return 0.0
}

proc ot_ps_edge {pin} {
  # active CK transition (rise|fall) of a register clock pin from its Liberty Clk-to-Q arc (report_edges, as
  # clock_family.tcl ot_cf_active), cached per {ref_name lib_pin}; rise when there is no unique Clk-to-Q edge.
  if {[catch {
    set key [list [get_property [get_cells -of_objects $pin] ref_name] [get_property $pin lib_pin_name]]
  }]} { return rise }
  if {![info exists ::ot_ps_edge_cache]} { set ::ot_ps_edge_cache {} }
  if {[dict exists $::ot_ps_edge_cache $key]} { return [dict get $::ot_ps_edge_cache $key] }
  set edges {}
  if {![catch {
    sta::redirect_string_begin
    set failed [catch {report_edges -from $pin}]
    set report [sta::redirect_string_end]
  }] && !$failed} {
    set on 0
    foreach line [split $report \n] {
      if {[regexp {^\S} $line]} { set on [regexp {Clk to Q} $line]; continue }
      if {$on && [regexp {^\s+([\^v])\s+->} $line -> e] && $e ni $edges} { lappend edges $e }
    }
  }
  set rf [expr {$edges eq "v" ? "fall" : "rise"}]
  dict set ::ot_ps_edge_cache $key $rf
  return $rf
}

proc ot_ps_ckarr {pin clk which {rf rise}} {
  # propagated CLOCK arrival (ps, latency from the launching clock edge) of a register clock pin, min or max, on CK
  # transition rf (rise|fall), from the pin's "(clock prop)" path tags of that clock only.  get_property
  # arrival_*_rise is NOT used by default: it is the max/min over every tag on the pin, so a data arrival riding the clock net (10-24 routed smoke, qkd_ctrl_kc: an
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
        set it [$v path_iterator $rf $which]
        while {[$it has_next]} {
          set pa [$it next]; set tag [$pa tag]; set e [lindex $tag 4]
          if {[lindex $tag 3] ne $cn || $e ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
          if {[info exists ::env(OT_PS_CORNER)] && [lindex $tag 1] ne $::env(OT_PS_CORNER)} continue
          set x [expr {[$pa arrival] * 1e12 - [lindex $wf [expr {$e eq "^" ? 0 : 1}]]}]
          if {[lsearch -real $vals $x] < 0} { lappend vals $x }
        }
        $it finish
      }
    } err]} {
      if {[llength $vals] == 1} { return [lindex $vals 0] }
      return ""
    }
    if {[info exists ::env(OT_PS_CORNER)]} {error "OT_PS_CORNER requires clock-tag API: $err"}
    set ::ot_ps_method "property"
    puts "OT_PS_WARN clock-tag arrival API unavailable ($err); falling back to arrival_${which}_rise"
  }
  if {[catch {set a [get_property $pin arrival_${which}_$rf]}] || $a eq "" || [string match *INF* $a]} { return "" }
  return $a
}

# Clock roles belong to the data timing arc, not to a register instance.
# Write-only SRAM clocks need not appear in all_registers -clock_pins.
proc ot_ps_parse_role {report role} {
  set out {}; set source ""; set enabled 0
  foreach line [split $report \n] {
    if {[regexp {^(\S+)\s+->\s+(\S+)\s+(.+)$} $line -> from to kind]} {
      set source $from
      set enabled [expr {$role eq "clkq" ? [regexp -nocase {Clk to Q} $kind] : [string equal -nocase [string trim $kind] $role]}]
      continue
    }
    if {$enabled && [regexp {^\s+([\^v])\s+->} $line -> edge]} {
      lappend out [list $source [expr {$edge eq "^" ? "rise" : "fall"}]]
    }
  }
  return [lsort -unique $out]
}
proc ot_ps_clock_role {pin role} {
  set owners [get_cells -quiet -of_objects $pin]
  if {[llength $owners] != 1} { return {} }
  set key [list [get_property [lindex $owners 0] ref_name] [get_property $pin lib_pin_name] $role]
  if {![info exists ::ot_ps_role_cache]} {set ::ot_ps_role_cache {}}
  if {![dict exists $::ot_ps_role_cache $key]} {
    sta::redirect_string_begin
    set failed [catch {report_edges -to $pin} message]
    set report [sta::redirect_string_end]
    if {$failed} {error "ot_ps_clock_role: report_edges failed for [get_full_name $pin]: $message"}
    set found [ot_ps_parse_role $report $role]
    # OpenSTA startpoints may be the sequential output or its source clock
    # pin. Both are resolved through the actual Clk-to-Q arc, never by instance.
    if {$role eq "clkq" && ![llength $found]} {
      sta::redirect_string_begin
      set failed [catch {report_edges -from $pin} message]
      set report [sta::redirect_string_end]
      if {$failed} {error "ot_ps_clock_role: report_edges failed for [get_full_name $pin]: $message"}
      set found [ot_ps_parse_role $report $role]
    }
    if {[llength $found] > 1} {error "ot_ps_clock_role: ambiguous $role clock/edge for [get_full_name $pin]: $found"}
    dict set ::ot_ps_role_cache $key $found
  }
  set found [dict get $::ot_ps_role_cache $key]
  if {![llength $found]} {return {}}
  lassign [lindex $found 0] formal rf
  set full "[ot_ps_inst [get_full_name $pin]]/$formal"
  set clocks [get_pins -quiet $full]
  if {[llength $clocks] != 1} {error "ot_ps_clock_role: missing/nonunique actual clock pin $full"}
  return [list [lindex $clocks 0] $rf]
}
# Native get_fanin may return a constant SRAM DATA input itself (its wire and
# checks are disabled by constant). It is a capture endpoint, not a launch.
# Require actual input/nonclock role, setup+hold checks and an EMPTY forward
# edge report. A through arc, unknown report or reporter error remains held.
proc ot_ps_capture_only_input {pin} {
  set name [get_full_name $pin]
  if {[dict exists $::ot_ps_nonlaunch_cache $name]} {return [dict get $::ot_ps_nonlaunch_cache $name]}
  if {[get_property $pin direction] ne "input" || [get_property $pin is_clock]} {return 0}
  if {![llength [ot_ps_clock_role $pin setup]] || ![llength [ot_ps_clock_role $pin hold]]} {return 0}
  sta::redirect_string_begin
  set failed [catch {report_edges -from $pin} message]
  set report [sta::redirect_string_end]
  if {$failed} {error "ot_ps_capture_only_input: report_edges failed for [get_full_name $pin]: $message"}
  # The pinned native reporter emits an empty string for no edges. Any
  # unrecognized nonempty output, including a possible through arc, is held.
  set result [expr {[string trim $report] eq ""}]
  dict set ::ot_ps_nonlaunch_cache $name $result
  return $result
}

proc ot_ps_add_clock {pin rf} {
  set full [get_full_name $pin]; set key [list $full $rf]
  if {[dict exists $::ot_ps_by_clock $key]} {return [dict get $::ot_ps_by_clock $key]}
  set cl [get_property $pin clocks]
  if {[llength $cl] != 1} {incr ::ot_ps_noarr;return ""}
  set a [ot_ps_ckarr $pin [lindex $cl 0] max $rf];set b [ot_ps_ckarr $pin [lindex $cl 0] min $rf]
  if {$a eq "" || $b eq ""} {incr ::ot_ps_noarr;return ""}
  set cn [get_full_name [lindex $cl 0]]
  set ik [expr {$rf eq "rise" ? $cn : "$cn fall"}]
  if {![dict exists $::ot_ps_insertion $ik]} {
    set roots {}
    foreach src [get_property [lindex $cl 0] sources] {
      set late [ot_ps_ckarr $src [lindex $cl 0] max $rf];set early [ot_ps_ckarr $src [lindex $cl 0] min $rf]
      if {$late ne "" && $early ne ""} {lappend roots [list $late $early]}
    }
    set roots [lsort -unique $roots]
    if {[llength $roots]!=1} {error "clock $cn has no unique $rf source insertion arrival"}
    dict set ::ot_ps_insertion $ik [lindex $roots 0]
  }
  set inst [ot_ps_inst $full];set ref $inst
  if {[dict exists $::ot_ps_R $ref]} {set ref "$inst@[lindex [split $full /] end]:$rf"}
  if {[dict exists $::ot_ps_R $ref]} {error "ot_ps_add_clock: clock reference collision $ref"}
  dict set ::ot_ps_R $ref [list $full $cn $a $b $rf]
  dict set ::ot_ps_by_clock $key $ref
  if {[info exists ::ot_ps_tpin] && [dict exists $::ot_ps_tpin $full]} {
    dict set ::ot_ps_toff $ref [dict get $::ot_ps_tpin $full]
    dict set ::ot_ps_tmatched $full 1
  }
  return $ref
}
proc ot_ps_regs {} {
  set ::ot_ps_R {};set ::ot_ps_by_clock {};set ::ot_ps_nonlaunch_cache {};set ::ot_ps_insertion {};set ::ot_ps_toff {};set ::ot_ps_tmatched {};set ::ot_ps_noarr 0
  foreach p [all_registers -clock_pins] {ot_ps_add_clock $p [ot_ps_edge $p]}
  return $::ot_ps_R
}
proc ot_ps_related {R} {
  set async {};foreach p [all_registers -async_pins] {dict set async [get_full_name $p] 1}
  set P {};set nx 0;set nd 0
  foreach d [all_registers -data_pins] {
    set dn [get_full_name $d]
    if {[dict exists $async $dn]} continue
    set setup [ot_ps_clock_role $d setup];set hold [ot_ps_clock_role $d hold]
    if {[llength $setup]!=2 || [llength $hold]!=2} {error "ot_ps_related: incomplete setup/hold clock role for $dn"}
    set cs [ot_ps_add_clock {*}$setup];set ch [ot_ps_add_clock {*}$hold]
    if {$cs eq "" || $ch eq ""} continue
    incr nd
    lassign [dict get $::ot_ps_R $cs] - cclk - cearly
    lassign [dict get $::ot_ps_R $ch] - hclk clate
    foreach s [get_fanin -to $d -startpoints_only -flat] {
      set launch [ot_ps_clock_role $s clkq]
      if {![llength $launch]} {
        if {[dict exists $::ot_ps_R [ot_ps_inst [get_full_name $s]]]} {
          if {[ot_ps_capture_only_input $s]} continue
          error "ot_ps_related: unresolved sequential launch clock for [get_full_name $s]"
        }
        continue
      }
      set l [ot_ps_add_clock {*}$launch]
      if {$l eq ""} continue
      lassign [dict get $::ot_ps_R $l] - lclk llate learly
      if {$lclk ne $cclk || $lclk ne $hclk} {incr nx;continue}
      set ds [expr {$llate-$cearly}];set dh [expr {$clate-$learly}]
      set k [list $l $cs $ch]
      if {[dict exists $P $k]} {
        lassign [dict get $P $k] - - - os oh
        if {$ds<=$os && $dh<=$oh} continue
        set ds [expr {max($ds,$os)}];set dh [expr {max($dh,$oh)}]
      }
      dict set P $k [list $l $cs $dn $ds $dh $ch]
    }
  }
  return [list $P [dict size $P] $nx $nd]
}

proc ot_ps_path {l dn dly} {
  # exact credited skew of one pair and check: {skew_ps crpr_ps} or {} when no constrained reg->reg path exists
  set lck [get_pins -quiet "[lindex [dict get $::ot_ps_R $l] 0]"]
  set corner_args {}
  if {[info exists ::env(OT_PS_CORNER)]} {
    if {$::env(OT_PS_CORNER) eq ""} {error "OT_PS_CORNER must name an exact OpenSTA corner"}
    set corner_args [list -corner $::env(OT_PS_CORNER)]
  }
  if {![llength $lck]} {return {}}
  if {[catch {set pes [find_timing_paths -from $lck -to [get_pins $dn] -path_delay $dly \
                                              -group_path_count 1 -endpoint_path_count 1 {*}$corner_args]} error]} {
    if {[llength $corner_args]} {error "OT_PS_CORNER path search failed: $error"}
    return {}
  }
  if {![llength $pes]} {return {}}
  set pe [lindex $pes 0]
  if {![$pe is_check] || [$pe is_latch_check]} { return {} }
  set role [$pe check_role]
  set tp [$pe target_clk_path]
  if {$tp eq "NULL" || $tp eq ""} { return {} }
  set per [expr {[get_property [$pe target_clk] period] * 1e-12}]
  set sk [$pe clk_skew]; set req [$pe data_required_time]; set tarr [$tp arrival]; set mg [$pe margin]
  # PathEndCheck::sourceClkDelay subtracts source insertion from the launch
  # path; targetClkDelay keeps capture insertion. Restore the launch insertion
  # so both sides use full physical CK arrivals (including signed early taps).
  # (a fall-edge launch removes the source's FALL insertion: ot_ps_regs keys it "clock fall")
  lassign [dict get $::ot_ps_R $l] - lc - - lrf
  set ik [expr {$lrf eq "fall" ? "$lc fall" : $lc}]
  set ins_ps [lindex [dict get $::ot_ps_insertion $ik] [expr {$dly eq "max" ? 0 : 1}]]
  set sk [expr {$sk + $ins_ps * 1e-12}]
  unset pes pe tp
  if {$role eq "setup"} {
    set x [expr {$req - $tarr + $mg}]
    set crpr [expr {$x - $per * round($x / $per)}]
    set sk [expr {-$sk}]
  } elseif {$role eq "hold"} {
    set x [expr {$req - $tarr - $mg}]
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

proc ot_ps_check {P dly credit_max tgt} {
  # one check (max = setup, min = hold) over the related pairs P: pin-arrival skew (tgt 0) or target-relative skew
  # (tgt 1: signed skew + d, d = L_capture - L_launch; raw damage -d setup / +d hold)
  set idx [expr {$dly eq "max" ? 3 : 4}]
  set raw {}
  dict for {k v} $P {
    set rd [lindex $v $idx]
    if {$dly eq "min" && [llength $v] > 5} {set v [lreplace $v 1 1 [lindex $v 5]]}
    if {$tgt} {
      set d [expr {[ot_ps_off [lindex $v 1]] - [ot_ps_off [lindex $v 0]]}]
      set rd [expr {$dly eq "max" ? $rd - $d : $rd + $d}]
    }
    lappend raw [list $rd [lindex $v 0] [lindex $v 1] [lindex $v 2]]
  }
  set raw [lsort -real -decreasing -index 0 $raw]
  set worst ""; set wrow {}; set rows {}; set ns 0; set nnp 0; set vfy 0.0; set bounded 0; set next ""
  foreach r $raw {
    lassign $r rd l c dn
    if {$worst ne "" && $rd <= $worst} { set next ""; break }
    if {$ns >= $credit_max} { set bounded 1; set next $rd; break }
    incr ns
    set pk "$l\t$dn\t$dly"
    if {[dict exists $::ot_ps_pc $pk]} { set e [dict get $::ot_ps_pc $pk] } else {
      set e [ot_ps_path $l $dn $dly]; dict set ::ot_ps_pc $pk $e
    }
    if {![llength $e]} { incr nnp; continue }
    lassign $e sk cr
    if {$tgt} { set sk [expr {$sk + [ot_ps_off $c] - [ot_ps_off $l]}] }
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
  return [dict create n [llength $raw] worst [expr {$worst eq "" ? "NA" : [format %.2f $worst]}] \
    bounded $bounded signed [expr {$wsk eq "" ? "NA" : [format %.2f $wsk]}] launch $wl capture $wc \
    crpr [expr {$wcr eq "" ? "NA" : [format %.2f $wcr]}] p99_raw $p99 searched $ns nopath $nnp \
    verify [format %.3f $vfy] rows $rows]
}

proc ot_ps_measure {{credit_max 5000}} {
  # -> dict: pairs inter_clock data_pins ; per check (max|min): n worst bounded signed launch capture crpr p99_raw
  #    searched nopath verify rows ({launch capture skew crpr raw}); with a target file also tgt_max / tgt_min (same
  #    keys, target-relative) + target_file target_pins target_unmatched
  set ::ot_ps_method tag
  # complete timing update BEFORE any arrival / path-tag query (sta_die.tcl: arrival-first segfaults be771a0)
  sta::worst_slack_cmd max; sta::worst_slack_cmd min
  set ::ot_ps_R [ot_ps_regs]
  set ::ot_ps_pc {}
  lassign [ot_ps_related $::ot_ps_R] P np nx nd
  set out [dict create pairs $np inter_clock $nx data_pins $nd regs [dict size $::ot_ps_R] no_clock_arrival \
             $::ot_ps_noarr method $::ot_ps_method]
  foreach dly {max min} { dict set out $dly [ot_ps_check $P $dly $credit_max 0] }
  if {[info exists ::ot_ps_tpin]} {
    foreach dly {max min} { dict set out tgt_$dly [ot_ps_check $P $dly $credit_max 1] }
    dict set out target_file $::ot_ps_tfile
    dict set out target_pins [dict size $::ot_ps_tmatched]
    dict set out target_unmatched [expr {[dict size $::ot_ps_tpin] - [dict size $::ot_ps_tmatched]}]
  }
  unset ::ot_ps_pc
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
  if {[dict exists $M tgt_max]} {
    foreach k {target_file target_pins target_unmatched} { puts $fh "H\t$k\t[dict get $M $k]" }
    puts $fh "H\tgate_basis\ttarget_relative"
    foreach dly {max min} {
      set m [dict get $M tgt_$dly]
      foreach k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} {
        puts $fh "H\t${dly}_tgt_$k\t[dict get $m $k]"
      }
      foreach r [dict get $m rows] { puts $fh "PT\t$dly\t[join $r \t]" }
    }
  }
  close $fh
}

proc ot_ps_main {} {
  set corner [expr {[info exists ::env(CORNER)] ? $::env(CORNER) : "NA"}]
  set cm [expr {[info exists ::env(OT_PS_CREDIT_MAX)] ? $::env(OT_PS_CREDIT_MAX) : 5000}]
  set t0 [clock seconds]
  if {[info exists ::env(OT_PS_TARGETS)] && $::env(OT_PS_TARGETS) ne ""} { ot_ps_load_targets $::env(OT_PS_TARGETS) }
  set_propagated_clock [all_clocks]
  ot_ps_zero_unc
  set M [ot_ps_measure $cm]
  ot_ps_write $M $::env(OT_PS_OUT) $corner
  foreach dly {max min} {
    set m [dict get $M $dly]
    puts "OT_PS $corner $dly n [dict get $m n] worst [dict get $m worst] bounded [dict get $m bounded] signed [dict get $m signed] [dict get $m launch] -> [dict get $m capture] crpr [dict get $m crpr] p99_raw [dict get $m p99_raw] verify [dict get $m verify]"
  }
  if {[dict exists $M tgt_max]} {
    foreach dly {max min} {
      set m [dict get $M tgt_$dly]
      puts "OT_PS_TGT $corner $dly n [dict get $m n] worst [dict get $m worst] bounded [dict get $m bounded] signed [dict get $m signed] [dict get $m launch] -> [dict get $m capture] crpr [dict get $m crpr] p99_raw [dict get $m p99_raw] verify [dict get $m verify] targets [dict get $M target_pins] unmatched [dict get $M target_unmatched]"
    }
  }
  puts "OT_PS_DONE $corner [expr {[clock seconds] - $t0}] s"
}

if {![info exists ::ot_ps_lib_only] && [info exists ::env(OT_PS_OUT)]} { ot_ps_main }
