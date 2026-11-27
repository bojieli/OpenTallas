# KV-HUB-HOLD 11-23 (FABLE-RC-KV 21:28 ruling): opt-in OT_TAP_LANDING_SEAM=1 (plan clock.tap_landing_seam true), sourced
# after macro follow and the data affinity passes, with an optional dependency before reset affinity and cloning.
# Cause it fixes: kv3_hub_Eo D28 (kit 1122231125) cland_i_astk_ES ep_zo ring read side sat on clk_t2 / clk_t3 / clk_t47 and its
# boundary capture u_bin_* on clk_t3, the grid tap that also carried the hard core pin u_astk_ES/ck (114 + ETM 269 ps).  CTS
# balanced clk_t3 to that pin (tree 623 ps), so the 3-cell ring -> bin seam read launch 215 / capture 572 = -323 ps hold at
# post-hook CTS, closed only by ~200 GRT hold buffers per pass.  Rule: for every landing <k> whose local-clock ring sinks
# (u_cland_<k>/..., soft cells only; the forwarded write side is on its own fclk net and is never touched) and boundary
# capture sinks (u_bin_<k>/...) are both on tap nets, all of them go to ONE tap: the tap nearest their centroid that carries
# NO hard clock pin, preferring one with room under the cap within the radius.  A landing already on one hard-free tap is
# left alone.  Clock pins only; no data, reset or cell change.  Moved pins are pinned against later cap passes.
namespace eval ::ot_landing_seam {
 proc run {} {
  global ct_taps ct_pinned ct_group_owned
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set cap [expr {[info exists ::env(OT_TAP_MAX_SINKS)] ? $::env(OT_TAP_MAX_SINKS) : 3000}]
  set rad_um [expr {[info exists ::env(OT_TAP_REASSIGN_UM)] && $::env(OT_TAP_REASSIGN_UM) ne "" ? $::env(OT_TAP_REASSIGN_UM) : 200.0}]
  if {[info exists ::env(OT_TAP_SEAM_RADIUS_UM)] && $::env(OT_TAP_SEAM_RADIUS_UM) ne ""} { set rad_um $::env(OT_TAP_SEAM_RADIUS_UM) }
  set rad [expr {$rad_um*$dbu}]
  set tapxy {}; set tapnet {}; set load {}; set hard {}; set grp {}; set side {}
  foreach tp $ct_taps {
   set net [lindex $tp 1]; set nm [$net getName]
   dict set tapxy $nm [list [lindex $tp 2] [lindex $tp 3]]; dict set tapnet $nm $net; dict set load $nm 0
   foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    dict incr load $nm
    set inst [$it getInst]
    if {![catch {[$inst getMaster] isBlock} hb] && $hb eq "1"} { dict set hard $nm 1; continue }
    if {[[$it getMTerm] getName] ni {CLK CLKN CK CKN}} continue
    set iname [$inst getName]
    if {[regexp {(?:^|[/.])u_cland_([A-Za-z0-9_]+)/} $iname -> k]} { dict lappend grp $k $it; dict set side $k,c 1 } \
    elseif {[regexp {(?:^|[/.])u_bin_([A-Za-z0-9_]+)/} $iname -> k]} { dict lappend grp $k $it; dict set side $k,b 1 }
   }
  }
  set nland 0; set nmoved 0; set nsinks 0; set nwarn 0; set nok 0
  dict for {k its} $grp {
   if {![dict exists $side $k,c] || ![dict exists $side $k,b]} continue
   incr nland
   set sx 0.0; set sy 0.0; set own {}
   foreach it $its {
    lassign [[$it getInst] getLocation] x y
    set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]
    dict incr own [[$it getNet] getName]
   }
   set n [llength $its]
   set cx [expr {$sx / $n}]; set cy [expr {$sy / $n}]
   if {[dict size $own] == 1 && ![dict exists $hard [lindex [dict keys $own] 0]]} { incr nok; continue }
   # best = nearest hard-free tap with room within the radius; else nearest hard-free within the radius; else nearest hard-free
   set best ""; set bd 0; set bclass 9
   dict for {nm xy} $tapxy {
    if {[dict exists $hard $nm] || [lindex $xy 0] eq ""} continue
    set d [expr {abs($cx - [lindex $xy 0]) + abs($cy - [lindex $xy 1])}]
    set mine [expr {[dict exists $own $nm] ? [dict get $own $nm] : 0}]
    set room [expr {[dict get $load $nm] - $mine + $n <= $cap}]
    set cl [expr {$d <= $rad ? ($room ? 0 : 1) : 2}]
    if {$best eq "" || $cl < $bclass || ($cl == $bclass && $d < $bd)} { set best $nm; set bd $d; set bclass $cl }
   }
   if {$best eq ""} { puts "OT_TAP_LANDING_SEAM WARN $k: no hard-free tap"; incr nwarn; continue }
   if {$bclass > 0} { incr nwarn }
   set bnet [dict get $tapnet $best]; set mv 0
   foreach it $its {
    set old [[$it getNet] getName]
    if {$old ne $best} {
     $it disconnect; $it connect $bnet; incr mv
     dict incr load $old -1; dict incr load $best
    }
    dict set ct_pinned $it 1
    dict set ct_group_owned $it 1
   }
   incr nmoved $mv; incr nsinks $n
   set from {}; dict for {t c} $own { lappend from "$t:$c[expr {[dict exists $hard $t] ? {(hard)} : {}}]" }
   puts "OT_TAP_LANDING_SEAM $k sinks=$n from {[join $from { }]} -> $best dist_um=[format %.0f [expr {$bd/$dbu}]] class=[lindex {room full far} $bclass] moved=$mv"
  }
  puts "OT_TAP_LANDING_SEAM landings $nland, already one hard-free tap $nok, sinks moved $nmoved, warn $nwarn (cap $cap, radius ${rad_um} um)"
  return $nmoved
 }
}
if {[info exists ::env(OT_TAP_LANDING_SEAM)] && $::env(OT_TAP_LANDING_SEAM) eq "1" && [info exists ct_taps] && [llength $ct_taps] >= 2} {
 ::ot_landing_seam::run
}
