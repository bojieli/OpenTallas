
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_FF_*] { read_liberty $l }
foreach l [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /ml0/ot_sram_1r1w_1024x256_m2_r2c2_ff.lib
read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
so CORNER FF
so PARASITICS spef
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "SO_PATH_BEGIN SDC_MAX"
report_checks -path_delay max -format full_clock_expanded -digits 2 -fields {slew cap fanout}
puts "SO_PATH_END"
# ---- standard boundary-hold overlay (4b7b2b3e64 kit standard) ----
if {[llength $so_vclk] == 1} {
  if {[llength $so_din]} { set_input_delay -min [expr {-40}] -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min 0 -clock [lindex $so_vclk 0] [all_outputs] }
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min -40 out_min 0
} else {
  so OVERLAY skipped vclks [llength $so_vclk]
}
so_timing STD
puts "SO_PATH_BEGIN STD_MIN"
report_checks -path_delay min -format full_clock_expanded -digits 2
puts "SO_PATH_END"
# ---- DRV ----
so SLEW_VIOL [sta::max_slew_violation_count]
so CAP_VIOL [sta::max_capacitance_violation_count]
set so_fo_max 0; set so_fo_n 0; set so_fo_worst ""
foreach n [get_nets -hierarchical *] {
  set k [llength [get_pins -quiet -of_objects $n -filter "direction==input"]]
  if {$k > $so_fo_max} { set so_fo_max $k; set so_fo_worst [get_full_name $n] }
  if {$k > 64} { incr so_fo_n }
}
so FANOUT_MAX $so_fo_max $so_fo_worst
so FANOUT_VIOL $so_fo_n
puts "SO_PATH_BEGIN DRV"
report_check_types -max_slew -max_capacitance -violators -max_count 10
puts "SO_PATH_END"
# ---- constraint coverage ----
puts "SO_PATH_BEGIN CHECK_SETUP"
check_setup -verbose -unconstrained_endpoints -no_clock -loops -generated_clocks -multiple_clock
puts "SO_PATH_END"
# ---- OCV sensitivity (information only) ----
set_timing_derate -late 1.05
set_timing_derate -early 0.95
so OCV5_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
so OCV5_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
unset_timing_derate
# ---- related flop-pair skew with CPPR (owner gate, BRIEFING decision 5) ----
# Measured on the golden SDC exactly as loaded (source latencies, propagated clocks, derate removed), BEFORE the
# insertion diagnostic below zeroes clock source latency; only the clock uncertainty is zeroed (clk_skew must not
# carry it) and nothing after this block reads slack.
set ::ot_ps_lib_only 1
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

unset ::ot_ps_lib_only
ot_ps_zero_unc
set so_t0 [clock seconds]
set so_pm [ot_ps_measure 5000]
ot_ps_write $so_pm /out/pair_skew.tsv FF
so PAIR_COUNTS regs [dict get $so_pm regs] no_clock_arrival [dict get $so_pm no_clock_arrival] data_pins [dict get $so_pm data_pins] pairs [dict get $so_pm pairs] inter_clock [dict get $so_pm inter_clock]
foreach dly {max min} {
  set m [dict get $so_pm $dly]
  so PAIR_$dly {*}[concat {*}[lmap k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} {list $k [dict get $m $k]}]]
}
so PAIR_METHOD [dict get $so_pm method]
so PAIR_SECONDS [expr {[clock seconds] - $so_t0}]
unset so_pm
so PAIR_DONE 1
# ---- clock: active-edge arrival at register clock pins, pin flops ----
# Actual OpenSTA clock ancestry and physical propagated-clock measurements.
# OpenSTA's Clock wrapper has no master accessor. Its canonical SDC exporter
# resolves inferred masters; evaluate only its generated-clock declarations in
# an isolated safe interpreter, never replay constraints in the live session.
proc ot_cf_record {args} {
  set ni [lsearch -exact $args -name]; set mi [lsearch -exact $args -master_clock]
  set si [lsearch -exact $args -source]
  if {$ni < 0 || $mi < 0 || $si < 0} {error "OT_CLOCK_FAMILY: canonical generated clock lacks resolved name/master/source"}
  set name [lindex $args [expr {$ni+1}]]
  set master [lindex $args [expr {$mi+1}]]; set source [lindex $args [expr {$si+1}]]
  if {[llength $master] != 1 || [llength $source] != 1 || [dict exists $::ot_cf_master $name]} {
    error "OT_CLOCK_FAMILY: ambiguous generated clock $name"
  }
  set parent [get_full_name $master]
  if {[sta::object_type $source] eq "Port"} {set source [sta::get_port_pin $source]}
  set owners {}; foreach c [get_property $source clocks] {lappend owners [get_full_name $c]}
  if {[lsort -unique $owners] ne [list $parent]} {
    error "OT_CLOCK_FAMILY: generated source of $name has owners $owners, expected $parent"
  }
  dict set ::ot_cf_master $name $parent
}
proc ot_cf_refresh {} {
  set ::ot_cf_master {}; set ::ot_cf_active_cache {}; set generated {}
  foreach c [all_clocks] {if {[$c is_generated]} {lappend generated [get_full_name $c]}}
  if {![llength $generated]} {return}
  sta::update_generated_clks
  # Iterating paths alone does not initialize generated source insertion.
  # A native timing search fills the complete root-to-bank physical arrivals.
  find_timing_paths -group_path_count 1
  set fd [file tempfile path ot-clock-family-]; close $fd
  set ip [interp create -safe]
  try {
    write_sdc $path
    foreach cmd {get_ports get_pins get_clocks} {interp alias $ip $cmd {} $cmd}
    interp alias $ip create_generated_clock {} ot_cf_record
    set fd [open $path r]; set text [read $fd]; close $fd
    set command {}
    foreach line [split $text \n] {
      append command $line \n
      if {![info complete $command]} continue
      if {[regexp {^\s*create_generated_clock\s} $command]} {interp eval $ip $command}
      set command {}
    }
    if {[string trim $command] ne ""} {error "OT_CLOCK_FAMILY: incomplete canonical SDC"}
    if {[lsort [dict keys $::ot_cf_master]] ne [lsort $generated]} {error "OT_CLOCK_FAMILY: incomplete generated-clock ancestry"}
    foreach c $generated {ot_cf_root $c}
  } finally {interp delete $ip; file delete -force $path}
}
proc ot_cf_root {name} {
  set seen {}
  while {[dict exists $::ot_cf_master $name]} {
    if {$name in $seen} {error "OT_CLOCK_FAMILY: ancestry cycle $name"}
    lappend seen $name; set name [dict get $::ot_cf_master $name]
  }
  set c [get_clocks -quiet $name]
  if {[llength $c] != 1 || [$c is_generated]} {error "OT_CLOCK_FAMILY: unresolved root $name"}
  return $name
}
proc ot_cf_pins {root} {
  set name [get_full_name $root]
  if {[ot_cf_root $name] ne $name} {error "OT_CLOCK_FAMILY: requested root $name is generated"}
  # Ordinary roots retain the existing all_registers ownership query. In
  # pre-CTS ideal sessions get_property(pin, clocks) can be empty on check-only
  # macro entries; all_registers -clock still proves actual graph membership.
  if {![dict size $::ot_cf_master]} {
    set pins [all_registers -clock_pins -clock $root]; set owners {}
    foreach p $pins {dict set owners [get_full_name $p] $root}
    return [list $pins $owners]
  }
  set pins {}; set owners {}
  foreach c [all_clocks] {
    if {[ot_cf_root [get_full_name $c]] ne $name} continue
    foreach p [all_registers -clock_pins -clock $c] {
      set pn [get_full_name $p]
      set actual {}; foreach owner [get_property $p clocks] {lappend actual [get_full_name $owner]}
      if {[llength [lsort -unique $actual]] != 1} {
        error "OT_CLOCK_FAMILY: ambiguous clock sink $pn ($actual)"
      }
      if {[ot_cf_root [lindex $actual 0]] ne $name} {error "OT_CLOCK_FAMILY: foreign sink $pn"}
      if {[lindex $actual 0] ne [get_full_name $c]} continue
      if {[dict exists $owners $pn]} {error "OT_CLOCK_FAMILY: duplicate sink $pn"}
      dict set owners $pn $c; lappend pins $p
    }
  }
  return [list $pins $owners]
}
proc ot_cf_active {p} {
  set cell [get_cells -of_objects $p]
  set key [list [get_property $cell ref_name] [get_property $p lib_pin_name]]
  if {[dict exists $::ot_cf_active_cache $key]} {return [dict get $::ot_cf_active_cache $key]}
  sta::redirect_string_begin
  set failed [catch {report_edges -from $p} message]
  set report [sta::redirect_string_end]; set on 0; set edges {}
  if {$failed} {error "OT_CLOCK_FAMILY: active-edge query failed [get_full_name $p]: $message"}
  foreach line [split $report \n] {
    if {[regexp {^\S} $line]} {set on [regexp {(Clk|En) to Q} $line]; continue}
    if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
  }
  if {![llength $edges] && [llength [info commands ord::get_db]]} {
    # Check-only hard entries (notably SRAM write clocks) have no clock-to-Q
    # arc. Only an actual physical BLOCK with unique loaded Liberty clock
    # timing-check edges is supported; missing soft-register arcs still fail.
    set master [[ord::get_db] findMaster [get_property $cell ref_name]]
    if {$master ne "NULL" && [$master isBlock]} {
      set on 0
      foreach line [split $report \n] {
        if {[regexp {^\S} $line]} {set on [regexp { (setup|hold|recovery|removal)$} $line]; continue}
        if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
      }
    }
  }
  if {[llength $edges] != 1} {error "OT_CLOCK_FAMILY: missing unique active clock edge [get_full_name $p] ($edges)"}
  set active [expr {[lindex $edges 0] eq "^" ? "rise" : "fall"}]
  dict set ::ot_cf_active_cache $key $active
  return $active
}
proc ot_cf_wire {pin clock {scene {}}} {
  return [ot_cf_wire_transition $pin $clock [ot_cf_active $pin] $scene]
}
# Also supports clock-buffer outputs, which have no sequential active-edge arc.
proc ot_cf_wire_transition {pin clock transition {scene {}}} {
  if {$transition ni {rise fall}} {error "OT_CLOCK_FAMILY: invalid transition $transition"}
  if {$scene eq ""} {set scene [get_property [sta::cmd_scene] name]}
  set cn [get_full_name $clock]; set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2} {error "OT_CLOCK_FAMILY: invalid waveform $cn"}
  foreach time $waveform {if {![string is double -strict $time] || [regexp -nocase {inf|nan} $time]} {error "OT_CLOCK_FAMILY: nonfinite waveform $cn"}}
  set marker [expr {$transition eq "rise" ? "^max" : "vmax"}]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator $transition max]
    while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; set edge [lindex $tag 4]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne $marker || [lindex $tag 3] ne $cn || $edge ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![string is double -strict $arrival] || [regexp -nocase {inf|nan} $arrival]} {$paths finish; error "OT_CLOCK_FAMILY: nonfinite clock arrival [get_full_name $pin]"}
      lappend values [expr {$arrival-[lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]}]
    }
    $paths finish
  }
  if {[llength $values] != 1} {error "OT_CLOCK_FAMILY: missing unique physical clock arrival [get_full_name $pin] clock=$cn scene=$scene"}
  return [lindex $values 0]
}

set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}
set so_data {}
set so_async {}
foreach p [all_registers -async_pins] { dict set so_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $so_async $n]} { dict set so_data $n 1 } }
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set so_ck_err 0
set so_cf [llength [info commands ot_cf_wire]]
if {$so_cf} { catch {ot_cf_refresh} }
dict for {i p} $so_regs {
  set cl [get_property $p clocks]
  if {[llength $cl] != 1} { incr so_ck_err; continue }
  set a ""
  if {$so_cf} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
  if {$a eq ""} {
    # get_property returns display units already (PropertyValue timeUnit);
    # converting again multiplies ASAP7 ps arrivals by 1e12.
    catch {set a [get_property $p arrival_max_rise]}
  }
  if {$a eq "" || ![string is double -strict $a]} { incr so_ck_err; continue }
  puts "SO_CK [expr {[dict exists $so_bnd $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
so CK_ERRORS $so_ck_err
so DONE 1
exit
