# tools/die_plan/ft_grt.tcl -- explicit FT track reservation in the kit GRT (PATH-KV-FTRES 2026-10-26).
# COORD ruling 2026-10-25 23:53: the reserved M4-M7 FT stripes (ft_reserve.py: middle half of every 8.64-um die lattice
# cell, the SAME tracks the die GRT model gives die feedthroughs) block ONLY the kit's own logic; the nets the plan
# declares as feedthroughs through this kit (ft_slots: ports <slot>_i / <slot>_o and the u_ft_<slot>_* station chain,
# incl. any buffer / inverter between them) route ON them.  OpenROAD (26Q3) has no per-net track / region restriction
# (no set_net_layer, region adjustments and odb obstructions apply to every net), so the reservation is two GRT passes
# with disjoint M4-M7 resources (GRT skips special nets):
#   pass FT : own nets special, the COMPLEMENT stripes (non-FT tracks) obstructed on M4-M7 -> FT nets on FT tracks only
#   pass OWN: FT nets special, the FT stripes obstructed on M4-M7               -> own nets off the FT tracks
#   then both route sets are merged (read_guides) so parasitics / repair / write_guides / DRT see every net.
# M2 / M3 keep the platform adjustment (the die model blocks M2/M3 over partitions, reservation 0 there); M4-M7 get
# adjustment 0: the explicit stripes replace the uniform ORFS 25%.  Data: ft_reserve.tcl (kit generator) sets
#   ot_ftres_slots {slot ...}  ot_ftres_ft {{L x0 y0 x1 y1} ...}  ot_ftres_nonft {{L x0 y0 x1 y1} ...}   (um, kit frame)
# Sourced from grt_pre.tcl (PRE_GLOBAL_ROUTE).  It wraps global_route: the FIRST full (non-incremental) call runs the
# two passes; incremental calls (repair_design / repair_timing DPL reroutes) go to the stock command unchanged.
# Limitation: incremental reroutes after the merge use the pass-OWN grid (FT stripes blocked), so an FT net that the
# GRT repair buffers is re-routed off the stripes; the post-GRT audit (ot_ftres_audit) counts such nets.
# ORFS sources step hooks inside a proc (source_step_tcl): the data goes to the global scope explicitly.
set ::ot_ftres_dir [file dirname [file normalize [info script]]]
if {![info exists ::ot_ftres_slots]} { uplevel #0 [list source [file join $::ot_ftres_dir ft_reserve.tcl]] }

proc ot_ftres_is_bufinv {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[regexp {^(BUF|INV|HB)} $m] && [llength [ot_ftres_sig_iterms $inst]] == 2}]
}
proc ot_ftres_sig_iterms {inst} {
  set out {}
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL"} { continue }
    if {[$n getSigType] in {POWER GROUND}} { continue }
    lappend out $it
  }
  return $out
}
# FT nets: seeds = nets on the FT slot ports + the D / Q(N) nets of the u_ft_<slot>_* station flops; closed through
# 1-in-1-out buffers / inverters (resizer / CTS-free repeaters).  Clock / reset nets are never FT.
proc ot_ftres_ft_nets {} {
  set blk [ord::get_db_block]
  set seen [dict create]
  set todo {}
  foreach bt [$blk getBTerms] {
    foreach s $::ot_ftres_slots {
      if {[regexp "^${s}_(i|o)(\\\[|$)" [$bt getName]]} { set n [$bt getNet]; if {$n ne "NULL"} { lappend todo $n } }
    }
  }
  foreach inst [$blk getInsts] {
    set nm [$inst getName]
    set hit 0
    foreach s $::ot_ftres_slots { if {[string match "u_ft_${s}_*" $nm]} { set hit 1; break } }
    if {!$hit} { continue }
    foreach it [ot_ftres_sig_iterms $inst] {
      set mt [[$it getMTerm] getName]
      if {$mt in {D Q QN A Y}} { lappend todo [$it getNet] }
    }
  }
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    set nn [$n getName]
    if {[dict exists $seen $nn]} { continue }
    if {[$n getSigType] in {POWER GROUND CLOCK RESET}} { continue }
    set clk 0
    foreach it [$n getITerms] { if {[[$it getMTerm] getName] in {CLK RESETN SETN}} { set clk 1; break } }
    if {$clk} { continue }
    dict set seen $nn $n
    foreach it [$n getITerms] {
      set inst [$it getInst]
      if {[ot_ftres_is_bufinv $inst]} { foreach j [ot_ftres_sig_iterms $inst] { lappend todo [$j getNet] } }
    }
  }
  return [dict values $seen]
}
proc ot_ftres_obs {rects} {
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]; set tech [ord::get_db_tech]
  set out {}
  foreach r $rects {
    lassign $r L a b c d
    lappend out [odb::dbObstruction_create $blk [$tech findLayer $L] [expr {round($a*$dbu)}] [expr {round($b*$dbu)}] \
                   [expr {round($c*$dbu)}] [expr {round($d*$dbu)}]]
  }
  return $out
}
proc ot_ftres_unobs {obs} { foreach o $obs { odb::dbObstruction_destroy $o } }
proc ot_ftres_set_special {nets v} { foreach n $nets { if {$v} { $n setSpecial } else { $n clearSpecial } } }
# guide merge: every FT net from the FT pass, every other net from the OWN pass (write_guides of the OWN pass also
# re-writes the FT nets' pass-FT routes, which GRT keeps for special nets: dropped here, so each net appears once)
proc ot_ftres_merge_guides {out ftf ownf ftn} {
  set fo [open $out w]
  set fi [open $ftf r]; puts -nonewline $fo [read $fi]; close $fi
  set fi [open $ownf r]; set keep 1; set name ""
  while {[gets $fi ln] >= 0} {
    set t [string trim $ln]
    if {$name eq "" && $t ne "(" && $t ne ")" && $t ne ""} { set name $t; set keep [expr {![dict exists $ftn $t]}] }
    if {$keep} { puts $fo $ln }
    if {$t eq ")"} { set name "" }
  }
  close $fi; close $fo
}
proc ot_ftres_run {args} {
  set blk [ord::get_db_block]
  set ft [ot_ftres_ft_nets]
  set ftn [dict create]; foreach n $ft { dict set ftn [$n getName] 1 }
  set own {}
  foreach n [$blk getNets] {
    if {[$n isSpecial] || [$n getSigType] in {POWER GROUND}} { continue }
    if {![dict exists $ftn [$n getName]]} { lappend own $n }
  }
  puts "OT_FTRES nets ft [llength $ft] own [llength $own] stripes ft [llength $::ot_ftres_ft] nonft [llength $::ot_ftres_nonft]"
  set wd [expr {[info exists ::env(OT_FTRES_DIR)] ? $::env(OT_FTRES_DIR) : $::env(RESULTS_DIR)}]
  # pass FT
  ot_ftres_set_special $own 1
  set obs [ot_ftres_obs $::ot_ftres_nonft]
  set r1 [catch { uplevel #0 [list ::ot_ftres_orig_global_route {*}$args] } e1]
  ot_ftres_unobs $obs
  ot_ftres_set_special $own 0
  if {$r1} { error "OT_FTRES pass FT: $e1" }
  write_guides $wd/ftres_ft.guide
  # pass OWN
  ot_ftres_set_special $ft 1
  set obs [ot_ftres_obs $::ot_ftres_ft]
  set r2 [catch { uplevel #0 [list ::ot_ftres_orig_global_route {*}$args] } e2]
  write_guides $wd/ftres_own.guide
  ot_ftres_unobs $obs
  ot_ftres_set_special $ft 0
  if {$r2} { error "OT_FTRES pass OWN: $e2" }
  ot_ftres_merge_guides $wd/ftres_all.guide $wd/ftres_ft.guide $wd/ftres_own.guide $ftn
  read_guides $wd/ftres_all.guide
  puts "OT_FTRES merged guides $wd/ftres_all.guide"
}
if {![llength [info commands ::ot_ftres_orig_global_route]]} {
  rename ::global_route ::ot_ftres_orig_global_route
  set ::ot_ftres_done 0
  proc ::global_route {args} {
    if {$::ot_ftres_done || "-start_incremental" in $args || "-end_incremental" in $args} {
      return [uplevel 1 [list ::ot_ftres_orig_global_route {*}$args]]
    }
    set ::ot_ftres_done 1
    return [ot_ftres_run {*}$args]
  }
}
set_global_routing_layer_adjustment M4-M7 0
puts "OT_FTRES hook armed: M4-M7 adjustment 0, explicit FT stripes (ft_reserve.tcl), two-pass GRT"
