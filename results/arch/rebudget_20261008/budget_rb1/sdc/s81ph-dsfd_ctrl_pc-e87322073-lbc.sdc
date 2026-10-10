# budget_rb1 for s81ph-dsfd_ctrl_pc-e87322073-lbc (block dsfd_ctrl_pc, tile of dsfd_ctrl), tools/budgets/rebudget.py derive 2026-10-08T20:58:51-07:00
# Re-derived IO budget from the REAL die links (die GRT parasitics / slab glue model) and REAL block needs
# (routed DB, zero-budget re-STA).  Read LAST (after io_ref_routed.sdc in a sign-off session).
# Ports re-budgeted: 6 of 6 linked (25 measured).  U_S 85 / U_H 50 are in the budget.
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
if {[llength $ot_rb_refs]} {
  ot_rb_vclocks $ot_rb_refs
  set u [sta::time_sta_ui 1e-12]
  set ot_rb_real [lmap r $ot_rb_refs {lindex $r 0}]
  # ci_w (in, core_clk): dsfd_ctrl:dsfd_ctrl_pc.co_w -> dsfd_ctrl:dsfd_ctrl_pc.ci_w C 514.7 need 93.7 -> 185.7
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {ci_w ci_w[*]}] { ot_rb_unset $ot_p in }
    set_input_delay -max [expr {($T - 185.7) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {ci_w ci_w[*]}]
    set_input_delay -min [expr {33.1 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {ci_w ci_w[*]}]
  } else { puts "OT_REBUDGET skip ci_w: no clock core_clk" }
  # co_w (out, core_clk): dsfd_ctrl:dsfd_ctrl_pc.co_w -> dsfd_ctrl:dsfd_ctrl_pc.ci_w C 514.7 need 231.0 -> 345.3; dsfd_ctrl:dsfd_ctrl_pc.co_w -> dsfd_ctrl:dsfd_ctrl_ctr.co_w C 597.6 need 231.0 -> 400.9
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {co_w co_w[*]}] { ot_rb_unset $ot_p out }
    set_output_delay -max [expr {($T - 345.3) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {co_w co_w[*]}]
    set_output_delay -min [expr {-72.4 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {co_w co_w[*]}]
  } else { puts "OT_REBUDGET skip co_w: no clock core_clk" }
  # r_beat (out, core_clk): ctrl_SW.rd -> svc_SW.rd C 745.1 need 197.5 -> 414.5
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {r_beat r_beat[*]}] { ot_rb_unset $ot_p out }
    set_output_delay -max [expr {($T - 414.5) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_beat r_beat[*]}]
    set_output_delay -min [expr {-45.6 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_beat r_beat[*]}]
  } else { puts "OT_REBUDGET skip r_beat: no clock core_clk" }
  # r_data (out, core_clk): ctrl_SW.rd -> svc_SW.rd C 745.1 need 212.0 -> 427.5
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {r_data r_data[*]}] { ot_rb_unset $ot_p out }
    set_output_delay -max [expr {($T - 427.5) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_data r_data[*]}]
    set_output_delay -min [expr {-37.4 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_data r_data[*]}]
  } else { puts "OT_REBUDGET skip r_data: no clock core_clk" }
  # r_tag (out, core_clk): ctrl_SW.rd -> svc_SW.rd C 745.1 need 228.0 -> 440.7
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {r_tag r_tag[*]}] { ot_rb_unset $ot_p out }
    set_output_delay -max [expr {($T - 440.7) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_tag r_tag[*]}]
    set_output_delay -min [expr {-44.5 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {r_tag r_tag[*]}]
  } else { puts "OT_REBUDGET skip r_tag: no clock core_clk" }
  # rv (out, core_clk): ctrl_SW.rd -> svc_SW.rd C 745.1 need 189.7 -> 407.1
  if {[lsearch -exact $ot_rb_real core_clk] >= 0} {
    set T [expr {[get_property [get_clocks core_clk] period] / $u}]
    foreach ot_p [get_ports -quiet {rv rv[*]}] { ot_rb_unset $ot_p out }
    set_output_delay -max [expr {($T - 407.1) * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {rv rv[*]}]
    set_output_delay -min [expr {-47.2 * $u}] -clock ot_rb_v_core_clk [get_ports -quiet {rv rv[*]}]
  } else { puts "OT_REBUDGET skip rv: no clock core_clk" }
  puts "OT_REBUDGET budget_rb1 s81ph-dsfd_ctrl_pc-e87322073-lbc ports 6"
}
