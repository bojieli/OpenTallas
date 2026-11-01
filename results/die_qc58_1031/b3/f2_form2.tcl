# DIE-QC-58A NK form (2) (no RTL change, ICG=2 B-hop per-entry gates): after clock_tree_synthesis, every per-entry hop
# ICG (OT_F2_ICG pattern) is moved along the ungated tree so its gated body lands on the ungated register latency:
#   delta  = median(ungated register CLK arr) - median(gated register CLK arr behind this ICG)
#   target = ICG CLK arr + (delay chain behind GCLK, removed) + delta, capped at OT_F2_CAP = max ungated leaf - one stage
# The ICG CLK pin is re-tapped on the ungated buffer net nearest the target (arrival + distance penalty), through a
# branch BUF at the tap. Clocks, SDC, corners, margins and the structural hold gate are unchanged.
#   OT_F2_ICG   full-name pattern of the hop ICGs (default *u_hop_*/u_icg)
#   OT_F2_ECO   1 = apply, 0 = report only
#   OT_F2_STAGE ps of one leaf stage (default 25)   OT_F2_PEN ps/um distance penalty for tap choice (default 0.08)
#   OT_F2_ODB   write the raw post-CTS ODB here before the ECO (offline iteration)
set ::ot_f2_cid 0
set ::ot_f2_nmix 0
proc ot_f2_arr {pin} {
  set p [get_pins $pin]
  foreach prop {arrival_max_rise max_rise_arrival} { if {![catch {get_property $p $prop} v] && $v ne ""} { return $v } }
  return ""
}
proc ot_f2_xy {dbi} {
  set l [$dbi getLocation]
  return [list [ord::dbu_to_microns [lindex $l 0]] [ord::dbu_to_microns [lindex $l 1]]]
}
proc ot_f2_med {l} { set s [lsort -real $l]; set n [llength $s]; if {!$n} { return "" }; return [lindex $s [expr {$n / 2}]] }
proc ot_f2_pct {l p} { set s [lsort -real $l]; set n [llength $s]; if {!$n} { return "" }; return [lindex $s [expr {min($n - 1, int($n * $p))}]] }
# gated sinks behind one ICG: BFS from GCLK through BUF/INV/HB only
proc ot_f2_gated {icgn} {
  set regs {}; set macs {}
  set q [list [get_nets -of_objects [get_pins $icgn/GCLK]]]
  set seen {}
  while {[llength $q]} {
    set n [lindex $q 0]; set q [lrange $q 1 end]
    if {$n eq "" || [catch {set nn [get_full_name $n]}]} continue
    if {[dict exists $seen $nn]} continue; dict set seen $nn 1
    foreach ip [get_pins -quiet -of_objects $n -filter "direction==input"] {
      set c [get_cells -of_objects $ip]
      if {[catch {set ref [get_property $c ref_name]}]} continue
      if {[regexp {^(BUF|INV|CKINV|HB)} $ref]} {
        foreach op [get_pins -of_objects $c -filter "direction==output"] { catch { set on [get_nets -of_objects $op]; if {$on ne ""} { lappend q $on } } }
      } elseif {[regexp {DFF|DHL|DLL|SDF} $ref]} { lappend regs [get_full_name $ip]
      } else { lappend macs [get_full_name $ip] }
    }
  }
  return [list $regs $macs]
}
proc ot_f2_report {tag} {
  catch {estimate_parasitics -placement}
  set pat [expr {[info exists ::env(OT_F2_ICG)] ? $::env(OT_F2_ICG) : "*u_hop_*/u_icg"}]
  set allg {}
  set rows {}
  foreach c [get_cells -quiet -hierarchical *u_icg] {
    set n [get_full_name $c]
    if {![string match $pat $n]} continue
    lassign [ot_f2_gated $n] regs macs
    set ra {}; foreach p $regs { set a [ot_f2_arr $p]; if {$a ne ""} { lappend ra $a }; dict set allg $p 1 }
    set ma {}; foreach p $macs { set a [ot_f2_arr $p]; if {$a ne ""} { lappend ma $a }; dict set allg $p 1 }
    lappend rows [list $n [ot_f2_arr $n/CLK] [ot_f2_arr $n/GCLK] [llength $ra] [ot_f2_pct $ra 0] [ot_f2_med $ra] [ot_f2_pct $ra 0.999] [llength $ma] [ot_f2_pct $ma 0] [ot_f2_pct $ma 0.999]]
  }
  set ua {}
  foreach p [all_registers -clock_pins] { set pn [get_full_name $p]; if {![dict exists $allg $pn]} { set a [ot_f2_arr $pn]; if {$a ne ""} { lappend ua $a } } }
  set ::ot_f2_umed [ot_f2_med $ua]; set ::ot_f2_umax [ot_f2_pct $ua 0.999]
  puts [format "OT_F2 %s ungated regs %d arr p0 %.1f p10 %.1f p50 %.1f p90 %.1f max %.1f" $tag [llength $ua] [ot_f2_pct $ua 0] [ot_f2_pct $ua 0.1] $::ot_f2_umed [ot_f2_pct $ua 0.9] $::ot_f2_umax]
  set ::ot_f2_rows $rows
  foreach r $rows {
    lassign $r n ck gck nr r0 rm r1 nm m0 m1
    puts [format "OT_F2 %s %-44s CLK %7s GCLK %7s regs %5d %7s/%7s/%7s mac %3d %7s..%7s d %s" $tag $n $ck $gck $nr $r0 $rm $r1 $nm $m0 $m1 [expr {$rm ne "" ? [format %.1f [expr {$::ot_f2_umed - $rm}]] : "-"}]]
  }
}
# ungated buffer output nets (tap candidates): BFS from the clock source ports through BUFs only (stops at ICGs)
proc ot_f2_taps {} {
  set block [ord::get_db_block]
  set taps {}; set q {}
  foreach c [all_clocks] {
    if {[catch {set srcs [get_property $c sources]}] || $srcs eq "" || $srcs eq "NULL"} continue
    foreach s $srcs { set bt [$block findBTerm [get_full_name $s]]; if {$bt ne "" && $bt ne "NULL" && [$bt getNet] ne "NULL"} { lappend q [get_nets [[$bt getNet] getName]] } }
  }
  set seen {}
  while {[llength $q]} {
    set n [lindex $q 0]; set q [lrange $q 1 end]
    if {$n eq "" || [catch {set nn [get_full_name $n]}]} continue
    if {[dict exists $seen $nn]} continue; dict set seen $nn 1
    foreach ip [get_pins -quiet -of_objects $n -filter "direction==input"] {
      set c [get_cells -of_objects $ip]
      if {[catch {set ref [get_property $c ref_name]}]} continue
      if {![regexp {^BUF} $ref]} continue
      foreach op [get_pins -of_objects $c -filter "direction==output"] {
        set a [ot_f2_arr [get_full_name $op]]
        catch { set on [get_nets -of_objects $op]; if {$on ne ""} { lappend q $on; if {$a ne ""} { lappend taps [list $a [get_full_name $on] [ot_f2_xy [sta::sta_to_db_inst $c]]] } } }
      }
    }
  }
  return $taps
}
proc ot_f2_eco {} {
  set block [ord::get_db_block]
  set stage [expr {[info exists ::env(OT_F2_STAGE)] ? $::env(OT_F2_STAGE) : 25.0}]
  set pen [expr {[info exists ::env(OT_F2_PEN)] ? $::env(OT_F2_PEN) : 0.08}]
  set bufc [expr {[info exists ::env(OT_F2_BUF)] ? $::env(OT_F2_BUF) : "BUFx8_ASAP7_75t_R"}]
  set cap [expr {$::ot_f2_umax - $stage}]
  set k 0
  foreach r $::ot_f2_rows {
    lassign $r n ck gck nr r0 rm r1
    if {$rm eq "" || $ck eq ""} continue
    set delta [expr {$::ot_f2_umed - $rm}]
    set icgi [sta::sta_to_db_inst [get_cells $n]]
    # delay chain behind GCLK (single-fanout CTS delaybufs): removed when the gate moves later
    set gnet [[$icgi findITerm GCLK] getNet]
    set chain {}; set nn $gnet
    while {1} {
      set loads {}; foreach it [$nn getITerms] { if {[$it isInputSignal]} { lappend loads $it } }
      if {[llength $loads] != 1} break
      set li [[lindex $loads 0] getInst]
      if {![string match "BUF*" [[$li getMaster] getName]] || ![string match "delaybuf_*" [$li getName]]} break
      lappend chain $li; set nn [[$li findITerm Y] getNet]
    }
    set d 0.0
    if {[llength $chain]} { set d [expr {[ot_f2_arr [[lindex $chain end] getName]/Y] - $gck}] }
    set tgt [expr {min($cap, $ck + $d + $delta)}]
    if {abs($tgt - $ck) < 0.5 * $stage && ![llength $chain]} { puts [format "OT_F2 eco %s: d %.1f within half a stage, kept" $n $delta]; continue }
    # tap: arrival + branch buffer (~stage) + wire (pen ps/um) nearest the target CLK arrival
    lassign [ot_f2_xy $icgi] ix iy
    set best ""; set be 1e9
    foreach t [ot_f2_taps] {
      lassign $t a tn txy; lassign $txy tx ty
      if {$tn eq [[[$icgi findITerm CLK] getNet] getName]} continue
      set dist [expr {abs($tx - $ix) + abs($ty - $iy)}]
      set est [expr {$a + $stage * 0.6 + $pen * $dist}]
      set e [expr {abs($est - $tgt) + 0.02 * $dist}]
      if {$e < $be} { set be $e; set best [list $a $tn $txy $dist $est] }
    }
    if {$best eq ""} { puts "OT_F2 eco $n: no tap"; continue }
    lassign $best ta tn txy dist est
    # remove the chain (its loads move onto GCLK)
    if {[llength $chain]} {
      set last [lindex $chain end]; set lnet [[$last findITerm Y] getNet]
      set lpins {}; foreach it [$lnet getITerms] { if {[$it isInputSignal]} { lappend lpins "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
      foreach b $chain { set bn [$b getName]; foreach pn {A Y} { catch { set xn [[[$b findITerm $pn] getNet] getName]; disconnect_pin [get_nets $xn] [get_pins $bn/$pn] } } }
      foreach p $lpins { connect_pin [get_nets [$gnet getName]] [get_pins $p] }
      foreach b $chain { delete_instance [get_cells [$b getName]] }
    }
    set old [[$icgi findITerm CLK] getNet]
    disconnect_pin [get_nets [$old getName]] [get_pins $n/CLK]
    connect_pin [get_nets $tn] [get_pins $n/CLK]
    # branch buffer at the midpoint of tap->ICG drives the re-tap wire
    lassign $txy tx ty
    set xy [list [expr {($tx + $ix) / 2.0}] [expr {($ty + $iy) / 2.0}]]
    catch {estimate_parasitics -placement}
    set bn "ot_f2_b$k"; incr k
    insert_buffer -buffer_cell $bufc -load_pins [get_pins $n/CLK] -location $xy -buffer_name $bn
    foreach i [$block getInsts] { if {[string match "*$bn*" [$i getName]]} { foreach it [$i getITerms] { set nt [$it getNet]; if {$nt ne "NULL" && $nt ne "" && ![$nt isSpecial]} { $nt setSigType CLOCK } } } }
    catch {estimate_parasitics -placement}
    puts [format "OT_F2 eco %s: chain %d (%.1f ps) removed, d %.1f, CLK %.1f -> tgt %.1f, tap %s arr %.1f dist %.0f um est %.1f -> CLK %s GCLK %s" \
      $n [llength $chain] $d $delta $ck $tgt $tn $ta $dist $est [ot_f2_arr $n/CLK] [ot_f2_arr $n/GCLK]]
  }
  puts "OT_F2 eco: $k hop ICGs re-tapped (cap $cap)"
}
proc ot_f2_post_cts {} {
  if {[info exists ::ot_f2_done]} { return }
  set ::ot_f2_done 1
  if {[info exists ::env(OT_F2_ODB)] && $::env(OT_F2_ODB) ne ""} { write_db $::env(OT_F2_ODB) }
  ot_f2_report pre
  if {[info exists ::env(OT_F2_ECO)] && $::env(OT_F2_ECO) eq "1"} {
    if {[info exists ::env(OT_F2_MODE)] && $::env(OT_F2_MODE) eq "clone"} { ot_f2_clone } else { ot_f2_eco }
    ot_f2_report post
  }
}
if {[info commands ot_f2_cts_inner] eq "" && [info commands clock_tree_synthesis] ne ""} {
  rename clock_tree_synthesis ot_f2_cts_inner
  proc clock_tree_synthesis {args} {
    set r [ot_f2_cts_inner {*}$args]
    ot_f2_post_cts
    return $r
  }
}

# ---- form (2) v2: per-leaf gate clones (OT_F2_MODE=clone) --------------------------------------------------------------
# The hop gate is cloned at every gated LEAF buffer of its tree: clone CLK on a nearby ungated tree net whose arrival is
# the ungated register reference minus (clone + leaf) delay, so the gate sits about one stage before the leaf and the gated
# body is built from the same tree as the ungated face (tracks across corners: the single hop gate fed a wire-dominated
# gated tree balanced in TT against a cell-dominated delay chain, -> 125 ps FF skew tap_q->ib_i). ENA / SE shared.
#   OT_F2_MIN_REGS (64) gates with fewer gated registers are kept   OT_F2_RAD (150) um tap search radius
proc ot_f2_leaves {icgn} {
  # buffers of the gated tree whose output net has register loads and no buffer loads -> {leafinst ...}; plus all tree bufs
  set leaves {}; set bufs {}; set mixed 0
  set q [list [get_nets -of_objects [get_pins $icgn/GCLK]]]
  set seen {}
  while {[llength $q]} {
    set n [lindex $q 0]; set q [lrange $q 1 end]
    if {$n eq "" || [catch {set nn [get_full_name $n]}]} continue
    if {[dict exists $seen $nn]} continue; dict set seen $nn 1
    set nb 0; set nr 0
    foreach ip [get_pins -quiet -of_objects $n -filter "direction==input"] {
      set c [get_cells -of_objects $ip]
      if {[catch {set ref [get_property $c ref_name]}]} continue
      if {[regexp {^(BUF|INV|CKINV|HB)} $ref]} {
        incr nb; lappend bufs [get_full_name $c]
        foreach op [get_pins -of_objects $c -filter "direction==output"] { catch { set on [get_nets -of_objects $op]; if {$on ne ""} { lappend q $on } } }
      } else { incr nr }
    }
    if {$nr && $nb} {
      incr mixed
      set rp {}
      foreach ip [get_pins -quiet -of_objects $n -filter "direction==input"] {
        set c [get_cells -of_objects $ip]
        if {[catch {set ref [get_property $c ref_name]}]} continue
        if {![regexp {^(BUF|INV|CKINV|HB)} $ref]} { lappend rp [get_full_name $ip] }
      }
      lappend ::ot_f2_mixed [list $nn $rp]
    }
    if {$nr && !$nb} {
      set drv ""
      foreach op [get_pins -quiet -of_objects $n -filter "direction==output"] { set drv [get_cells -of_objects $op] }
      if {$drv ne "" && [regexp {^(BUF|INV|CKINV|HB)} [get_property $drv ref_name]]} { lappend leaves [get_full_name $drv] }
    }
  }
  return [list $leaves $bufs $mixed]
}
proc ot_f2_clone {} {
  set block [ord::get_db_block]
  set minr [expr {[info exists ::env(OT_F2_MIN_REGS)] ? $::env(OT_F2_MIN_REGS) : 64}]
  set rad [expr {[info exists ::env(OT_F2_RAD)] ? $::env(OT_F2_RAD) : 150.0}]
  set pen [expr {[info exists ::env(OT_F2_PEN)] ? $::env(OT_F2_PEN) : 0.08}]
  set ref $::ot_f2_umed
  if {[info exists ::env(OT_F2_REF_PS)] && $::env(OT_F2_REF_PS) ne ""} { set ref $::env(OT_F2_REF_PS) }
  set taps [ot_f2_taps]
  set bufd [expr {[info exists ::env(OT_F2_BUFD)] ? $::env(OT_F2_BUFD) : 20.0}]
  set tot 0
  foreach r $::ot_f2_rows {
    lassign $r n ck gck nr
    if {$nr < $minr} continue
    set icgi [sta::sta_to_db_inst [get_cells $n]]
    set master [[$icgi getMaster] getName]
    if {[info exists ::env(OT_F2_ICGCELL)] && $::env(OT_F2_ICGCELL) ne ""} { set master $::env(OT_F2_ICGCELL) }
    set dicg [expr {$gck - $ck}]
    set ena [[$icgi findITerm ENA] getNet]; set se [[$icgi findITerm SE] getNet]
    set ::ot_f2_mixed {}
    lassign [ot_f2_leaves $n] leaves bufs mixed
    set k 0; set errs {}
    # pre-ECO numbers for every leaf first (arrivals change as the tree is edited)
    set plan {}
    foreach L $leaves {
      set li [sta::sta_to_db_inst [get_cells $L]]
      set ipin ""; set opin ""
      foreach it [$li getITerms] { if {[$it isInputSignal]} { set ipin [[$it getMTerm] getName] } elseif {[$it isOutputSignal]} { set opin [[$it getMTerm] getName] } }
      set aA [ot_f2_arr $L/$ipin]; set aY [ot_f2_arr $L/$opin]
      if {$aA eq "" || $aY eq ""} continue
      set tgt [expr {$ref - ($aY - $aA) - $dicg}]
      lassign [ot_f2_xy $li] lx ly
      set best ""; set be 1e9
      foreach t $taps {
        lassign $t a tn txy; lassign $txy tx ty
        set dist [expr {abs($tx - $lx) + abs($ty - $ly)}]
        if {$dist > $rad} continue
        set e [expr {abs($a + $bufd + $pen * $dist - $tgt)}]
        if {$e < $be} { set be $e; set best [list $a $tn $dist $txy] }
      }
      if {$best eq ""} { lappend errs $L; continue }
      lappend plan [list $L $ipin $lx $ly $tgt {*}$best]
    }
    if {![info exists ::env(OT_F2_MIXED)] || $::env(OT_F2_MIXED) ne "0"} {
      foreach mx $::ot_f2_mixed {
        lassign $mx mnet rps
        set sx 0.0; set sy 0.0; set nn 0
        foreach rp $rps { lassign [ot_f2_xy [sta::sta_to_db_inst [get_cells -of_objects [get_pins $rp]]]] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; incr nn }
        if {!$nn} continue
        set lx [expr {$sx / $nn}]; set ly [expr {$sy / $nn}]
        set tgt [expr {$ref - $dicg - 10.0}]
        set best ""; set be 1e9
        foreach t $taps {
          lassign $t a tn txy; lassign $txy tx ty
          set dist [expr {abs($tx - $lx) + abs($ty - $ly)}]
          if {$dist > $rad} continue
          set e [expr {abs($a + $bufd + $pen * $dist - $tgt)}]
          if {$e < $be} { set be $e; set best [list $a $tn $dist $txy] }
        }
        if {$best eq ""} { lappend errs $mnet; continue }
        lappend plan [list "#REGS" $rps $lx $ly $tgt {*}$best]
      }
    }
    set bufm [[ord::get_db] findMaster [expr {[info exists ::env(OT_F2_BUF)] ? $::env(OT_F2_BUF) : "BUFx12f_ASAP7_75t_R"}]]
    set icgm [[ord::get_db] findMaster $master]
    foreach p $plan {
      lassign $p L ipin lx ly tgt ta tn dist txy
      set id [incr ::ot_f2_cid]
      set tnet [$block findNet $tn]
      if {$L ne "#REGS"} { set li [$block findInst $L]; if {$li eq "NULL"} { lappend errs $L; continue } }
      if {$tnet eq "NULL"} { lappend errs $L; continue }
      # branch buffer at the tap driver (short stub on the tap net), clone at the leaf
      set bi [odb::dbInst_create $block $bufm "ot_f2b_$id"]
      lassign $txy tx ty
      $bi setLocation [ord::microns_to_dbu $tx] [ord::microns_to_dbu $ty]; $bi setPlacementStatus PLACED
      set bnet [odb::dbNet_create $block "ot_f2n_$id"]; $bnet setSigType CLOCK
      [$bi findITerm A] connect $tnet
      [$bi findITerm Y] connect $bnet
      set ci [odb::dbInst_create $block $icgm "ot_f2c_$id"]
      $ci setLocation [ord::microns_to_dbu $lx] [ord::microns_to_dbu $ly]; $ci setPlacementStatus PLACED
      set gnet [odb::dbNet_create $block "ot_f2g_$id"]; $gnet setSigType CLOCK
      [$ci findITerm CLK] connect $bnet
      [$ci findITerm ENA] connect $ena
      [$ci findITerm SE] connect $se
      [$ci findITerm GCLK] connect $gnet
      if {$L eq "#REGS"} {
        foreach rp $ipin {
          set ri [sta::sta_to_db_inst [get_cells -of_objects [get_pins $rp]]]
          set rit [$ri findITerm [lindex [split $rp /] end]]
          $rit disconnect; $rit connect $gnet
        }
        incr ::ot_f2_nmix
      } else {
        set lit [$li findITerm $ipin]
        $lit disconnect
        $lit connect $gnet
      }
      incr k
    }
    # upstream gated buffers left without loads
    set del 0
    for {set pass 0} {$pass < 30} {incr pass} {
      set any 0
      foreach b $bufs {
        set bi [$block findInst $b]; if {$bi eq "NULL" || $bi eq ""} continue
        set loads 0; set on ""
        foreach it [$bi getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
        if {$on ne "" && $on ne "NULL"} { foreach it [$on getITerms] { if {[$it isInputSignal]} { incr loads } } }
        if {!$loads} { delete_instance [get_cells $b]; incr del; set any 1 }
      }
      if {!$any} break
    }
    incr tot $k
    puts [format "OT_F2 clone %s: %d leaf gates (%s), %d tree bufs deleted, %d mixed nets kept, %d leaves without tap" $n $k $master $del $mixed [llength $errs]]
  }
  puts "OT_F2 clone: $::ot_f2_nmix mixed-net register groups moved onto their own clone"
  if {![info exists ::env(OT_F2_RD)] || $::env(OT_F2_RD) ne "0"} {
    catch {estimate_parasitics -placement}
    # the shared ENA / clone CLK branch nets now span the tile: buffer them (max slew / cap / wire), clock nets untouched
    repair_design
  }
  catch {estimate_parasitics -placement}
  # clone ENA setup
  set w 1e9; set nn 0
  foreach c [get_cells -quiet ot_f2c_*] {
    foreach pth [find_timing_paths -path_delay max -to [get_pins [get_full_name $c]/ENA] -group_path_count 1] { set s [get_property $pth slack]; incr nn; if {$s < $w} { set w $s } }
  }
  puts [format "OT_F2 clone: %d gates total, ENA setup ws %.1f over %d" $tot $w $nn]
}

# ---- form (2) L: late launch of the ungated face registers (OT_F2_LATE) --------------------------------------------------
# Measured on the ICG=2 NK CTS tree (FF): the single hop gate drives a wire-dominated gated tree that TritonCTS balanced in
# TT against a cell-dominated ungated delay chain, so at FF the gated body lands ~125 ps after the ungated face that
# launches into it with zero logic (tap_q -> ib_i / xl_q, tile_id_q -> g_tidr, constant ot_fconst -> tie ports).
# The launch registers matching OT_F2_LATE move onto a later ungated tree net (branch BUF at the tap driver), by the FF
# hold deficit of their fanout + OT_F2_LATE_M, capped by their own D-side FF hold slack - OT_F2_LATE_M. Runs on the
# synchronized FF scene, right before the CTS structural hold gate (offline: the single FF scene).
proc ot_f2_sc {} { if {[info exists ::ot_mm_synced] && $::ot_mm_synced} { return [list -scenes BC] }; return {} }
proc ot_f2_arrf {pin} {
  if {[info exists ::ot_mm_synced] && $::ot_mm_synced && [llength [info commands ot_mm_arrival_bc]]} { return [ot_mm_arrival_bc [get_pins $pin] arrival_max_rise] }
  return [ot_f2_arr $pin]
}
proc ot_f2_wslack {args} {
  set w 1e9
  foreach p [find_timing_paths -path_delay min {*}[ot_f2_sc] {*}$args -group_path_count 1] { set s [get_property $p slack]; if {$s ne "INF" && $s < $w} { set w $s } }
  return $w
}
proc ot_f2_late {} {
  if {![info exists ::env(OT_F2_LATE)] || $::env(OT_F2_LATE) eq ""} { return }
  if {[info exists ::ot_f2_late_done]} { return }
  set ::ot_f2_late_done 1
  set block [ord::get_db_block]
  set m [expr {[info exists ::env(OT_F2_LATE_M)] ? $::env(OT_F2_LATE_M) : 15.0}]
  set rad [expr {[info exists ::env(OT_F2_RAD)] ? $::env(OT_F2_RAD) : 150.0}]
  set pen [expr {[info exists ::env(OT_F2_LPEN)] ? $::env(OT_F2_LPEN) : 0.12}]
  set bufd [expr {[info exists ::env(OT_F2_LBUFD)] ? $::env(OT_F2_LBUFD) : 22.0}]
  set bufm [[ord::get_db] findMaster [expr {[info exists ::env(OT_F2_BUF)] ? $::env(OT_F2_BUF) : "BUFx12f_ASAP7_75t_R"}]]
  catch {estimate_parasitics [expr {[catch {grt::have_routes} h] || !$h ? "-placement" : "-global_routing"}]}
  # ungated tap nets with their (FF) driver arrival
  set taps {}
  foreach t [ot_f2_taps] {
    lassign $t a tn txy
    set d [lindex [get_pins -quiet -of_objects [get_nets $tn] -filter "direction==output"] 0]
    if {$d eq ""} continue
    set af [ot_f2_arrf [get_full_name $d]]; if {$af eq ""} continue
    lappend taps [list $af $tn $txy]
  }
  set groups {}
  set nf 0; set nskip 0
  foreach pat $::env(OT_F2_LATE) {
    foreach c [get_cells -quiet $pat] {
      if {![regexp {DFF} [get_property $c ref_name]]} continue
      set cn [get_full_name $c]
      set sq [ot_f2_wslack -from $c]
      if {$sq >= $m} continue
      set sd 1e9
      foreach dp [get_pins -quiet $cn/D] { set sd [ot_f2_wslack -to $dp] }
      # Q-side setup (mode ss / TT in the mm session) caps the move: an FF ps of clock delay costs ~1.4 TT ps
      set ss 1e9
      foreach p [find_timing_paths -path_delay max -from $c -group_path_count 1] { set s [get_property $p slack]; if {$s ne "INF" && $s < $ss} { set ss $s } }
      set delta [expr {min($m - $sq, $sd - $m, ($ss - $m) / 1.4)}]
      if {$delta < 5.0} { incr nskip; puts [format "OT_F2L skip %s: fanout hold %.1f, own D hold %.1f, Q setup %.1f" $cn $sq $sd $ss]; continue }
      set net [get_full_name [get_nets -of_objects [get_pins $cn/CLK]]]
      set key "$net|[expr {int($delta / 10.0)}]"
      dict lappend groups $key [list $cn $delta [ot_f2_arrf $cn/CLK]]
      incr nf
    }
  }
  set k 0
  dict for {key mem} $groups {
    set sx 0.0; set sy 0.0; set ds {}; set as {}
    foreach e $mem { lassign $e cn d a; lassign [ot_f2_xy [sta::sta_to_db_inst [get_cells $cn]]] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; lappend ds $d; lappend as $a }
    set n [llength $mem]; set lx [expr {$sx / $n}]; set ly [expr {$sy / $n}]
    set tgt [expr {[ot_f2_med $as] + [lindex [lsort -real $ds] 0]}]
    set best ""; set be 1e9
    foreach t $taps {
      lassign $t a tn txy; lassign $txy tx ty
      set dist [expr {abs($tx - $lx) + abs($ty - $ly)}]
      if {$dist > $rad} continue
      set est [expr {$a + $bufd + $pen * $dist}]
      if {$est < [ot_f2_med $as] + 0.5 * [lindex [lsort -real $ds] 0] || $est > $tgt + 20.0} continue
      set e [expr {abs($est - $tgt)}]
      if {$e < $be} { set be $e; set best [list $a $tn $dist $txy] }
    }
    if {$best eq ""} { puts "OT_F2L $key: no tap in the window"; continue }
    lassign $best ta tn dist txy; lassign $txy tx ty
    set id [incr ::ot_f2_cid]
    set bi [odb::dbInst_create $block $bufm "ot_f2l_$id"]
    $bi setLocation [ord::microns_to_dbu $tx] [ord::microns_to_dbu $ty]; $bi setPlacementStatus PLACED
    set bnet [odb::dbNet_create $block "ot_f2ln_$id"]; $bnet setSigType CLOCK
    [$bi findITerm A] connect [$block findNet $tn]
    [$bi findITerm Y] connect $bnet
    foreach e $mem { set it [[sta::sta_to_db_inst [get_cells [lindex $e 0]]] findITerm CLK]; $it disconnect; $it connect $bnet }
    incr k
    puts [format "OT_F2L group %s: %d flops, clk %.1f +%.1f -> tgt %.1f, tap %s arr %.1f dist %.0f" $key $n [ot_f2_med $as] [lindex [lsort -real $ds] 0] $tgt $tn $ta $dist]
  }
  catch {estimate_parasitics [expr {[catch {grt::have_routes} h] || !$h ? "-placement" : "-global_routing"}]}
  puts "OT_F2L: $nf face registers late-launched in $k branch groups ($nskip skipped)"
}
if {[info commands ot_hold_structural_gate] ne "" && [info commands ot_f2_gate_inner] eq ""} {
  rename ot_hold_structural_gate ot_f2_gate_inner
  proc ot_hold_structural_gate {} {
    if {[info exists ::ot_mm_synced] && $::ot_mm_synced && [ot_hold_stage] eq "cts"} {
      lassign [ot_hold_stats] w t n; puts [format "OT_F2L before: FF hold ws %.2f, %d endpoints" $w $n]
      ot_f2_late
      lassign [ot_hold_stats] w t n; puts [format "OT_F2L after: FF hold ws %.2f, %d endpoints" $w $n]
    }
    return [ot_f2_gate_inner]
  }
}
