# vms_relay_lattice.tcl -- VM hub-glue g7 (L2H-PGVM-G7 2026-10-19), PRE_GLOBAL_PLACE (kit pin_hook_before_flops).
# WHY (placed census of the g6 r2 SW gate, 3_place.odb, tools/hbm_die_v16/vms_glue_hop_census.tcl): 70,083 of 114,320 flops
# sat on PURE flop -> flop hops and 29,495 of those hops were <= 50 um: the reach relays of every tile port chain
# (gen_vms_glue_tiles.py: pin flop + DB-1 / DD-1 / DC-1 relays) were placed by GPL wherever HPWL is flat -- next to each
# other -- so one hop carried the whole 400-950 um and the others were zero-wire hold endpoints (46,076 endpoints inside
# the 30 ps hold margin, ~40k CTS hold buffers, GATE_STALL).  A relay is a floorplan object: this hook puts every relay of
# a tile port chain (and the ring stop's mirror-egress landings a_eg / eg_m, the g7 eg reach relays) on its planned
# lattice point, FIRM through global placement, released for detailed placement (vms_relay_lattice_release.tcl).
#   hop plan: a chain of d stages between pin P and anchor A has d hops; relay j sits at fraction j/d of P -> A (input
#   chains: s0 = pin flop, s1.. toward the core; output chains: s0 next to the core, s(d-1) = pin flop renamed to the port).
#   anchors: lane band b (centroid of its four ring-lane port groups, OT_RL_INSET um inside the ring face) for xq / xq2 /
#   eg of bank b; the header band (ring headers + tx controls) for xq_done / xq2_done / mirror_busy / ring_fault; the hub
#   island (tile centre) for pq / pr / status / flt and the client ports.  Each bit keeps its place in the bus: the anchor
#   point of bit i is offset along the pin face by OT_RL_SPREAD x (pin_i - pin centroid).
# Placement only: no cells, nets or edges change (0 cycles).
global rl_blk rl_dbu rl_list
set rl_blk [ord::get_db_block]
set rl_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rl_inset [expr {[info exists ::env(OT_RL_INSET)] ? $::env(OT_RL_INSET) : 25.0}]
set rl_spread [expr {[info exists ::env(OT_RL_SPREAD)] ? $::env(OT_RL_SPREAD) : 0.35}]
set rl_core [$rl_blk getCoreArea]
set rl_cx0 [expr {double([$rl_core xMin]) / $rl_dbu}]; set rl_cx1 [expr {double([$rl_core xMax]) / $rl_dbu}]
set rl_cy0 [expr {double([$rl_core yMin]) / $rl_dbu}]; set rl_cy1 [expr {double([$rl_core yMax]) / $rl_dbu}]
set rl_list {}
# ---- port bit -> pin centre
set rl_pin [dict create]
set rl_base [dict create]
foreach bt [$rl_blk getBTerms] {
  set n [$bt getName]
  set x ""; set y ""
  foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set x [expr {([$bx xMin] + [$bx xMax]) / 2.0 / $rl_dbu}]; set y [expr {([$bx yMin] + [$bx yMax]) / 2.0 / $rl_dbu}]; break }; break }
  if {$x eq ""} continue
  dict set rl_pin $n [list $x $y]
  set b [regsub {\[[0-9]+\]$} $n ""]
  dict lappend rl_base $b [list $x $y]
}
proc rl_centroid {bases} {
  global rl_base
  set sx 0.0; set sy 0.0; set k 0
  foreach b $bases {
    if {![dict exists $rl_base $b]} continue
    foreach p [dict get $rl_base $b] { set sx [expr {$sx + [lindex $p 0]}]; set sy [expr {$sy + [lindex $p 1]}]; incr k }
  }
  if {$k == 0} { return "" }
  return [list [expr {$sx / $k}] [expr {$sy / $k}]]
}
# the ring face = the face of the lane ports
set rl_rc [rl_centroid {cw_in_l0 cw_in_l1 cw_in_l2 cw_in_l3 cw_in_l4 cw_in_l5 cw_in_l6 cw_in_l7}]
if {$rl_rc eq ""} { error "OT_RLAT: no ring lane ports (netlist / pin plan changed?)" }
set rl_mx [expr {($rl_cx0 + $rl_cx1) / 2.0}]; set rl_my [expr {($rl_cy0 + $rl_cy1) / 2.0}]
set rl_ring_e [expr {[lindex $rl_rc 0] > $rl_mx}]
proc rl_inside {p} {
  global rl_ring_e rl_inset
  set x [lindex $p 0]
  return [list [expr {$rl_ring_e ? $x - $rl_inset : $x + $rl_inset}] [lindex $p 1]]
}
set rl_anchor [dict create]
for {set b 0} {$b < 8} {incr b} {
  set c [rl_centroid [list cw_in_l$b cw_out_l$b ccw_in_l$b ccw_out_l$b]]
  if {$c eq ""} { error "OT_RLAT: lane band $b has no ring ports" }
  dict set rl_anchor band$b [rl_inside $c]
}
set c [rl_centroid {cw_in_h cw_out_h ccw_in_h ccw_out_h ring_tx_enable ring_tx_source}]
if {$c eq ""} { error "OT_RLAT: no ring header ports" }
dict set rl_anchor hdr [rl_inside $c]
dict set rl_anchor hub [list $rl_mx $rl_my]
# ---- chains: base -> {width anchor-kind depth dir}
# bank-side buses (gen_vms_glue_tiles.py BANK + FLT): port b<k>_<n>, tile chain bk_<n>_s<i> (flat bit = k * width + j)
set rl_bank {xq {276 band out} xq2 {276 band out} xq_done {1 hdr in} xq2_done {1 hdr in} eg {276 band in}
             pq {285 hub out} pr {266 hub in} status {18 hub in} flt {1 hub in}}
