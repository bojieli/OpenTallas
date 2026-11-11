# HEAD-92 11-10 hd_mesh form ZLP (zero-logic hold pad, hold safe by construction; COORD fail_watch 0432aced49ac).
# Read of a2 (FF, routed): 1754 hold violators, all register starts; 1239 same tap (CRPR ~-37, net skew med 7.5 ps)
# and 515 cross tap; data path med 42.9 ps = clk-Q + one INV/BUF: shift chains / pipeline copies whose zero-logic
# data delay is below 25 ps hold uncertainty + ~14 ps hold time + leaf skew.  GRT hold repair needed >3 h
# (8700 -> 526 endpoints, OT_HOLD_STALL) and route lost ~25 ps again.
# This PRE_CTS step puts ONE kept HB4xp67 (~37-47 ps FF) in front of every register / SRAM data or async input
# whose driver reaches a register Q/QN through at most OT_ZLP_DEPTH buffer / inverter cells (no other logic).
# Data pins only: async RESETN/SETN are rewired by reset_taps.tcl later in PRE_CTS (removal stays with GRT repair).
# Clock nets never qualify (their drivers are ports / clock cells, not register outputs).  Pads are buffers:
# logic unchanged.  NOT dont_touch (a dont_touch load blocks repair_design buffering of the driver net, RSZ-3006);
# zero-logic hops carry no setup demand, so setup repair has no reason to touch them.  CTS detailed_placement legalizes.
# Env: OT_ZLP (1 = on), OT_ZLP_DEPTH (default 4), OT_ZLP_MAX (abort above, default 150000), OT_ZLP_REPORT_ONLY,
#      OT_ZLP_PORTS (1 = also pad register D pins fed by an input data port: port-start hold, hd_spn LK/LK0).
proc zlp_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
if {[zlp_env OT_ZLP 0] eq "1"} {
  set zlp_depth [zlp_env OT_ZLP_DEPTH 4]
  set zlp_max [zlp_env OT_ZLP_MAX 150000]
  set zlp_ronly [zlp_env OT_ZLP_REPORT_ONLY 0]
  set ::zlp_ports [zlp_env OT_ZLP_PORTS 0]
  set zlp_blk [ord::get_db_block]
  set zlp_master [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
  if {$zlp_master eq "NULL" || $zlp_master eq ""} { error "OT_ZLP: HB4xp67_ASAP7_75t_R master missing" }
  proc zlp_is_reg {m} { regexp {^(DFF|DHL|DLL|ASYNC_DFF|SDF)} [$m getName] }
  proc zlp_is_bufinv {m} { regexp {^(BUF|INV|HB)[x0-9]} [$m getName] }
  # driver output iterm of a net (NULL for a port / undriven net)
  proc zlp_driver {n} {
    foreach it [$n getITerms] { if {[$it isOutputSignal]} { return $it } }
    return ""
  }
  # 1 when the net reaches a register Q/QN through only buffer / inverter cells (depth bounded)
  proc zlp_zero_logic {n depth} {
    for {set d 0} {$d <= $depth} {incr d} {
      if {$n eq "NULL" || $n eq ""} { return 0 }
      set st [$n getSigType]
      if {$st eq "CLOCK" || $st eq "POWER" || $st eq "GROUND"} { return 0 }
      set drv [zlp_driver $n]
      if {$drv eq ""} {
        # OT_ZLP_PORTS=1: an input data port (not a clock / forwarded clock port) also counts as a launch point
        if {$::zlp_ports ne "1"} { return 0 }
        foreach bt [$n getBTerms] {
          if {[$bt getIoType] eq "INPUT" && [$bt getSigType] ne "CLOCK" && ![regexp {^(f?clk|arst)} [$bt getName]]} { return 1 }
        }
        return 0
      }
      set m [[$drv getInst] getMaster]
      if {[zlp_is_reg $m]} { return [regexp {^QN?$} [[$drv getMTerm] getName]] }
      if {![zlp_is_bufinv $m]} { return 0 }
      set nx ""
      foreach it [[$drv getInst] getITerms] { if {[$it isInputSignal]} { set nx [$it getNet]; break } }
      set n $nx
    }
    return 0
  }
  set zlp_sinks {}
  set zlp_seen_dt 0
  foreach inst [$zlp_blk getInsts] {
    set m [$inst getMaster]
    set is_reg [zlp_is_reg $m]
    set is_mac [expr {[$m getType] eq "BLOCK"}]
    if {!$is_reg && !$is_mac} { continue }
    foreach it [$inst getITerms] {
      if {![$it isInputSignal]} { continue }
      set pn [[$it getMTerm] getName]
      if {$is_reg && ![regexp {^D$} $pn]} { continue }
      set n [$it getNet]
      if {$n eq "NULL" || $n eq ""} { continue }
      if {[$inst isDoNotTouch] || [$n isDoNotTouch]} { incr zlp_seen_dt; continue }
      if {[zlp_zero_logic $n $zlp_depth]} { lappend zlp_sinks $it }
    }
  }
  set zlp_n [llength $zlp_sinks]
  puts "OT_ZLP census: $zlp_n zero-logic register/SRAM input pins (depth $zlp_depth, dont_touch skipped $zlp_seen_dt)"
  if {$zlp_n > $zlp_max} { error "OT_ZLP: $zlp_n pads > OT_ZLP_MAX $zlp_max" }
  if {$zlp_ronly ne "1"} {
    set i 0
    foreach it $zlp_sinks {
      set n [$it getNet]
      set inst [$it getInst]
      set nn [odb::dbNet_create $zlp_blk "zlp_n_$i"]
      set pad [odb::dbInst_create $zlp_blk $zlp_master "zlp_pad_$i"]
      $it disconnect
      $it connect $nn
      foreach pit [$pad getITerms] {
        set pmn [[$pit getMTerm] getName]
        if {$pmn eq "A"} { $pit connect $n } elseif {$pmn eq "Y"} { $pit connect $nn }
      }
      set loc [$inst getLocation]
      $pad setLocation [lindex $loc 0] [lindex $loc 1]
      $pad setPlacementStatus PLACED
      incr i
    }
    puts "OT_ZLP inserted $i HB4xp67 pads (legalized by CTS detailed_placement)"
  }
}
