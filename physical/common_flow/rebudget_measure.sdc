# REBUDGET 2026-10-08 (tools/budgets/rebudget.py measure): the REAL per-port need of a routed block.
# Read LAST in a meas_resta.py session (--append physical/common_flow/io_ref_routed.sdc --append this file), so the IO
# reference is the routed boundary-register mean of the session's corner ($ot_ir_ins from io_ref_routed.sdc).
# Every common-clock data port gets a ZERO budget against a new virtual clock ot_rb_v at that reference, no IO
# uncertainty, and every other IO delay on the port is removed:
#   TT setup: input  slack = T - R   (R = pin -> capture flop + setup + reference - capture clock)
#             output slack = T - S   (S = reference -> launch flop clk->Q -> pin)
#   FF hold : input  slack = -h      (h = earliest arrival after the reference the receiver needs)
#             output slack = s_min   (s_min = earliest change at the pin after the reference)
# Prints one "OT_RB_PORT <port> <in|out> <slack_max_ps|INF> <slack_min_ps|INF>" line per port bit (the caller keeps
# slack_max from the TT session and slack_min from the FF session).  Ports of other clock domains are cut from ot_rb_v
# (false paths both ways), as link_budget_consistent.sdc does.  Measurement only: never a sign-off SDC.
# --- OT_RB_PROCS begin (copied verbatim into every generated budget_rb SDC by tools/budgets/rebudget.py) ---
proc ot_rb_reference {} {
  # {{real_clock latency_ui} ...} for every real clock with registers: the routed boundary mean (io_ref_routed.sdc) when
  # it ran in this session, else each port clock's report_clock_latency mid (ideal / pre-route sessions,
  # link_budget_consistent.sdc convention)
  set out {}
  if {[info exists ::ot_ir_ins] && [dict size $::ot_ir_ins]} {
    dict for {c v} $::ot_ir_ins { lappend out [list $c [lindex $v 0]] }
    return $out
  }
  foreach c [all_clocks] {
    set src [get_property $c sources]
    if {[llength $src] != 1 || [get_property $c is_generated]} continue
    if {![llength [get_ports -quiet [get_full_name [lindex $src 0]]]]} continue
    sta::redirect_string_begin; report_clock_latency -clock $c; set rs [sta::redirect_string_end]
    if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $rs -> lo hi]} { lappend out [list [get_full_name $c] [expr {($lo + $hi) / 2.0}]] }
  }
  return $out
}
proc ot_rb_data_ports {} {
  set src {}
  foreach c [all_clocks] { foreach s [get_property $c sources] { lappend src [get_full_name $s] } }
  set ins {}; set outs {}
  foreach p [all_inputs -no_clocks] {
    set n [get_full_name $p]
    if {[regexp -nocase {(^|[._])(rst|reset|por|rstn|rst_n|arst|rs|rss|rsv)($|[._\[])} $n] || [lsearch -exact $src $n] >= 0} continue
    lappend ins $p
  }
  foreach p [all_outputs] {
    set n [get_full_name $p]
    if {[lsearch -exact $src $n] >= 0 || [regexp -nocase {(^|[._])(rst|reset|por)($|[._\[])} $n]} continue
    lappend outs $p
  }
  return [list $ins $outs]
}
proc ot_rb_vclocks {refs} {
  # one virtual clock ot_rb_v_<clk> per real clock at its reference latency; each times only its own domain
  set real [lmap r $refs {lindex $r 0}]
  foreach r $refs {
    lassign $r rc L
    set vn ot_rb_v_$rc
    if {![llength [get_clocks -quiet $vn]]} {
      create_clock -name $vn -period [get_property [get_clocks $rc] period]
      foreach c [all_clocks] {
        set n [get_full_name $c]
        if {$n eq $vn || $n eq $rc || [string match ot_rb_v_* $n]} continue
        if {[get_property $c is_generated] && [lsearch -exact $real $n] < 0} {
          # a generated clock of THIS real clock stays timed; of another real clock it is cut
          set m $n
          for {set i 0} {$i < 8 && [get_property [get_clocks $m] is_generated]} {incr i} { set m [get_full_name [get_property [get_clocks $m] master_clock]] }
          if {$m eq $rc} continue
        }
        set_false_path -from [get_clocks $vn] -to $c; set_false_path -from $c -to [get_clocks $vn]
      }
      foreach o $real { if {$o ne $rc && [llength [get_clocks -quiet ot_rb_v_$o]]} {
        set_false_path -from [get_clocks $vn] -to [get_clocks ot_rb_v_$o]; set_false_path -from [get_clocks ot_rb_v_$o] -to [get_clocks $vn] } }
    }
    set_clock_latency -source 0 [get_clocks $vn]
    set_clock_latency $L [get_clocks $vn]
    # the budget already carries the die-link uncertainty (rebudget.py: setup 60 sign-off + 25 plan, hold 25 + 25)
    foreach a [list $vn $rc] b [list $rc $vn] {
      set_clock_uncertainty -setup 0 -from [get_clocks $a] -to [get_clocks $b]
      set_clock_uncertainty -hold 0 -from [get_clocks $a] -to [get_clocks $b]
    }
  }
}
proc ot_rb_domain {p dir} {
  # the real clock whose ot_rb_v_<clk> constrains port p (worst path through its first bit), else ""
  if {$dir eq "in"} { set pes [find_timing_paths -path_delay max -from $p -group_path_count 4 -endpoint_path_count 1]
  } else { set pes [find_timing_paths -path_delay max -to $p -group_path_count 4 -endpoint_path_count 1] }
  foreach pe $pes {
    if {[$pe is_unconstrained]} continue
    set c [get_full_name [get_property $pe [expr {$dir eq "in" ? "startpoint_clock" : "endpoint_clock"}]]]
    if {[string match ot_rb_v_* $c]} { return [string range $c 8 end] }
  }
  return ""
}
proc ot_rb_unset {p dir} {
  foreach c [all_clocks] {
    if {$dir eq "in"} { catch {unset_input_delay -clock $c $p} } else { catch {unset_output_delay -clock $c $p} }
  }
}
# --- OT_RB_PROCS end ---
set ot_rb_refs [ot_rb_reference]
if {![llength $ot_rb_refs]} { puts "OT_RB_MEASURE no reference clock" } else {
  set ot_rb_ports [ot_rb_data_ports]
  ot_rb_vclocks $ot_rb_refs
  foreach p [lindex $ot_rb_ports 0] { ot_rb_unset $p in; foreach r $ot_rb_refs { set_input_delay -max 0 -add_delay -clock ot_rb_v_[lindex $r 0] $p; set_input_delay -min 0 -add_delay -clock ot_rb_v_[lindex $r 0] $p } }
  foreach p [lindex $ot_rb_ports 1] { ot_rb_unset $p out; foreach r $ot_rb_refs { set_output_delay -max 0 -add_delay -clock ot_rb_v_[lindex $r 0] $p; set_output_delay -min 0 -add_delay -clock ot_rb_v_[lindex $r 0] $p } }
  set ot_rb_u [sta::time_sta_ui 1e-12]
  foreach r $ot_rb_refs { puts [format "OT_RB_REF %s %.1f T %.3f in %d out %d" [lindex $r 0] [expr {[lindex $r 1] / $ot_rb_u}] [expr {[get_property [get_clocks [lindex $r 0]] period] / $ot_rb_u}] [llength [lindex $ot_rb_ports 0]] [llength [lindex $ot_rb_ports 1]]] }
  set ot_rb_seen [dict create]
  foreach dir {in out} ps [list [lindex $ot_rb_ports 0] [lindex $ot_rb_ports 1]] {
    foreach p $ps {
      set v [list]
      foreach k {slack_max slack_min} {
        if {[catch {set s [get_property $p $k]}]} { set s INF }
        if {$s eq "INF" || $s eq "-INF" || $s eq "" || abs($s) > 1e20} { lappend v INF } else { lappend v [format %.2f [expr {$s / $ot_rb_u}]] }
      }
      set n [get_full_name $p]; regsub {\[[0-9]+\]$} $n {} b
      if {![dict exists $ot_rb_seen $b]} { dict set ot_rb_seen $b [set dom [ot_rb_domain $p $dir]]; puts "OT_RB_DOMAIN $b $dir [expr {$dom eq {} ? {-} : $dom}]" }
      puts "OT_RB_PORT $n $dir [lindex $v 0] [lindex $v 1]"
    }
  }
  # FORWARDED-CLOCK outputs (a clock-network output with no data domain, e.g. S81 fo = cks): the forwarded clock's
  # arrival at the pin relative to its source clock's reference, so rebudget.py judges a source-synchronous data bus in
  # the forwarded frame (S_fw = S - A).  A generated clock on the pin; A = its capture-clock delay on a data output of
  # the same clock.  Prints "OT_RB_FWDCLK <port> <clock> <A_max_ps> <A_min_ps>" (rebudget.py keeps max from the TT
  # session, min from the FF session).
  set ot_rb_i 0
  foreach p [lindex $ot_rb_ports 1] {
    set n [get_full_name $p]; regsub {\[[0-9]+\]$} $n {} b
    if {![dict exists $ot_rb_seen $b] || [dict get $ot_rb_seen $b] ne ""} continue
    foreach r $ot_rb_refs {
      lassign $r rc L
      set d0 ""
      dict for {ob od} $ot_rb_seen { if {$od eq $rc} { set d0 [lindex [get_ports -quiet [list $ob ${ob}\[0\]]] 0]; if {$d0 ne ""} break } }
      if {$d0 eq "" || [get_property $d0 direction] ne "output"} continue
      set gn ot_rb_fw_[incr ot_rb_i]
      if {[catch {create_generated_clock -name $gn -source [lindex [get_property [get_clocks $rc] sources] 0] -divide_by 1 $p}]} continue
      set_propagated_clock [get_clocks $gn]
      set_output_delay 0 -add_delay -clock $gn $d0
      set A {}
      foreach mm {max min} {
        set a NA
        foreach pe [find_timing_paths -path_delay $mm -to $d0 -group_path_count 8 -endpoint_path_count 4] {
          if {[$pe is_unconstrained] || [get_full_name [get_property $pe endpoint_clock]] ne $gn} continue
          set a [format %.1f [expr {[$pe target_clk_delay] * 1e12 - $L / $ot_rb_u}]]
          break
        }
        lappend A $a
      }
      catch {unset_output_delay -clock [get_clocks $gn] $d0}
      if {[lindex $A 0] ne "NA"} { puts "OT_RB_FWDCLK $n $rc [join $A { }]"; break }
    }
  }
}