set rl_hdrports {mirror_busy ring_fault}
# stage counts of the tile chains (gen_vms_glue_tiles.py DB / DD / DC; g7 DEPTH eg 1)
set rl_db [expr {[info exists ::env(OT_RL_DB)] ? $::env(OT_RL_DB) : 3}]
set rl_dd [expr {[info exists ::env(OT_RL_DD)] ? $::env(OT_RL_DD) : 4}]
set rl_dc [expr {[info exists ::env(OT_RL_DC)] ? $::env(OT_RL_DC) : 3}]
proc rl_fx {x} { global rl_cx0 rl_cx1; return [expr {max($rl_cx0 + 1.0, min($x, $rl_cx1 - 3.0))}] }
proc rl_fy {y} { global rl_cy0 rl_cy1; return [expr {max($rl_cy0 + 1.0, min($y, $rl_cy1 - 1.0))}] }
proc rl_put {inst x y} {
  global rl_dbu rl_list
  if {[$inst getPlacementStatus] eq "FIRM"} { return 0 }
  if {[[$inst getMaster] isBlock]} { error "OT_RLAT: relay is a block: [$inst getName]" }
  $inst setLocation [expr {round([rl_fx $x] * $rl_dbu)}] [expr {round([rl_fy $y] * $rl_dbu)}]
  $inst setPlacementStatus FIRM
  lappend rl_list [$inst getName]
  return 1
}
# bus centroid per port base (for the per-bit anchor offset)
proc rl_target {pinxy anc pcent f} {
  global rl_spread
  set px [lindex $pinxy 0]; set py [lindex $pinxy 1]
  set ox [expr {($px - [lindex $pcent 0]) * $rl_spread}]; set oy [expr {($py - [lindex $pcent 1]) * $rl_spread}]
  set axx [expr {[lindex $anc 0] + $ox}]; set ayy [expr {[lindex $anc 1] + $oy}]
  return [list [expr {$px + $f * ($axx - $px)}] [expr {$py + $f * ($ayy - $py)}]]
}
set rl_n 0; set rl_miss 0
set rl_stats [dict create]
foreach inst [$rl_blk getInsts] {
  set nm [$inst getName]
  set m [[$inst getMaster] getName]
  if {![string match "DFF*" $m]} continue
  set clean [string map {"\\" ""} $nm]
  set port ""; set f -1.0; set kind ""
  set n ""
  if {[regexp {^bk_([a-z0-9_]+?)_s([0-9]+)\[([0-9]+)\]} $clean -> n st bit] && [dict exists $rl_bank $n]} {
  } elseif {[regexp {^bank_status_s([0-9]+)\[([0-9]+)\]} $clean -> st bit]} { set n status
  } elseif {[regexp {^bk_flt_s([0-9]+)\[([0-9]+)\]} $clean -> st bit]} { set n flt
  } else { set n "" }
  if {$n ne ""} {
    lassign [dict get $rl_bank $n] wd kind dir
    set k [expr {$bit / $wd}]; set j [expr {$bit % $wd}]
    set port "b${k}_$n\[$j\]"; if {$wd == 1} { set port "b${k}_$n" }
    if {![dict exists $rl_pin $port]} { set port "b${k}_$n" }
    set d [expr {$n in {xq_done xq2_done} ? $rl_dd : $rl_db}]
    if {$dir eq "in"} {
      if {$st == 0} continue
      if {$n eq "eg" && ![info exists ::env(OT_RL_TEST_G6)]} { error "OT_RLAT: eg tile relay $clean found (g7 eg depth is 1)" }
      set f [expr {double($st) / $d}]
    } else {
      if {$st >= $d - 1} continue
      set f [expr {1.0 - double($st + 1) / $d}]
    }
    if {$kind eq "band"} { set kind band$k }
  } elseif {[regexp {^u_core\.u_c?cw\.a_eg\[([0-9]+)\]} $clean -> bit]} {
    set k [expr {$bit / 276}]; set j [expr {$bit % 276}]
    set port "b${k}_eg\[$j\]"; set kind band$k; set f [expr {1.0 / 3.0}]
  } elseif {[regexp {^u_core\.u_c?cw\.band\[([0-9])\]\.eg_m\[([0-9]+)\]} $clean -> k j]} {
    set port "b${k}_eg\[$j\]"; set kind band$k; set f [expr {2.0 / 3.0}]
  } elseif {[regexp {^([a-z_]+)_g_s([0-9]+)(\[([0-9]+)\])?$} [regsub {\$.*$} $clean ""] -> n st - bit]} {
    set port [expr {$bit eq "" ? $n : "$n\[$bit\]"}]
    if {![dict exists $rl_pin $port]} { set port $n }
    set kind [expr {$n in $rl_hdrports ? "hdr" : "hub"}]
    set d $rl_dc
    # client inputs: <n>_g_s0 is the pin flop; outputs: <n>_g_s0.. relays, the port flop is renamed to the port
    set bt [$rl_blk findBTerm $port]
    if {$bt eq "NULL"} { incr rl_miss; continue }
    if {[$bt getIoType] eq "OUTPUT"} {
      if {$st >= $d - 1} continue
      set f [expr {1.0 - double($st + 1) / $d}]
    } else {
      if {$st == 0} continue
      set f [expr {double($st) / $d}]
    }
  } else {
    continue
  }
  if {![dict exists $rl_pin $port]} { incr rl_miss; continue }
  set base [regsub {\[[0-9]+\]$} $port ""]
  set pc [rl_centroid [list $base]]
  set t [rl_target [dict get $rl_pin $port] [dict get $rl_anchor $kind] $pc $f]
  if {[rl_put $inst [lindex $t 0] [lindex $t 1]]} {
    incr rl_n
    dict incr rl_stats "$kind:[format %.2f $f]"
  }
}
# ---- core reach relays between the hub island and the ring-stop header band (hfd_vms_glue_core_lt: pi / ri / cco / rce,
#      one plain edge each, 400-700 um): at the midpoint of their two anchors (cco from lane band 0), bits spread along the
#      face direction (0.30 um per bit) so the bus keeps its width
proc rl_mid {a b} { return [list [expr {([lindex $a 0] + [lindex $b 0]) / 2.0}] [expr {([lindex $a 1] + [lindex $b 1]) / 2.0}]] }
set rl_core_rel [dict create pi0_r {hub hdr 290} pi1_r {hub hdr 290} ri0_r {hub hdr 266} ri1_r {hub hdr 266} \
                             cco0_r {band0 hub 264} cco1_r {band0 hub 264} rce0_r {hdr hub 288} rce1_r {hdr hub 288}]
