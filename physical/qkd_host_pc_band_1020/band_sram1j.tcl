# KV-HOST7 2026-10-20 PC sram1j: hard placement fence of every non-boundary standard cell into the central band
# and the centre channel (spec "pin_hook_after_flops", sourced after io_flop_at_pins.tcl).  Why: the 1e gate placed internal
# cells/control above the top macro row (y>590), giving 285 driver->terminal pairs >405 um (max 597.8 reset, 550.6 data;
# results/rtl/kv_host6_pc_1e_collect_1020).  Pattern of the KV-RST3 HROOT central fence (central_fence_s32v4.tcl).
# Classes: anchor = pin-hook listed cells; FIRM; port_chain = BUF/INV/HB reachable from ports through BUF/INV/HB only;
# tie / physical loose; every other standard cell -> INCLUSIVE region.  Hard macros are skipped.  No RTL/cycle change.
set pf_b [ord::get_db_block]
set pf_u [$pf_b getDbUnitsPerMicron]
set pf_name ot_pc_band_sram1j
if {[$pf_b findRegion $pf_name] ne "NULL"} { error "PC_BAND: region already exists; refuse duplicate hook" }
set pf_boxes {{2.16 216.0 473.04 334.8} {226.8 2.16 253.8 537.84}}
set pf_anchor [dict create]
foreach pf_file {ot_out_flop_at_pins.txt ot_inhold_firm.txt} {
  set pf_path [file join $::env(RESULTS_DIR) $pf_file]
  if {![file exists $pf_path]} { error "PC_BAND: missing boundary ownership list $pf_path (hook must run after io_flop_at_pins)" }
  set pf_f [open $pf_path r]
  foreach pf_n [split [read $pf_f] "\n"] { if {$pf_n ne ""} { dict set pf_anchor $pf_n 1 } }
  close $pf_f
}
proc pf_isbuf {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]}]
}
set pf_bnd [dict create]
set pf_q {}
set pf_seen [dict create]
foreach bt [$pf_b getBTerms] {
  set n [$bt getNet]
  if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND CLOCK}} { lappend pf_q $n }
}
while {[llength $pf_q]} {
  set n [lindex $pf_q 0]; set pf_q [lrange $pf_q 1 end]
  if {[dict exists $pf_seen [$n getName]]} continue
  dict set pf_seen [$n getName] 1
  foreach it [$n getITerms] {
    set i [$it getInst]
    if {![pf_isbuf $i] || [dict exists $pf_bnd [$i getName]]} continue
    dict set pf_bnd [$i getName] 1
    foreach ot [$i getITerms] {
      set on [$ot getNet]
      if {$on ne "NULL" && [$on getSigType] ni {POWER GROUND CLOCK} && ![dict exists $pf_seen [$on getName]]} { lappend pf_q $on }
    }
  }
}
set pf_members {}; set pf_area 0.0
set cnt [dict create anchor 0 firm_unlisted 0 port_chain 0 tie 0 physical 0 macro 0 central 0]
set pf_rep [open [file join $::env(RESULTS_DIR) ot_pc_band_members.tsv] w]
puts $pf_rep "instance\tmaster\tstatus\tclass"
foreach pf_i [$pf_b getInsts] {
  set nm [$pf_i getName]; set st [$pf_i getPlacementStatus]; set m [$pf_i getMaster]; set mn [$m getName]
  if {[$m isBlock]} { dict incr cnt macro; continue }
  set sig 0
  foreach it [$pf_i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { set sig 1; break } }
  if {[dict exists $pf_anchor $nm]} { set cls anchor
  } elseif {$st in {FIRM LOCKED COVER}} { set cls [expr {$sig ? "firm_unlisted" : "physical"}]
  } elseif {!$sig} { set cls physical
  } elseif {[string match "TIE*" $mn]} { set cls tie
  } elseif {[dict exists $pf_bnd $nm]} { set cls port_chain
  } else {
    set cls central
    if {[$pf_i getGroup] ne "NULL"} { error "PC_BAND: preexisting group on $nm; refuse overwrite" }
    lappend pf_members $pf_i
    set pf_area [expr {$pf_area + double([$m getWidth]) * [$m getHeight] / $pf_u / $pf_u}]
  }
  dict incr cnt $cls
  puts $pf_rep "$nm\t$mn\t$st\t$cls"
}
close $pf_rep
set pf_cap 0.0
foreach bb $pf_boxes { lassign $bb x0 y0 x1 y1; set pf_cap [expr {$pf_cap + ($x1-$x0)*($y1-$y0)}] }
puts [format "PC_BAND sram1j classes %s area_um2=%.3f capacity_um2=%.1f util=%.4f" $cnt $pf_area $pf_cap [expr {$pf_area / $pf_cap}]]
if {[dict get $cnt anchor] < 600} { error "PC_BAND: only [dict get $cnt anchor] pin-anchored cells; classification implausible" }
if {[llength $pf_members] < 1500} { error "PC_BAND: only [llength $pf_members] central cells; classification implausible" }
if {[dict get $cnt macro] != 4} { error "PC_BAND: expected 4 SRAM macros, found [dict get $cnt macro]" }
if {$pf_area > 0.6 * $pf_cap} { error "PC_BAND: central area $pf_area exceeds 60% of the fence" }
set pf_r [odb::dbRegion_create $pf_b $pf_name]
foreach bb $pf_boxes { odb::dbBox_create $pf_r {*}[lmap v $bb {expr {round($v * $pf_u)}}] }
$pf_r setRegionType INCLUSIVE
set pf_g [odb::dbGroup_create $pf_r ${pf_name}_group]
foreach pf_i $pf_members { $pf_g addInst $pf_i }
puts "PC_BAND sram1j fenced [llength $pf_members] cells"
