# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
# --- inlined cross_clock_paths.tcl (cts_native_probe: the probe runs as /probe.tcl in the container)
# CROSS-CLOCK GATE (CX-IJ-ROOT 2026-10-18, HBM SU cxport dl/rc 761317600): same-tile reg->reg paths BETWEEN two clocks
# of a multi-clock tile, timed under the kit's own signoff.sdc (so the distinct-entry reserve it applies, e.g.
# set_clock_uncertainty -setup 150/210 -hold 100 -from/-to every pair of different entries, and the related edge windows
# such as the 3:4 VCO tick, are exactly the sign-off ones; nothing is re-derived here).  A crossing is "declared" when an
# SDC exception covers it (set_false_path / set_multicycle_path / set_max_delay / set_min_delay recorded while the
# constraints are read, or STA's own path-delay flag); clock groups and false paths remove the path from STA anyway.
# Everything else is an ordinary synchronous crossing that the route must close at sign-off: one GATE_XCLK line per
# (launch, capture, max|min) pair; pre_route_gate.py fails a pair with undeclared setup slack < 0.
#
# Use: source this file BEFORE any read_sdc (installs the exception recorders), then call ot_xclk_report after the
# signoff SDC is read and parasitics are estimated.  Single-clock designs print GATE_XCLK_SCOPE clocks=1 and nothing else.
namespace eval ::ot_xclk { variable exc {} }

proc ::ot_xclk::names {v} {
  set out {}
  foreach e $v {
    set t ""
    catch {set t [sta::object_type $e]}
    if {$t eq "Clock"} { lappend out "clock:[get_name $e]"; continue }
    if {$t ne ""} { catch {lappend out [get_full_name $e]}; continue }
    set hit 0
    foreach c [get_clocks -quiet $e] { lappend out "clock:[get_name $c]"; set hit 1 }
    if {$hit} continue
    foreach o [concat [get_pins -quiet $e] [get_cells -quiet $e] [get_ports -quiet $e]] { lappend out [get_full_name $o] }
  }
  return $out
}

proc ::ot_xclk::note {kind argv} {
  if {[catch {
    set from {}; set to {}; set through 0; set setup 1; set hold 1
    if {$kind eq "max_delay"} { set hold 0 }
    if {$kind eq "min_delay"} { set setup 0 }
    set n [llength $argv]
    for {set i 0} {$i < $n} {incr i} {
      set a [lindex $argv $i]
      switch -- $a {
        -from - -rise_from - -fall_from { incr i; lappend from {*}[::ot_xclk::names [lindex $argv $i]] }
        -to - -rise_to - -fall_to { incr i; lappend to {*}[::ot_xclk::names [lindex $argv $i]] }
        -through - -rise_through - -fall_through { incr i; set through 1 }
        -comment { incr i }
        -setup { if {$kind in {false_path multicycle}} { set hold 0 } }
        -hold { if {$kind in {false_path multicycle}} { set setup 0 } }
      }
    }
    lappend ::ot_xclk::exc [dict create kind $kind from $from to $to through $through setup $setup hold $hold]
  } err]} { puts "GATE_XCLK_NOTE recorder could not parse $kind ($err); counted as declared"
    lappend ::ot_xclk::exc [dict create kind $kind from {} to {} through 1 setup 1 hold 1] }
}

proc ::ot_xclk::install {} {
  foreach {cmd kind} {set_false_path false_path set_multicycle_path multicycle set_max_delay max_delay set_min_delay min_delay} {
    if {![llength [info commands ::$cmd]] || [llength [info commands ::ot_xclk_orig_$cmd]]} continue
    rename ::$cmd ::ot_xclk_orig_$cmd
    proc ::$cmd {args} "::ot_xclk::note $kind \$args; uplevel 1 \[linsert \$args 0 ::ot_xclk_orig_$cmd\]"
  }
}

