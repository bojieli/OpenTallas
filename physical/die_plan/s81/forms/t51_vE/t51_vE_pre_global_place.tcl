# DIE-S81-84 t51 vE: 2026-11-08. Same RTL, pins, outline and pin cycles as vD.
# Measured problem (vD ECO DB, -35.31 / -14.8 ft6, +5.7 / +18.6 ft7): the landing-ring CDC capture flops
# u_ring.n0[0] and u_ring.g1[0] take their D from the same inverter as the shared decode of tc[1]
# (_09145_ fanout 7 in ft6, _5047_ fanout 29 in ft7). Launch and capture flops are 10-30 um apart,
# but placement pulls the shared inverter 100-140 um away toward its other sinks, so the 416.5 ps
# set_max_delay path doubles back through a chain of long-wire repeaters.
# The sibling bits tg[1], tg[2] have dedicated drivers and are not critical.
# Change: give the two capture flops their own clone of the inverter, driven from the launch net.
# Logic is unchanged (same function on the same net); routed LEC compares against the original kit RTL.
source /work/t51_m5_120_pre_global_place_tcl.tcl

proc ot_ve_escape {s} {
  set out ""
  foreach c [split $s ""] {
    if {$c in {[ ] /}} { append out "\\" $c } else { append out $c }
  }
  return $out
}

proc ot_ve_find_inst {block name} {
  return [$block findInst [ot_ve_escape $name]]
}

proc ot_ve_output_iterm {inst} {
  foreach it [$inst getITerms] {
    if {[$it isOutputSignal]} { return $it }
  }
  return "NULL"
}

proc ot_ve_input_iterm {inst} {
  foreach it [$inst getITerms] {
    if {[$it isInputSignal]} { return $it }
  }
  return "NULL"
}

proc ot_ve_isolate {block ring ffs} {
  set prefix "u_bound.u_cland_${ring}"
  set clone_name [ot_ve_escape "${prefix}/ot_ve_cdc_inv"]
  if {[$block findInst $clone_name] ne "NULL"} {
    puts "OT_VE $ring: clone already present, nothing to do"
    return
  }
  set d_iterms {}
  set shared_net "NULL"
  foreach f $ffs {
    set inst [ot_ve_find_inst $block "${prefix}/u_ring.${f}"]
    if {$inst eq "NULL"} { error "OT_VE $ring: capture flop not found: $f" }
    set d [$inst findITerm D]
    if {$d eq "NULL"} { error "OT_VE $ring: $f has no D pin" }
    set net [$d getNet]
    if {$net eq "NULL"} { error "OT_VE $ring: $f D is unconnected" }
    if {$shared_net eq "NULL"} {
      set shared_net $net
    } elseif {[$shared_net getName] ne [$net getName]} {
      error "OT_VE $ring: capture flops do not share a D net: [$shared_net getName] vs [$net getName]"
    }
    lappend d_iterms $d
  }
  set driver "NULL"
  foreach it [$shared_net getITerms] {
    if {[$it isOutputSignal]} { set driver $it; break }
  }
  if {$driver eq "NULL"} { error "OT_VE $ring: shared net [$shared_net getName] has no instance driver" }
  set drv_inst [$driver getInst]
  set master [$drv_inst getMaster]
  if {![string match "INV*" [$master getName]]} {
    error "OT_VE $ring: driver [$drv_inst getName] is [$master getName], expected an inverter"
  }
  set in_it [ot_ve_input_iterm $drv_inst]
  set launch_net [$in_it getNet]
  if {$launch_net eq "NULL"} { error "OT_VE $ring: inverter input unconnected" }
  set fanout [expr {[llength [$shared_net getITerms]] - 1}]
  if {$fanout <= [llength $ffs]} {
    error "OT_VE $ring: net [$shared_net getName] fanout $fanout has no other sinks to isolate from"
  }
  set clone [odb::dbInst_create $block $master $clone_name]
  set new_net [odb::dbNet_create $block [ot_ve_escape "${prefix}/ot_ve_cdc_d"]]
  $new_net setSigType SIGNAL
  [ot_ve_input_iterm $clone] connect $launch_net
  [ot_ve_output_iterm $clone] connect $new_net
  foreach d $d_iterms {
    $d disconnect
    $d connect $new_net
  }
  puts "OT_VE $ring: cloned [$drv_inst getName] ([$master getName]), launch [$launch_net getName], moved [llength $ffs] capture D pins off [$shared_net getName] (fanout $fanout -> [expr {$fanout - [llength $ffs]}]) onto ${prefix}/ot_ve_cdc_d"
}

set ot_ve_block [ord::get_db_block]
ot_ve_isolate $ot_ve_block ft6_i {n0[0]$_DFF_N_ g1[0]$_DFF_P_}
ot_ve_isolate $ot_ve_block ft7_i {n0[0]$_DFF_N_ g1[0]$_DFF_P_}
global_connect
