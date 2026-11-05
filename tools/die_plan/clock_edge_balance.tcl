# DIE-QC-75 11-05: POST_CTS, after tap_balance.tcl (uses its procs + tb_target/tb_win/tb_tol/tb_master).  Prints each root's
# arrival.  CTS's own latency balancing already aligns the groups of one port to its slowest chain (coll_s: clk_serdes 489-516,
# clk_coll 425-472), and that is kept: bypassing it gave 242-515 inside one domain.  A group below the plan insertion is padded
# up to it, the clk family rule.  One pin cannot reach 250 ps over 730 um (about 0.29 ps/um + 100 ps local tree).
if {[llength [info commands tb_sinks]] && [info exists ::env(OT_EDGE_SPLIT_PORTS)] && !([info exists ::env(OT_EDGE_SPLIT)] && $::env(OT_EDGE_SPLIT) eq "0")} {
  set eb_roots {}
  foreach i [$tb_blk getInsts] { if {[string match "ot_edge_root_*" [$i getName]]} { lappend eb_roots $i } }
  if {[llength $eb_roots]} {
    for {set eb_it 0} {$eb_it < 4} {incr eb_it} {
      set_propagated_clock [all_clocks]
      estimate_parasitics -placement
      ot_cf_refresh
      set eb_line {}; set eb_todo {}
      set eb_bad 0
      foreach i $eb_roots {
        set in ""; set out ""
        foreach t [$i getITerms] {
          if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue
          if {[[$t getMTerm] getIoType] eq "INPUT"} { set in $t } elseif {[[$t getMTerm] getIoType] eq "OUTPUT"} { set out $t }
        }
        set s 0.0; set n 0; set mn 1e9; set mx 0.0
        foreach p [tb_sinks [$out getNet]] {
          set pin [get_pins -quiet $p]
          if {$pin eq ""} continue
          if {[catch {set a [tb_rise $pin]} eb_err]} {
            incr eb_bad
            if {$eb_bad <= 5} { puts "OT_EDGE_BAL no arrival $p under [$i getName]: clocks {[lmap c [get_property $pin clocks] {get_full_name $c}]} net [[[$tb_blk findInst [lindex [split $p /] 0]] findITerm CLK] getNet]" }
            continue
          }
          if {$a eq ""} continue
          set s [expr {$s + $a}]; incr n; set mn [expr {min($mn, $a)}]; set mx [expr {max($mx, $a)}]
        }
        if {!$n} continue
        set m [expr {$s / $n}]
        append eb_line [format " %s=%.0f(%.0f-%.0f,%d)" [string range [$i getName] 13 end] $m $mn $mx $n]
        set d [expr {min($tb_target - $m, $tb_target + $tb_win - $mx)}]
        if {$d > $tb_tol} { lappend eb_todo [list $i $in $d] }
      }
      puts "OT_EDGE_BAL it$eb_it target [format %.0f $tb_target]:$eb_line"
      if {$eb_bad} { puts "OT_EDGE_BAL WARN $eb_bad sinks with no unique clock arrival" }
      if {![llength $eb_todo] || $eb_it == 3} break
      foreach e $eb_todo {
        lassign $e i in d
        lassign [$i getLocation] x y
        tb_hang $in [$in getNet] [expr {max(1, int(round($d / 18.0 * 0.75)))}] "[$i getName]_eb$eb_it" $x $y
      }
    }
  }
}