# The exception kind covering this path, or "" (undeclared).  kind max = setup, min = hold.
proc ::ot_xclk::declared {kind sp ep lc cc} {
  set S [list [get_full_name $sp] "clock:$lc"]; set E [list [get_full_name $ep] "clock:$cc"]
  foreach c [get_cells -quiet -of_objects $sp] { lappend S [get_full_name $c] }
  foreach c [get_cells -quiet -of_objects $ep] { lappend E [get_full_name $c] }
  foreach r $::ot_xclk::exc {
    if {![dict get $r [expr {$kind eq "max" ? "setup" : "hold"}]]} continue
    set f [dict get $r from]; set t [dict get $r to]
    set fo [expr {![llength $f]}]; set tm [expr {![llength $t]}]
    foreach x $S { if {$x in $f} { set fo 1; break } }
    foreach x $E { if {$x in $t} { set tm 1; break } }
    if {$fo && $tm} { return [dict get $r kind] }
  }
  return ""
}

proc ::ot_xclk::finite {v} { expr {[string is double -strict $v] && abs($v) < 1e20} }

proc ot_xclk_report {{limit 2000}} {
  set async {}
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  set clocks {}
  foreach c [all_clocks] { if {[llength [all_registers -clock $c -clock_pins]]} { lappend clocks $c } }
  set cn {}; foreach c $clocks { lappend cn [get_name $c] }
  puts "GATE_XCLK_SCOPE clocks=[llength $clocks] names=[join $cn ,] exceptions=[llength $::ot_xclk::exc]"
  set pairs 0
  if {[llength $clocks] >= 2} {
    foreach a $clocks {
      set from [all_registers -clock $a -clock_pins]
      foreach b $clocks {
        if {[get_name $a] eq [get_name $b]} continue
        set to {}
        foreach p [all_registers -clock $b -data_pins] { if {![dict exists $async [get_full_name $p]]} { lappend to $p } }
        if {![llength $to]} continue
        foreach kind {max min} {
          set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count $limit \
                       -endpoint_path_count 1 -sort_by_slack]
          set nu 0; set nd 0; set nv 0; set worst ""; set wsp -; set wep -; set dk {}
          foreach pe $paths {
            set s [get_property $pe slack]
            if {![::ot_xclk::finite $s]} continue
            set sp [get_property $pe startpoint]; set ep [get_property $pe endpoint]
            set d [::ot_xclk::declared $kind $sp $ep [get_name $a] [get_name $b]]
            if {$d eq "" && [$pe is_path_delay]} { set d max_delay }
            if {$d ne ""} { incr nd; if {$d ni $dk} { lappend dk $d }; continue }
            incr nu
            if {$s < 0} { incr nv }
            if {$worst eq "" || $s < $worst} { set worst $s; set wsp [get_full_name $sp]; set wep [get_full_name $ep] }
          }
          # the inter-clock uncertainty STA applied on the worst undeclared path (the signoff.sdc reserve), for the record
          set unc -
          if {$wep ne "-"} {
            catch {
              sta::redirect_string_begin
              report_checks -from [get_pins $wsp] -to [get_pins $wep] -path_delay $kind -format full_clock_expanded
              set rpt [sta::redirect_string_end]
              if {[regexp {(-?[0-9.]+)\s+[-0-9.]+\s+(?:\S+\s+)?inter-clock uncertainty} $rpt -> u] ||
                  [regexp {(-?[0-9.]+)[^\n]*clock uncertainty} $rpt -> u]} { set unc [expr {abs($u)}] }
            }
          }
          if {$worst eq ""} { set worst - } else { set worst [format %.1f $worst] }
          incr pairs
          puts "GATE_XCLK launch=[get_name $a] capture=[get_name $b] kind=$kind timed=$nu declared=$nd violating=$nv worst_ps=$worst uncertainty_ps=$unc startpoint=$wsp endpoint=$wep declared_kinds=[expr {[llength $dk] ? [join $dk ,] : "-"}] capped=[expr {[llength $paths] >= $limit}]"
        }
      }
    }
  }
  puts "GATE_XCLK_DONE pairs=$pairs"
}

::ot_xclk::install
# --- end cross_clock_paths.tcl
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner tt
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc (TT placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}

write_timing_model -library_name native_cts_probe_tt /work/native_probe_tt.lib
