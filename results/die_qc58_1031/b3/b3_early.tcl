# DIE-QC-58A variant B3 (no RTL change): planned early clock branch for the root-ICG enable state + ENA repeater.
# Sourced at the end of the kit's orfs_hold_mm.tcl; acts once, right after clock_tree_synthesis (CTS stage only).
#   OT_B3_ICG    root ICG instance (e.g. g_icg.g_root.u_icg)
#   OT_B3_EARLY  cell patterns of enable-state flops clocked at the ICG's own insertion: CLK moved onto the ICG CLK net
#                through one branch buffer (OT_B3_EBUF, default BUFx8) at the group centroid
#   OT_B3_MID    "pattern=target_ps ..." flops whose D cone is late (body / input face): CLK moved to the ungated
#                pre-gate tree net whose TT arrival is nearest target_ps - OT_B3_MBUF_PS, through a local branch buffer
#   OT_B3_ENA_UM ENA wire length (um, driver->ICG manhattan) above which repeaters are inserted (one per 120 um)
# Clock definitions, SDC, corners, margins and the structural hold gate are unchanged.
proc ot_b3_arr {pin} {
  set p [get_pins $pin]
  foreach prop {arrival_max_rise max_rise_arrival} { if {![catch {get_property $p $prop} v] && $v ne ""} { return $v } }
  return ""
}
proc ot_b3_xy {dbi} {
  set l [$dbi getLocation]
  return [list [ord::dbu_to_microns [lindex $l 0]] [ord::dbu_to_microns [lindex $l 1]]]
}
proc ot_b3_ena_report {tag} {
  set icg $::env(OT_B3_ICG)
  catch {estimate_parasitics -placement}
  set w 1e9; set n 0
  foreach pth [find_timing_paths -path_delay max -to [get_pins $icg/ENA] -group_path_count 200 -endpoint_path_count 200 -unique_paths_to_endpoint] {
    set s [get_property $pth slack]; set sp [get_full_name [get_property $pth startpoint]]
    if {$n < 20} { puts [format "OT_B3 %s ENA setup %8.1f  %s" $tag $s $sp] }
    incr n; if {$s < $w} { set w $s }
  }
  puts [format "OT_B3 %s ENA setup ws %.1f (%d starts), ICG CLK arr %s" $tag $w $n [ot_b3_arr $icg/CLK]]
}
proc ot_b3_brbuf {pins xy name cell {clk 1}} {
  catch {estimate_parasitics -placement}
  set r [insert_buffer -buffer_cell $cell -load_pins $pins -location $xy -buffer_name $name]
  set bi [[ord::get_db_block] findInst $name]
  if {$bi eq "NULL" || $bi eq ""} {
    foreach i [[ord::get_db_block] getInsts] { if {[string match "*$name*" [$i getName]]} { set bi $i } }
  }
  if {$bi eq "NULL" || $bi eq ""} { error "OT_B3: branch buffer $name not created" }
  if {$clk} { foreach it [$bi getITerms] { set n [$it getNet]; if {$n ne "NULL" && $n ne "" && ![$n isSpecial]} { $n setSigType CLOCK } } }
  return $bi
}

