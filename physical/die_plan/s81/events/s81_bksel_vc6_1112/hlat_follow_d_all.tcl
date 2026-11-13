# S81-ARCH-RTL-2 11-12 (DIE-S81-87 bksel hold, structural; core-kit twin of tools/die_plan/clock_taps.tcl TYPE-SAFE-1
# "clock follows data"): source AFTER regional_taps.tcl (PRE_CTS hook, all tap assignments done) when the RTL has
# dsdv_bksel_q HLAT 1.  Every zero-logic hop lockup latch u_fl_* (ot_s81ph_hlk, ASAP7 DLLx* negative-level / DHLx*) is
# re-hung on the clock net of the flop that drives its D (through BUF / INV / HB only): the launch -> latch check is
# intra-tap (one local TritonCTS tree, CRPR shared) and only latch -> capture crosses taps, with ~T/2 of hold margin.
# Legality (fail closed, OT_HLAT_STRICT 1 default): every u_fl_ latch must be a DLL/DHL cell on a CLOCK net, have a flop
# D-driver, and end on that flop's clock net; any miss is an error (no silent region-tap latch).  No u_fl_ cell = no-op.
uplevel #0 {
set hl_blk [ord::get_db_block]
set hl_strict [expr {[info exists ::env(OT_HLAT_STRICT)] ? $::env(OT_HLAT_STRICT) : 1}]
proc hl_clk {i} { foreach t [$i getITerms] { if {[[$t getMTerm] getSigType] eq "CLOCK" || [[$t getMTerm] getName] eq "CLK"} { return $t } }; return "" }
set hl_n 0; set hl_m 0; set hl_bad {}; set hl_nonlat 0; set hl_total 0
foreach hl_i [$hl_blk getInsts] {
  set hl_mn [[$hl_i getMaster] getName]
  if {[string match "DLLx*" $hl_mn] || [string match "DHLx*" $hl_mn]} {incr hl_total}
  # Yosys names many HLAT cells after their public output alias rather than u_fl_*.
  # These aliases account for 2,432 otherwise omitted latches in the OLL2/HLAT1 core.
  if {![regexp {(^|[./])(u_fl_(x|i0|c1|r1|r1s|pend|pe|o0m|o0p|o0s|row|g1|fq)|o0_m_l|o0_p_l|pend_d1_l|r1_d_l|g1_l|wdata_l|prevdata_l)} [$hl_i getName]]} continue
  if {![string match "DLLx*" $hl_mn] && ![string match "DHLx*" $hl_mn]} {
    if {[[$hl_i getMaster] isSequential]} { lappend hl_bad "[$hl_i getName] master $hl_mn" }
    incr hl_nonlat; continue }
  set hl_c [hl_clk $hl_i]
  if {$hl_c eq "" || [$hl_c getNet] eq "NULL"} { lappend hl_bad "[$hl_i getName] no clock"; continue }
  set hl_net ""; foreach t [$hl_i getITerms] { if {[[$t getMTerm] getName] eq "D"} { set hl_net [$t getNet] } }
  set hl_drv ""; set hl_seen {}
  while {$hl_net ne "" && $hl_net ne "NULL" && ![dict exists $hl_seen [$hl_net getName]] && $hl_drv eq ""} {
    dict set hl_seen [$hl_net getName] 1
    set hl_nx ""
    foreach t [$hl_net getITerms] {
      if {[[$t getMTerm] getIoType] ne "OUTPUT"} continue
      set d [$t getInst]
      if {[regexp {^(BUF|INV|HB)} [[$d getMaster] getName]]} {
        foreach u [$d getITerms] { if {[[$u getMTerm] getIoType] eq "INPUT" && [$u getNet] ne "NULL"} { set hl_nx [$u getNet] } }
      } elseif {[[$d getMaster] isSequential] && [hl_clk $d] ne ""} { set hl_drv $d }
    }
    set hl_net $hl_nx
  }
  if {$hl_drv eq ""} { lappend hl_bad "[$hl_i getName] D not driven by a flop through buffers"; continue }
  set hl_tn [[hl_clk $hl_drv] getNet]
  if {[$hl_c getNet] ne $hl_tn} { $hl_c disconnect; $hl_c connect $hl_tn; incr hl_m }
  incr hl_n
}
puts "OT_HLAT_FOLLOW_D: $hl_n hop latches on their launch flop's clock net ($hl_m re-hung), [llength $hl_bad] illegal, $hl_nonlat non-latch u_fl_ cells"
foreach b [lrange $hl_bad 0 19] { puts "OT_HLAT_FOLLOW_D illegal: $b" }
if {[info exists ::env(OT_HLAT_REQUIRE_ALL)] && $::env(OT_HLAT_REQUIRE_ALL) eq "1" && $hl_total != $hl_n} {error "OT_HLAT_FOLLOW_D incomplete: handled $hl_n of $hl_total negative latches (all-latch contract requested)"}
puts "OT_HLAT_COVERAGE handled=$hl_n total_negative_latches=$hl_total require_all=[expr {[info exists ::env(OT_HLAT_REQUIRE_ALL)] ? $::env(OT_HLAT_REQUIRE_ALL) : 0}]"
if {[llength $hl_bad] && $hl_strict} { error "OT_HLAT_FOLLOW_D: [llength $hl_bad] hop latches illegal (see above)" }
}
