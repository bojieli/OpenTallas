# PRE_GLOBAL_PLACE hook (el1011-hbm-no3 2026-10-11): deterministic dont_touch delay stage AT THE PORT PIN of each
# hold-failing boundary port (OWNER 10-10 "hold-only miss -> delay stage at the boundary; no ECO loops").
# Derived from main's physical/dsrom_window_source/leaf_inhold.tcl (one dont_touch HB4xp67 per input), but the cells are
# placed at the PORT's pin location, not on the capture flop (flop-site placement caused RSZ-3006 elsewhere).
#   OT_PH_IN  = space-separated input port names (or "*" = every single-sink DFF-D data input, as leaf_inhold.tcl)
#   OT_PH_OUT = space-separated output port names: the stage goes between the port and everything that drove it
#   OT_PH_N   = cells per port (default 1); OT_PH_MASTER (default HB4xp67_ASAP7_75t_R)
# ot_hbm_w2_stn_hub_no2 (stnh-hub-no2a-2cf685462): the only FF hold violator is the forwarded clock clk_sm -> fclk_o
# (-3.60 ps routed-insertion IO, -4.29 after the loop hold ECO; every input->reg >= +6.79): synthesis folded the RTL's
# 4-inverter forwarding chain (held.fwdclk.u_clk0..3, no keep) into the clock net, so fclk_o left on a bare clock leaf.
# NOTE: ORFS sources this file inside a proc (source_env_var_if_exists), so every name the helper procs read is
# explicitly global (::ot_ph_*); a bare top-level `set` would be proc-local ("can't read ::ot_ph_blk", b91dca8f4).
set ::ot_ph_master [expr {[info exists ::env(OT_PH_MASTER)] ? $::env(OT_PH_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ::ot_ph_nper   [expr {[info exists ::env(OT_PH_N)] ? $::env(OT_PH_N) : 1}]
set ::ot_ph_in     [expr {[info exists ::env(OT_PH_IN)] ? $::env(OT_PH_IN) : ""}]
set ::ot_ph_out    [expr {[info exists ::env(OT_PH_OUT)] ? $::env(OT_PH_OUT) : ""}]
set ::ot_ph_blk [ord::get_db_block]
if {$::ot_ph_nper eq "" || ![string is integer -strict $::ot_ph_nper] || $::ot_ph_nper < 1} { set ::ot_ph_nper 1 }
if {[string trim "$::ot_ph_in$::ot_ph_out"] eq ""} { puts "PORTHOLD: OT_PH_IN/OT_PH_OUT empty, nothing to do"; return }
set ::ot_ph_m [[ord::get_db] findMaster $::ot_ph_master]
if {$::ot_ph_m eq "NULL"} { error "PORTHOLD: $::ot_ph_master missing" }
set ::ot_ph_k 0; set ::ot_ph_ports 0; set ::ot_ph_skip 0

proc ot_ph_xy {bt} {
  # pin location of a placed port, clamped into the core; else the core centre
  set core [$::ot_ph_blk getCoreArea]
  set lx [$core xMin]; set ly [$core yMin]; set ux [$core xMax]; set uy [$core yMax]
  set x [expr {($lx + $ux) / 2}]; set y [expr {($ly + $uy) / 2}]
  foreach bp [$bt getBPins] {
    set bb [$bp getBBox]
    set x [expr {([$bb xMin] + [$bb xMax]) / 2}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2}]
    break
  }
  set x [expr {max($lx, min($x, $ux - 2000))}]; set y [expr {max($ly, min($y, $uy - 2000))}]
  return [list $x $y]
}
proc ot_ph_cell {xy} {
  set name [format "ot_porthold_%05d" $::ot_ph_k]; incr ::ot_ph_k
  set c [odb::dbInst_create $::ot_ph_blk $::ot_ph_m $name]
  lassign $xy x y
  $c setLocation $x $y; $c setPlacementStatus PLACED
  return $c
}
proc ot_ph_net {} { return [odb::dbNet_create $::ot_ph_blk [format "ot_porthold_n%05d" $::ot_ph_k]] }

foreach bt [$::ot_ph_blk getBTerms] {
  set pn [$bt getName]; set io [$bt getIoType]
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {$io eq "INPUT" && $::ot_ph_in ne "" && ($::ot_ph_in eq "*" || [lsearch -exact $::ot_ph_in $pn] >= 0)} {
    if {[$net getSigType] ne "SIGNAL"} { incr ::ot_ph_skip; continue }
    set its [$net getITerms]
    if {[llength $its] != 1} { incr ::ot_ph_skip; continue }
    set d [lindex $its 0]
    if {![string match "DFF*" [[[$d getInst] getMaster] getName]] || [[$d getMTerm] getName] ne "D"} { incr ::ot_ph_skip; continue }
    # port -> c0 -> ... -> c(N-1) -> capture D
    set xy [ot_ph_xy $bt]; set prev $net
    $d disconnect
    for {set i 0} {$i < $::ot_ph_nper} {incr i} {
      set c [ot_ph_cell $xy]; [$c findITerm A] connect $prev
      set prev [ot_ph_net]; [$c findITerm Y] connect $prev
    }
    $d connect $prev
    incr ::ot_ph_ports
  } elseif {$io eq "OUTPUT" && [lsearch -exact $::ot_ph_out $pn] >= 0} {
    # everything on the port's net except the port moves to a new driver-side net; the chain feeds the port's net
    set src [ot_ph_net]
    foreach it [$net getITerms] { $it disconnect; $it connect $src }
    foreach ob [$net getBTerms] { if {[$ob getName] ne $pn} { $ob disconnect; $ob connect $src } }
    if {[$net getSigType] eq "CLOCK"} { $src setSigType CLOCK }
    set xy [ot_ph_xy $bt]; set prev $src
    for {set i 0} {$i < $::ot_ph_nper} {incr i} {
      set c [ot_ph_cell $xy]; [$c findITerm A] connect $prev
      if {$i == $::ot_ph_nper - 1} { set prev $net } else { set prev [ot_ph_net] }
      [$c findITerm Y] connect $prev
    }
    incr ::ot_ph_ports
  }
}
if {$::ot_ph_k > 0} { set_dont_touch [get_cells ot_porthold_*] }
puts "PORTHOLD: $::ot_ph_ports ports, $::ot_ph_k dont_touch $::ot_ph_master cells at the port pins ($::ot_ph_nper per port), $::ot_ph_skip inputs skipped"
if {$::ot_ph_ports == 0 && ($::ot_ph_in ne "" || $::ot_ph_out ne "")} { error "PORTHOLD: no port matched (in {$::ot_ph_in} out {$::ot_ph_out})" }
