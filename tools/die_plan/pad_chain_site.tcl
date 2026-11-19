# PAD-CHAIN-SITE (FABLE-FIX-QC 11-18): site the landing-pad register chains `ot_dp_dly #(.W(1), .D(pad)) u_pd<pad>_<bus>_<bit>` of a
# kit from the kit's OWN netlist and FIRM geometry, in PRE_GLOBAL_PLACE (end of face_flops.tcl, after istations / relay_sites,
# core_input_anchor and tail_copy_anchor).
# Class (QC sle_ctl x7, N4 kits, TT at CTS -86 / -98 / -109): the pad depth is an as-built number (R8 strap pad, lane as-built
# cycles), so it differs between the types of one family and moves with every plan event, while plan relay_sites rows are keyed by
# it (u_pd11_x_fw_i_236.r[3]).  One table shared by the seven sle_ctl types matched 8,492..11,708 of 21,808 keys; the other pad
# chains (u_pd14_x_st_a_i, u_pd7_b_tw_data_i, u_pd6_x_fw_p1_i on cl372cea1c) were left to GPL.  And the rows that did match were
# aimed at the consumer core's RECTANGLE, not at its pins (type_relay_sites.py point()): u_pd11_x_fw_i_236.q at (750,145), the pin
# u_u_ctl/chd_q[236] on the core's top edge at (550,596): 651 um in the last hop, 102 ends to -97.9 ps.
# Rule here, per chain (every stage feeds only the next, through unary BUF/INV cells):
#   launch A  = what drives the first stage: a hard-macro output pin, a FIRM flop, or a block port;
#   captures  = what the last stage reaches through combinational cells: hard-macro input pins, FIRM flops, block ports
#               (flops GPL still owns are not anchors; a chain with no located capture or launch is left alone);
#   tail B    = L1 centre of the captures; inside a hard core (+ halo) it moves to the core edge point or corner with the smallest
#               largest ROUTED distance (around the cores) to the captures; all captures on one core within 60 um of each other:
#               1.5 um outside the nearest pin;
#   stages    = equal hops d = (route(A,B) + rb) / (n + 1) along a Manhattan route around the hard cores, rb = the largest
#               capture distance from B; stage j at path length min(route, j * d).
# No netlist change.  Sited cells are FIRM through GPL and listed in ot_face_flops.txt (released to PLACED for DPL).
# Opt-in at gen time (gen_phys.pad_chain_site_place, gen env OT_PAD_CHAIN_SITE; unset = no hook, kit unchanged):
#   unsited  only chains no earlier hook made FIRM (a matching plan relay_sites row always wins);
#   auto     unsited + STALE plan-sited chains: a chain whose plan-sited last stage is more than the reach (OT_PAD_CHAIN_HOP_UM,
#            380 um) from a capture, or that is only partly sited, is sited again from the netlist;
#   all      every chain (derived sites replace plan rows);   off  nothing.
# Tail-split copies and trunks (tail_copies.tsv, tail_copy_anchor.tcl) are never touched.
# OT_PAD_CHAIN_SITE_DRY=1: no cell moves; the targets go to $OT_PAD_CHAIN_SITE_OUT (tsv) for a read on any placed DB (placed cells
# count as anchors); =firm: the same read with FIRM anchors only (3_3_place_gp.odb still holds the PRE_GLOBAL_PLACE FIRM set).
proc pcs_chain_of {nm} {
  set nm [string map {\\ {}} $nm]
  if {![regexp {(?:^|[./])(u_pd[0-9]+_[A-Za-z0-9_]+_[0-9]+)[./](?:r\[[0-9]+\]|q)(?:\$|$)} $nm -> c]} { return "" }
  return $c
}
proc pcs_isseq {i} { return [regexp {^(DFF|SDF|DLL|DHL|ICG|ASYNC)} [[$i getMaster] getName]] }
proc pcs_ctr {i} { set b [$i getBBox]; return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]] }
# a hard-core pin as a route end: the point 1.5 um outside the core face nearest the pin (a pin box lies inside the core box, so a
# route that starts at the pin itself counts as entering the core)
proc pcs_pin_out {it} { return [tcs_out_pos $it 1.5 [[ord::get_db_block] getDbUnitsPerMicron]] }
proc pcs_bterm_xy {bt} { set b [$bt getBBox]; return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]] }
set ::pcs_anchor_status {FIRM LOCKED COVER}
# launch point of net n (through up to 6 unary repeaters / flops GPL still owns): {x y kind} or {}
proc pcs_launch {n} {
  for {set h 0} {$h < 7} {incr h} {
    if {$n eq "" || $n eq "NULL"} { return {} }
    foreach bt [$n getBTerms] { if {[$bt getIoType] ne "OUTPUT"} { return [concat [pcs_bterm_xy $bt] port] } }
    set drv ""
    foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set drv $it } }
    if {$drv eq ""} { return {} }
    set di [$drv getInst]
    if {[[$di getMaster] isBlock]} { return [concat [pcs_pin_out $drv] macro] }
    if {[pcs_isseq $di]} {
      if {[$di getPlacementStatus] in $::pcs_anchor_status} { return [concat [pcs_ctr $di] flop] }
      # a flop GPL still owns (the unsited last stage of a packed lane pad): look through it to what feeds it
      if {![tcs_isff $di]} { return {} }
      set n [tcs_dnet $di]
      continue
    }
    if {![tcs_isrep $di]} { return {} }
    set ins {}
    foreach it [$di getITerms] { if {[[$it getMTerm] getIoType] eq "INPUT"} { set x [$it getNet]; if {$x ne "" && $x ne "NULL"} { lappend ins $x } } }
    if {[llength $ins] != 1} { return {} }
    set n [lindex $ins 0]
  }
  return {}
}
# captures of flop f through combinational cells: {{{x y} ..} macros soft} (macros = list of hard cores holding a capture pin,
# soft = sequential captures GPL still owns)
proc pcs_captures {f {maxcells 600}} {
  set pts {}; set macs {}; set soft 0; set seen [dict create]; set front [list [tcs_out $f]]; set ncell 0
  while {[llength $front] && $ncell < $maxcells} {
    set nf {}
    foreach n $front {
      if {$n eq "" || $n eq "NULL" || [dict exists $seen $n]} continue
      dict set seen $n 1
      foreach bt [$n getBTerms] { if {[$bt getIoType] ne "INPUT"} { lappend pts [pcs_bterm_xy $bt] } }
      foreach it [$n getITerms] {
        if {[[$it getMTerm] getIoType] ne "INPUT"} continue
        set c [$it getInst]; set m [$c getMaster]
        if {[$m isBlock]} { lappend pts [pcs_pin_out $it]; if {[lsearch -exact $macs $c] < 0} { lappend macs $c }; continue }
        if {[pcs_isseq $c]} {
          if {[[$it getMTerm] getName] in {CLK CLKN CK}} continue
          if {[$c getPlacementStatus] in $::pcs_anchor_status} { lappend pts [pcs_ctr $c] } else { incr soft }
          continue
        }
        incr ncell
        foreach ot [$c getITerms] { if {[[$ot getMTerm] getIoType] eq "OUTPUT"} { set x [$ot getNet]; if {$x ne "" && $x ne "NULL"} { lappend nf $x } } }
      }
    }
    set front $nf
  }
  return [list $pts $macs $soft]
}
# the extreme points of pts in u = x + y and v = x - y (at most 4): enough to bound the largest L1 / routed distance cheaply
proc pcs_extremes {pts} {
  set a ""; set b ""; set c ""; set d ""
  foreach p $pts {
    lassign $p x y; set u [expr {$x + $y}]; set v [expr {$x - $y}]
    if {$a eq "" || $u < [lindex $a 0]} { set a [list $u $p] }; if {$b eq "" || $u > [lindex $b 0]} { set b [list $u $p] }
    if {$c eq "" || $v < [lindex $c 0]} { set c [list $v $p] }; if {$d eq "" || $v > [lindex $d 0]} { set d [list $v $p] }
  }
  set out {}
  foreach e [list $a $b $c $d] { set p [lindex $e 1]; if {[lsearch -exact $out $p] < 0} { lappend out $p } }
  return $out
}
# tail point for captures pts: {x y}.  boxes = hard cores grown by the halo, raw = hard cores, step = push-out step (dbu).
# Candidates: the L1 centre (when outside every core), the middle of the routed path between the two captures that are farthest
# apart by route, and, when the centre is inside a core, that core's edge projections and corners.  The candidate with the
# smallest largest routed distance to the capture extremes wins.
proc pcs_tail {pts boxes raw halo step} {
  set ext [pcs_extremes $pts]
  lassign [tcs_l1_centre $pts] cx cy
  set cands {}
  set hit [tcs_inside $cx $cy $boxes]
  if {$hit eq ""} {
    lappend cands [list $cx $cy]
  } else {
    lassign $hit x0 y0 x1 y1
    foreach x [list [expr {$x0 - $step}] $cx [expr {$x1 + $step}]] { foreach y [list [expr {$y0 - $step}] $cy [expr {$y1 + $step}]] {
      if {$x == $cx && $y == $cy} continue
      if {[tcs_inside $x $y $boxes] eq ""} { lappend cands [list $x $y] }
    } }
  }
  set far ""
  for {set i 0} {$i < [llength $ext]} {incr i} { for {set j [expr {$i + 1}]} {$j < [llength $ext]} {incr j} {
    set r [tcs_route [lindex $ext $i] [lindex $ext $j] $raw $halo]
    if {$far eq "" || [lindex $r 0] > [lindex $far 0]} { set far $r }
  } }
  if {$far ne ""} {
    lassign [tcs_frac $far 0.5] mx my
    lassign [tcs_push_out $mx $my $boxes $step] mx my clear
    if {$clear} { lappend cands [list $mx $my] }
  }
  set best ""
  foreach c $cands {
    set worst 0
    foreach p $ext { set l [lindex [tcs_route $c $p $raw $halo] 0]; if {$l > $worst} { set worst $l } }
    if {$best eq "" || $worst < [lindex $best 0]} { set best [list $worst {*}$c] }
  }
  if {$best eq ""} { lassign [tcs_push_out $cx $cy $boxes $step] x y _; return [list $x $y] }
  return [lrange $best 1 2]
}
# stage targets: n points along route {len hits pts..} at path length min(len, j * (len + rb) / (n + 1)), j = 1..n
proc pcs_stage_points {route n rb} {
  set len [lindex $route 0]; set out {}
  set d [expr {double($len + $rb) / ($n + 1)}]
  for {set j 1} {$j <= $n} {incr j} {
    set f [expr {$len > 0 ? min(1.0, $j * $d / $len) : 1.0}]
    lappend out [tcs_frac $route $f]
  }
  return $out
}
proc pcs_run {} {
  set mode [expr {[info exists ::env(OT_PAD_CHAIN_SITE)] ? $::env(OT_PAD_CHAIN_SITE) : "unsited"}]
  if {$mode eq "off" || $mode eq "0"} { puts "OT_PAD_CHAIN_SITE off"; return }
  if {$mode ni {unsited auto all}} { error "pad_chain_site: OT_PAD_CHAIN_SITE must be unsited, auto, all or off (got $mode)" }
  set dry [expr {[info exists ::env(OT_PAD_CHAIN_SITE_DRY)] && $::env(OT_PAD_CHAIN_SITE_DRY) in {1 firm}}]
  # anchors: cells an earlier PRE_GLOBAL_PLACE hook fixed; a dry read on a placed DB (everything PLACED) takes placed cells too
  set ::pcs_anchor_status [expr {($dry && $::env(OT_PAD_CHAIN_SITE_DRY) eq "1") ? {FIRM LOCKED COVER PLACED} : {FIRM LOCKED COVER}}]
  set blk [ord::get_db_block]
  set dbu [$blk getDbUnitsPerMicron]
  set hop_um [expr {[info exists ::env(OT_PAD_CHAIN_HOP_UM)] ? $::env(OT_PAD_CHAIN_HOP_UM) : 380.0}]
  set halo [expr {round(9.0 * $dbu)}]
  set cb [$blk getCoreArea]; set core [list [$cb xMin] [$cb yMin] [$cb xMax] [$cb yMax]]
  set row [lindex [$blk getRows] 0]
  lassign [$row getOrigin] ox oy
  set sw [[$row getSite] getWidth]; set sh [[$row getSite] getHeight]
  set boxes {}; set raw {}
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend raw [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]; lappend boxes [list [expr {[$b xMin] - $halo}] [expr {[$b yMin] - $halo}] [expr {[$b xMax] + $halo}] [expr {[$b yMax] + $halo}]] }
  }
  set copies [dict create]
  if {[file exists /work/tail_copies.tsv]} { set copies [tcs_read_tsv /work/tail_copies.tsv] }
  set cff [dict create]
  foreach i [$blk getInsts] {
    if {![tcs_isff $i]} continue
    set nm [$i getName]
    set c [pcs_chain_of $nm]
    if {$c eq "" || [dict exists $copies $c] || [tcs_is_trunk $nm]} continue
    dict lappend cff $c $i
  }
  set nchain 0; set ncell 0; set stale 0; set broken 0; set nolaunch 0; set nocap 0; set kept 0; set maxhop 0.0; set over 0; set inside 0; set softonly 0
  set bybus [dict create]
  set out ""; set tsv ""
  if {$dry} {
    if {[info exists ::env(OT_PAD_CHAIN_SITE_OUT)]} { set tsv [open $::env(OT_PAD_CHAIN_SITE_OUT) w] }
  } else { set out [open $::env(RESULTS_DIR)/ot_face_flops.txt a] }
  set use_ff [expr {!$dry && [llength [info commands ff_put_near]] > 0}]
  dict for {c ffs} $cff {
    set k [llength $ffs]
    set firm 0
    foreach f $ffs { if {[$f getPlacementStatus] in {FIRM LOCKED COVER}} { incr firm } }
    if {$firm && $mode eq "unsited"} { incr kept; continue }
    # chain order by connectivity
    set prev [dict create]; set first ""
    foreach f $ffs {
      set d [tcs_ffdriver [tcs_dnet $f]]
      set p [expr {[llength $d] ? [lindex $d 0] : ""}]
      if {$p ne "" && [lsearch -exact $ffs $p] >= 0} { dict set prev $p $f } else { set first $f }
    }
    if {$first eq "" || [dict size $prev] != $k - 1} { incr broken; continue }
    set chain [list $first]
    while {[dict exists $prev [lindex $chain end]]} { lappend chain [dict get $prev [lindex $chain end]] }
    if {[llength $chain] != $k} { incr broken; continue }
    set a [pcs_launch [tcs_dnet $first]]
    if {![llength $a]} { incr nolaunch; continue }
    lassign [pcs_captures [lindex $chain end]] pts macs soft
    if {![llength $pts]} { incr nocap; if {$soft} { incr softonly }; continue }
    set ext [pcs_extremes $pts]
    if {$firm && $mode eq "auto"} {
      # plan-sited chain: kept unless only partly sited or its last stage is out of reach of a capture (a stale row)
      set far 0; set t [pcs_ctr [lindex $chain end]]
      foreach p $ext { set dd [tcs_md $t $p]; if {$dd > $far} { set far $dd } }
      if {$firm == $k && $far <= $hop_um * $dbu} { incr kept; continue }
      incr stale
    }
    set b [pcs_tail $pts $boxes $raw $halo $sw]
    if {[llength $macs] == 1} {
      set spread 0; foreach p $ext { foreach q $ext { set dd [tcs_md $p $q]; if {$dd > $spread} { set spread $dd } } }
      if {$spread <= 60 * $dbu} {
        # one core, one pin cluster: the last stage sits 1.5 um outside the nearest pin
        set pin ""; set best 1e30
        foreach it [tcs_sinks_macro [lindex $chain end] [lindex $macs 0]] { set dd [tcs_md [tcs_pin_xy $it] $b]; if {$dd < $best} { set best $dd; set pin $it } }
        if {$pin ne ""} { set b [tcs_out_pos $pin 1.5 $dbu] }
      }
    }
    lassign [tcs_push_out [lindex $b 0] [lindex $b 1] $boxes $sw] bx by clear
    if {!$clear} { incr inside }
    set b [list $bx $by]
    set rb 0; foreach p $ext { set l [lindex [tcs_route $b $p $raw $halo] 0]; if {$l > $rb} { set rb $l } }
    set route [tcs_route [lrange $a 0 1] $b $raw $halo]
    set tg [pcs_stage_points $route $k $rb]
    set q [lrange $a 0 1]; set worst 0.0
    for {set s_ 0} {$s_ < $k} {incr s_} {
      set f [lindex $chain $s_]
      lassign [lindex $tg $s_] x y
      lassign [tcs_push_out $x $y $boxes $sw] x y clear
      if {!$clear} { incr inside }
      set p [tcs_snap $x $y $core $ox $oy $sw $sh]
      set h [expr {[tcs_md $q $p] / double($dbu)}]; if {$h > $worst} { set worst $h }
      set q $p
      if {$dry} {
        if {$tsv ne ""} { puts $tsv "[string map {\\ {}} [$f getName]]\t[expr {[lindex $p 0] / double($dbu)}]\t[expr {[lindex $p 1] / double($dbu)}]\t[lindex $a 2]\t[llength $pts]\t$soft\t[join [lmap e $ext {format %.0f,%.0f [expr {[lindex $e 0] / double($dbu)}] [expr {[lindex $e 1] / double($dbu)}]}] { }]" }
        continue
      }
      lassign [tcs_follow $f] reps _
      if {$use_ff} {
        set got [ff_put_near $f [lindex $p 0] [lindex $p 1]]
        if {$got eq ""} { tcs_unfix $f; $f setLocation {*}$p; $f setPlacementStatus FIRM } else { set p $got }
      } else { tcs_unfix $f; $f setLocation {*}$p; $f setPlacementStatus FIRM }
      puts $out [$f getName]; incr ncell
      foreach cell $reps { tcs_unfix $cell; $cell setLocation {*}$p; $cell setPlacementStatus FIRM; puts $out [$cell getName]; incr ncell }
    }
    set h [expr {$rb / double($dbu)}]; if {$h > $worst} { set worst $h }
    if {$worst > $maxhop} { set maxhop $worst }; if {$worst > $hop_um} { incr over }
    regexp {^u_pd[0-9]+_(.*)_[0-9]+$} $c -> bus
    if {![dict exists $bybus $bus] || $worst > [dict get $bybus $bus]} { dict set bybus $bus $worst }
    incr nchain
  }
  if {$out ne ""} { close $out }
  if {$tsv ne ""} { close $tsv }
  set bb {}; dict for {bus w} $bybus { lappend bb [format "%s %.0f" $bus $w] }
  puts [format "OT_PAD_CHAIN_SITE mode %s%s chains %d of %d sited (%d cells, %d stale plan-sited re-sited) kept_plan_sited %d broken %d no_launch %d no_capture %d (soft only %d) max_hop %.1f um over_%g %d in_halo %d | worst hop per bus: %s" \
          $mode [expr {$dry ? " DRY" : ""}] $nchain [dict size $cff] $ncell $stale $kept $broken $nolaunch $nocap $softonly $maxhop $hop_um $over $inside [join $bb ", "]]
}
# hard-macro input pins of core mac reached from flop f through unary repeaters only
proc tcs_sinks_macro {f mac} {
  set out {}; set front [list [tcs_out $f]]; set seen [dict create]
  for {set h 0} {$h < 8 && [llength $front]} {incr h} {
    set nf {}
    foreach n $front {
      if {$n eq "" || $n eq "NULL" || [dict exists $seen $n]} continue
      dict set seen $n 1
      foreach it [tcs_sinks $n] {
        set c [$it getInst]
        if {$c eq $mac} { lappend out $it } elseif {[tcs_isrep $c]} { lappend nf [tcs_out $c] }
      }
    }
    set front $nf
  }
  return $out
}
# ORIGIN-SITE (FABLE-FIX-QC 11-19, same hook and env): the landing start origin `ot_dp_landing_origin(_s) u_cland_origin` of an origin
# partition is a synchroniser (s0 s1 s2 [sf] + pd taps) whose `start` feeds every reader / writer / forwarded start flop of the
# partition AND the region relay tx flop u_cland_rstart_tx at its pin.  Its flops are soft: GPL puts them with the majority of the
# loads and the one far load pays the whole distance in one hop (QC sle_st_b_v2__cl14c98df5__pvcd986c42: origin at (99,470), 13 loads
# within 300 um, u_cland_rstart_tx at (313,1331): 1,075 um, 1 end at -106.2 ps TT at GRT; st_b x5 kits -4..-106 on that end).
# p_start into s0 is asynchronous, so the origin may sit anywhere: when the FIRM captures of `start` are spread over more than the
# reach, all origin flops go to the point with the smallest largest routed distance to them (pcs_tail), FIRM through GPL.  0 cycles,
# no netlist change.  An origin an earlier hook made FIRM is kept (mode all re-sites it).
proc pcs_origin_of {nm} {
  set nm [string map {\\ {}} $nm]
  if {![regexp {^(.*(?:^|[./])u_cland_origin)[./](s0|s1|s2|sf|pd(?:\[[0-9]+\])?)(?:\$|$)} $nm -> o st]} { return "" }
  return [list $o $st]
}
proc pcs_origin_run {} {
  set mode [expr {[info exists ::env(OT_PAD_CHAIN_SITE)] ? $::env(OT_PAD_CHAIN_SITE) : "unsited"}]
  if {$mode ni {unsited auto all}} { return }
  set dry [expr {[info exists ::env(OT_PAD_CHAIN_SITE_DRY)] && $::env(OT_PAD_CHAIN_SITE_DRY) in {1 firm}}]
  set blk [ord::get_db_block]
  set dbu [$blk getDbUnitsPerMicron]
  set hop_um [expr {[info exists ::env(OT_PAD_CHAIN_HOP_UM)] ? $::env(OT_PAD_CHAIN_HOP_UM) : 380.0}]
  set halo [expr {round(9.0 * $dbu)}]
  set row [lindex [$blk getRows] 0]; set sw [[$row getSite] getWidth]; set sh [[$row getSite] getHeight]
  lassign [$row getOrigin] ox oy
  set cb [$blk getCoreArea]; set core [list [$cb xMin] [$cb yMin] [$cb xMax] [$cb yMax]]
  set boxes {}; set raw {}; set org [dict create]
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend raw [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]; lappend boxes [list [expr {[$b xMin] - $halo}] [expr {[$b yMin] - $halo}] [expr {[$b xMax] + $halo}] [expr {[$b yMax] + $halo}]]; continue }
    if {![pcs_isseq $i]} continue
    set o [pcs_origin_of [$i getName]]
    if {$o ne ""} { dict lappend org [lindex $o 0] [list $i [lindex $o 1]] }
  }
  set nsite 0; set nkeep 0; set nnear 0; set ncell 0; set rep {}
  set out ""; if {!$dry && [dict size $org]} { set out [open $::env(RESULTS_DIR)/ot_face_flops.txt a] }
  dict for {o recs} $org {
    set firm 0; set pts {}; set own {}
    foreach r $recs { lappend own [lindex $r 0]; if {!$dry && [[lindex $r 0] getPlacementStatus] in {FIRM LOCKED COVER}} { incr firm } }
    if {$firm && $mode ne "all"} { incr nkeep; continue }
    foreach r $recs {
      lassign $r f st
      if {$st ni {s0 s1 sf}} { foreach p [lindex [pcs_captures $f] 0] { lappend pts $p } }
    }
    # the origin's own stages are not captures (a dry read on a placed DB sees them placed)
    set keep {}; foreach p $pts { set mine 0; foreach f $own { if {[pcs_ctr $f] eq $p} { set mine 1; break } }; if {!$mine} { lappend keep $p } }
    set pts [lsort -unique $keep]
    if {[llength $pts] < 2} { incr nnear; continue }
    set ext [pcs_extremes $pts]
    set spread 0; foreach p $ext { foreach q $ext { set dd [tcs_md $p $q]; if {$dd > $spread} { set spread $dd } } }
    if {$spread <= $hop_um * $dbu} { incr nnear; continue }
    lassign [pcs_tail $pts $boxes $raw $halo $sw] bx by
    lassign [tcs_push_out $bx $by $boxes $sw] bx by _
    set b [tcs_snap $bx $by $core $ox $oy $sw $sh]
    set worst 0; foreach p $ext { set l [lindex [tcs_route $b $p $raw $halo] 0]; if {$l > $worst} { set worst $l } }
    lappend rep [format "%s at (%.1f,%.1f) %d captures spread %.0f worst hop %.0f um" [string map {\\ {}} $o] [expr {[lindex $b 0] / double($dbu)}] [expr {[lindex $b 1] / double($dbu)}] [llength $pts] [expr {$spread / double($dbu)}] [expr {$worst / double($dbu)}]]
    incr nsite
    if {$dry} continue
    foreach f $own {
      if {[llength [info commands ff_put_near]]} {
        if {[ff_put_near $f [lindex $b 0] [lindex $b 1]] eq ""} { tcs_unfix $f; $f setLocation {*}$b; $f setPlacementStatus FIRM }
      } else { tcs_unfix $f; $f setLocation {*}$b; $f setPlacementStatus FIRM }
      puts $out [$f getName]; incr ncell
    }
  }
  if {$out ne ""} { close $out }
  puts "OT_ORIGIN_SITE mode $mode[expr {$dry ? " DRY" : ""}] origins [dict size $org] sited $nsite ($ncell flops) kept_firm $nkeep captures_within_reach $nnear | [join $rep {; }]"
}
if {[llength [info commands tcs_route]] == 0} { uplevel #0 {source [file join [file dirname [info script]] tail_copy_anchor.tcl]} }
if {![info exists ::pcs_no_run]} { pcs_run; pcs_origin_run }
