# DIE-HEAD-16 DIAGNOSTIC: pair_skew.tcl unchanged, related pairs filtered to register<->register (hard-core pins excluded),
# to separate the register spine balance from the core early-tap target (cores were tapped for T=450).
set c $::env(CORNER)
set pat [expr {$c eq "TT" ? "*RVT_TT*" : "*RVT_FF*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] { read_liberty $l }
foreach l [glob /work/macros/*_[string tolower $c].lib] { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set ::ot_ps_lib_only 1
source /work/pair_skew.tcl
rename ot_ps_related ot_ps_related_orig
proc ot_ps_related {R} {
  lassign [ot_ps_related_orig $R] P np nx nd
  set Q [dict create]; set drop 0
  dict for {k v} $P {
    if {[regexp {g_cvb?\.u_e[AB][0-9]?$} [lindex $v 0]] || [regexp {g_cvb?\.u_e[AB][0-9]?$} [lindex $v 1]]} { incr drop; continue }
    dict set Q $k $v
  }
  puts "H16_PS dropped $drop core pairs, kept [dict size $Q]"
  return [list $Q [dict size $Q] $nx $nd]
}
ot_ps_main