set rl_nc 0
foreach inst [$rl_blk getInsts] {
  if {![string match "DFF*" [[$inst getMaster] getName]]} continue
  set clean [string map {"\\" ""} [$inst getName]]
  if {![regexp {^u_core\.([a-z0-9]+_r)\[([0-9]+)\]} $clean -> r bit] || ![dict exists $rl_core_rel $r]} continue
  lassign [dict get $rl_core_rel $r] ka kb wd
  set p [rl_mid [dict get $rl_anchor $ka] [dict get $rl_anchor $kb]]
  set off [expr {($bit - $wd / 2.0) * 0.30}]
  if {[rl_put $inst [lindex $p 0] [expr {[lindex $p 1] + $off}]]} { incr rl_n; incr rl_nc }
}
dict set rl_stats core_relays $rl_nc
puts "OT_RLAT anchors: [dict get $rl_anchor hub] hub, [dict get $rl_anchor hdr] hdr, ring face [expr {$rl_ring_e ? {E} : {W}}]"
dict for {k v} $rl_stats { puts "OT_RLAT $k $v" }
if {$rl_miss > 0} { error "OT_RLAT: $rl_miss relay bits without their port pin (netlist / naming changed?)" }
if {$rl_n < 1000} { error "OT_RLAT: only $rl_n relays found (netlist / naming changed?)" }
set rl_pack [expr {[info exists ::env(OT_RL_PACK)] ? $::env(OT_RL_PACK) : "/src/physical/common_flow/anchor_row_packing.tcl"}]
if {![file exists $rl_pack] && [info script] ne ""} { set rl_pack [file join [file dirname [info script]] .. .. physical common_flow anchor_row_packing.tcl] }
source $rl_pack
ot_anchor_pack::repair $rl_blk $rl_list
set fh [open $::env(RESULTS_DIR)/ot_relay_lattice.txt w]
foreach n $rl_list { puts $fh $n }
close $fh
puts "OT_RLAT fixed $rl_n relays on the lattice (FIRM until detailed placement)"