# OT_B3_SWAP=1: move the gate deeper. The CTS delay chain behind GCLK (single-fanout BUFs) is removed and the ICG CLK pin
# is re-tapped on the ungated pre-gate chain at (old CLK arrival + removed chain delay - OT_B3_SWAP_COMP_PS): gated sink
# latency is kept, the ENA capture edge moves later by the chain delay.
proc ot_b3_swap {icgi taps} {
  set icg $::env(OT_B3_ICG)
  set gnet [[$icgi findITerm GCLK] getNet]
  set chain {}
  set n $gnet
  while {1} {
    set loads {}
    foreach it [$n getITerms] { if {[$it isInputSignal]} { lappend loads $it } }
    if {[llength $loads] != 1} break
    set li [[lindex $loads 0] getInst]
    if {![string match "BUF*" [[$li getMaster] getName]] || ![string match "delaybuf_*" [$li getName]]} break
    lappend chain $li
    set n [[$li findITerm Y] getNet]
  }
  if {![llength $chain]} { puts "OT_B3 swap: no delay chain behind GCLK"; return }
  set last [lindex $chain end]
  set a0 [ot_b3_arr $icg/CLK]; set ag [ot_b3_arr $icg/GCLK]; set al [ot_b3_arr [$last getName]/Y]
  set d [expr {$al - $ag}]
  set comp [expr {[info exists ::env(OT_B3_SWAP_COMP_PS)] ? $::env(OT_B3_SWAP_COMP_PS) : 0.0}]
  set tgt [expr {$a0 + $d - $comp}]
  set best ""; set bd 1e9
  foreach t $taps { lassign $t a nn xy; set e [expr {abs($a - $tgt)}]; if {$e < $bd} { set bd $e; set best $t } }
  lassign $best ta tn txy
  puts [format "OT_B3 swap: %d chain bufs (%.1f ps) removed; ICG CLK %.1f -> tap %s arr %.1f at %s (target %.1f)" [llength $chain] $d $a0 $tn $ta $txy $tgt]
  set lnet [[$last findITerm Y] getNet]
  set lpins {}
  foreach it [$lnet getITerms] { if {[$it isInputSignal]} { lappend lpins "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach b $chain {
    set bn [$b getName]
    foreach pn {A Y} { catch { set nn [[[$b findITerm $pn] getNet] getName]; disconnect_pin [get_nets $nn] [get_pins $bn/$pn] } }
  }
  foreach p $lpins { connect_pin [get_nets [$gnet getName]] [get_pins $p] }
  foreach b $chain { delete_instance [get_cells [$b getName]] }
  set old [[$icgi findITerm CLK] getNet]
  disconnect_pin [get_nets [$old getName]] [get_pins $icg/CLK]
  connect_pin [get_nets $tn] [get_pins $icg/CLK]
  catch {estimate_parasitics -placement}
  puts [format "OT_B3 swap done: ICG CLK %.1f GCLK %.1f (was %.1f / chain end %.1f)" [ot_b3_arr $icg/CLK] [ot_b3_arr $icg/GCLK] $a0 $al]
}

# PRE_CTS (called from b3_pre_cts.tcl): place the root ICG beside its enable cone, OT_B3_ICG_AT = "x y" (um) or "mid" =
# centroid of the OT_B3_MID flops (the late-launched enable terms), so the ENA net is short. CTS then builds the
# gated tree from there; the post-CTS detailed_placement legalizes the ICG.
proc ot_b3_pre_cts {} {
  if {![info exists ::env(OT_B3_ICG_AT)] || $::env(OT_B3_ICG_AT) eq ""} { return }
  set icgi [sta::sta_to_db_inst [get_cells $::env(OT_B3_ICG)]]
  set at $::env(OT_B3_ICG_AT)
  if {$at eq "mid"} {
    set sx 0.0; set sy 0.0; set n 0
    foreach spec $::env(OT_B3_MID) {
      foreach c [get_cells -quiet [lindex [split $spec =] 0]] {
        lassign [ot_b3_xy [sta::sta_to_db_inst $c]] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; incr n
      }
    }
    if {!$n} { error "OT_B3: OT_B3_ICG_AT mid but no OT_B3_MID flops" }
    set at [list [expr {$sx / $n}] [expr {$sy / $n}]]
  }
  set was [ot_b3_xy $icgi]
  lassign $at x y
  $icgi setLocation [ord::microns_to_dbu $x] [ord::microns_to_dbu $y]
  $icgi setPlacementStatus PLACED
  puts "OT_B3 pre-CTS: ICG [$icgi getName] moved $was -> [ot_b3_xy $icgi]"
}
proc ot_b3_early_branch {} {
  if {![info exists ::env(OT_B3_ICG)] || $::env(OT_B3_ICG) eq ""} { return }
  if {[info exists ::ot_b3_done]} { return }
  set ::ot_b3_done 1
  set block [ord::get_db_block]
  set icg $::env(OT_B3_ICG)
  set icgi [sta::sta_to_db_inst [get_cells $icg]]
  set cknet [[$icgi findITerm CLK] getNet]
  puts "OT_B3 ICG $icg CLK net [$cknet getName] at [ot_b3_xy $icgi]"
  catch {estimate_parasitics -placement}
  ot_b3_ena_report pre
  # ungated pre-gate tree nets (driver arrival), BFS from the ICG CLK net's root (clock source port) via buffers only
  set taps {}
  set q {}
  foreach c [all_clocks] {
    if {[catch {set srcs [get_property $c sources]}] || $srcs eq "" || $srcs eq "NULL"} continue
    foreach s $srcs {
      set bt [$block findBTerm [get_full_name $s]]
      if {$bt ne "" && $bt ne "NULL" && [$bt getNet] ne "NULL"} { lappend q [get_nets [[$bt getNet] getName]] }
    }
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
        set a [ot_b3_arr [get_full_name $op]]
        catch { set on [get_nets -of_objects $op]; if {$on ne ""} { lappend q $on; if {$a ne ""} { lappend taps [list $a [get_full_name $on] [ot_b3_xy [sta::sta_to_db_inst $c]]] } } }
      }
    }
  }
  puts "OT_B3 ungated buffer nets: [llength $taps]"
  set moved 0
  # early group -> ICG CLK net + one branch buffer at the centroid
  set epins {}; set sx 0.0; set sy 0.0
  if {[info exists ::env(OT_B3_EARLY)]} {
    foreach pat $::env(OT_B3_EARLY) {
      foreach c [get_cells -quiet $pat] {
        if {![regexp {DFF} [get_property $c ref_name]]} continue
        set dbi [sta::sta_to_db_inst $c]; set it [$dbi findITerm CLK]
        puts [format "OT_B3 early %s clk %s -> %s" [get_full_name $c] [ot_b3_arr [get_full_name $c]/CLK] [$cknet getName]]
        disconnect_pin [get_nets [[$it getNet] getName]] [get_pins [get_full_name $c]/CLK]
        connect_pin [get_nets [$cknet getName]] [get_pins [get_full_name $c]/CLK]
        lassign [ot_b3_xy $dbi] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]
        lappend epins [get_pins [get_full_name $c]/CLK]
      }
    }
  }
  if {[llength $epins]} {
    set cell [expr {[info exists ::env(OT_B3_EBUF)] ? $::env(OT_B3_EBUF) : "BUFx8_ASAP7_75t_R"}]
    set xy [list [expr {$sx / [llength $epins]}] [expr {$sy / [llength $epins]}]]
    ot_b3_brbuf $epins $xy ot_b3_eb0 $cell
    incr moved [llength $epins]
    puts "OT_B3 early branch: [llength $epins] flops, buffer ot_b3_eb0 ($cell) at $xy"
  }
  if {[info exists ::env(OT_B3_SWAP)] && $::env(OT_B3_SWAP) eq "1"} { ot_b3_swap $icgi $taps }
  # ENA repeaters
  set lim [expr {[info exists ::env(OT_B3_ENA_UM)] ? $::env(OT_B3_ENA_UM) : 0}]
  if {$lim > 0} {
    set ena [get_pins $icg/ENA]
    set en [[$icgi findITerm ENA] getNet]
    set drv ""
    foreach it [$en getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst] } }
    if {$drv ne ""} {
      lassign [ot_b3_xy $drv] dx dy; lassign [ot_b3_xy $icgi] ix iy
      set len [expr {abs($dx - $ix) + abs($dy - $iy)}]
      set nr [expr {int($len / 120.0)}]
      if {$len > $lim && $nr < 1} { set nr 1 }
      if {$len <= $lim} { set nr 0 }
      puts [format "OT_B3 ENA net %s driver %s len %.1f um -> %d repeaters (dont_touch)" [$en getName] [$drv getName] $len $nr]
      set load [list $ena]
      set ::ot_b3_rep {}
      for {set k 1} {$k <= $nr} {incr k} {
        set f [expr {double($k) / ($nr + 1)}]
        set xy [list [expr {$ix + ($dx - $ix) * $f}] [expr {$iy + ($dy - $iy) * $f}]]
        set bi [ot_b3_brbuf $load $xy ot_b3_er$k BUFx8_ASAP7_75t_R 0]
        lappend ::ot_b3_rep [$bi getName]
        puts "OT_B3 ENA repeater [$bi getName] at $xy"
        set load [list [get_pins [$bi getName]/A]]
      }
      foreach r $::ot_b3_rep { set_dont_touch [get_cells $r] }
    }
  }
  catch {estimate_parasitics -placement}
  # mid group -> ungated tap + local branch buffer; pass 2 re-picks the tap with the measured tap->CLK offset
  set mb [expr {[info exists ::env(OT_B3_MBUF_PS)] ? $::env(OT_B3_MBUF_PS) : 25.0}]
  set k 0
  set ::ot_b3_mset {}
  if {[info exists ::env(OT_B3_MID)]} {
    foreach spec $::env(OT_B3_MID) {
      lassign [split $spec =] pat tgt0
      foreach c [get_cells -quiet $pat] {
        if {![regexp {DFF} [get_property $c ref_name]]} continue
        set cn [get_full_name $c]
        set was [ot_b3_arr $cn/CLK]
        set tgt $tgt0
        if {$tgt eq "auto"} {
          # shift = ENA deficit + margin, unless that leaves the flop's own D setup below the margin: then balance the two
          set mg [expr {[info exists ::env(OT_B3_MID_MARGIN)] ? $::env(OT_B3_MID_MARGIN) : 30.0}]
          set se 1e9; foreach pth [find_timing_paths -path_delay max -from $c -to [get_pins $icg/ENA] -group_path_count 1] { set se [get_property $pth slack] }
          set sd 1e9; foreach pth [find_timing_paths -path_delay max -to [get_pins -of_objects $c -filter "direction==input"] -group_path_count 20 -endpoint_path_count 1] { set v [get_property $pth slack]; if {$v < $sd} { set sd $v } }
          set sh [expr {$mg - $se}]
          if {$sd - $sh < $mg} { set sh [expr {($sd - $se) / 2.0}] }
          if {$sh < 0} { set sh 0 }
          if {$se >= 1e8 || $sh < 1.0} { puts "OT_B3 mid $cn auto: not an ENA start or no deficit (ENA slack $se) -> left on its tree"; continue }
          set tgt [format %.1f [expr {$was - $sh}]]
          puts [format "OT_B3 mid %s auto: ENA slack %.1f, D setup %.1f -> shift %.1f, target %s" $cn $se $sd $sh $tgt]
        }
        dict set ::ot_b3_mset $cn 1
        set off $mb; set bi ""; set bestd 1e9; set bestn ""
        for {set pass 1} {$pass <= 3} {incr pass} {
          set best ""; set bd 1e9
          foreach t $taps { lassign $t a nn xy; set d [expr {abs($a + $off - $tgt)}]; if {$d < $bd} { set bd $d; set best $t } }
          if {$best eq ""} { error "OT_B3: no ungated tap for $pat" }
          lassign $best a nn txy
          if {$bi eq ""} {
            set dbi [sta::sta_to_db_inst $c]; set it [$dbi findITerm CLK]
            disconnect_pin [get_nets [[$it getNet] getName]] [get_pins $cn/CLK]
            connect_pin [get_nets $nn] [get_pins $cn/CLK]
            set bi [ot_b3_brbuf [list [get_pins $cn/CLK]] [ot_b3_xy $dbi] ot_b3_mb$k BUFx4_ASAP7_75t_R]
          } else {
            set ain [get_pins [$bi getName]/A]
            set cur [[[$bi findITerm A] getNet] getName]
            if {$cur ne $nn} { disconnect_pin [get_nets $cur] $ain; connect_pin [get_nets $nn] $ain }
          }
          catch {estimate_parasitics -placement}
          set got [ot_b3_arr $cn/CLK]
          puts [format "OT_B3 mid %s pass %d clk %s -> tap %s (arr %.1f at %s) got %.1f target %s" $cn $pass $was $nn $a $txy $got $tgt]
          set off [expr {$got - $a}]
          if {abs($got - $tgt) < $bestd} { set bestd [expr {abs($got - $tgt)}]; set bestn $nn }
          if {abs($got - $tgt) <= 15.0} break
        }
        set cur [[[$bi findITerm A] getNet] getName]
        if {$cur ne $bestn} {
          disconnect_pin [get_nets $cur] [get_pins [$bi getName]/A]; connect_pin [get_nets $bestn] [get_pins [$bi getName]/A]
          catch {estimate_parasitics -placement}
          puts [format "OT_B3 mid %s best pass tap %s got %.1f target %s" $cn $bestn [ot_b3_arr $cn/CLK] $tgt]
        }
        incr k; incr moved
      }
    }
  }
  # planned hold pads: a re-tapped (earlier) launch into a late capture outside the re-tapped set gets HB4 data hold
  # buffers at the capture pin until its TT hold slack >= OT_B3_PAD_TT_PS (structural part of the early branch).
  if {[info exists ::env(OT_B3_PAD_TT_PS)] && [dict size $::ot_b3_mset]} {
    set want $::env(OT_B3_PAD_TT_PS)
    set hb [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
    unset_dont_use $hb
    set np 0
    foreach cn [dict keys $::ot_b3_mset] {
      set eps {}
      foreach pth [find_timing_paths -path_delay min -from [get_cells $cn] -group_path_count 50 -endpoint_path_count 1] {
        lappend eps [list [get_full_name [get_property $pth endpoint]] [get_property $pth slack]]
      }
      foreach e $eps {
        lassign $e epn s
        set ec [lindex [split $epn /] 0]
        if {[dict exists $::ot_b3_mset $ec] || [string match "g_icg.*" $ec]} continue
        set j 0
        while {$s < $want && $j < 12} {
          set dbi [sta::sta_to_db_inst [get_cells $ec]]
          ot_b3_brbuf [list [get_pins $epn]] [ot_b3_xy $dbi] ot_b3_hp${np}_$j HB4xp67_ASAP7_75t_R 0
          incr j
          catch {estimate_parasitics -placement}
          set s [get_property [lindex [find_timing_paths -path_delay min -to [get_pins $epn] -group_path_count 1] 0] slack]
        }
        if {$j} { puts [format "OT_B3 hold pad %s <- %s: %d HB4, TT hold slack now %.1f" $epn $cn $j $s]; incr np }
      }
    }
    set_dont_use $hb
  }
  catch {estimate_parasitics -placement}
  if {[info exists ::env(OT_B3_EARLY)]} { foreach pat $::env(OT_B3_EARLY) { foreach c [get_cells -quiet $pat] { if {[regexp {DFF} [get_property $c ref_name]]} { puts "OT_B3 post [get_full_name $c] clk [ot_b3_arr [get_full_name $c]/CLK]" } } } }
  if {[info exists ::env(OT_B3_MID)]} { foreach spec $::env(OT_B3_MID) { foreach c [get_cells -quiet [lindex [split $spec =] 0]] { if {[regexp {DFF} [get_property $c ref_name]]} { puts "OT_B3 post [get_full_name $c] clk [ot_b3_arr [get_full_name $c]/CLK]" } } } }
  ot_b3_ena_report post
  puts "OT_B3 done: $moved flops re-tapped"
}
if {[info commands ot_b3_cts_inner] eq "" && [info commands clock_tree_synthesis] ne ""} {
  rename clock_tree_synthesis ot_b3_cts_inner
  proc clock_tree_synthesis {args} {
    set r [ot_b3_cts_inner {*}$args]
    ot_b3_early_branch
    return $r
  }
}
