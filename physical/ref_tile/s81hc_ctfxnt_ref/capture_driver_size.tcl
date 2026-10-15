# Seven measured input capture paths ended in a BUFx2 driving two pin-owned D
# loads (~16 fF). Size those real final drivers to BUFx3 after CTS hold repair.
# TT experiment: worst capture199.439 ->189.1ps; FF hold residual cost rises
# by7.6..8.1ps. Full source CTS, legal placement and routed MM remain required.
# No registers, nets, pin positions, clock roots or timing constraints change.
set ot_nt_size_bits {1004 1018 857 855 853 840 838}
set ot_nt_size_block [ord::get_db_block]
set ot_nt_size_cts [expr {[llength [info procs ::ot_ref_cts_boundary_orig]] && [info exists ::cts_args]}]
set ot_nt_size_targets {}; set ot_nt_size_early 0
foreach inst [$ot_nt_size_block getInsts] {
  set plain [string map {\\ ""} [$inst getName]]
  if {![regexp {^fdx\[([0-9]+)\]\$_DFF_P_$} $plain -> bit] || $bit ni $ot_nt_size_bits} continue
  set d [$inst findITerm D]
  if {$d eq "NULL" || [$d getNet] eq "NULL"} { error "NORM_CAPTURE_SIZE: missing D for $plain" }
  set driver ""
  foreach it [[$d getNet] getITerms] { if {[$it isOutputSignal]} { set driver [$it getInst]; break } }
  if {$driver eq ""} { error "NORM_CAPTURE_SIZE: no driver for $plain" }
  # The boundary is also applied inside the CTS wrapper, before hold repair.
  if {![string match hold* [$driver getName]]} { incr ot_nt_size_early; continue }
  set master [[$driver getMaster] getName]
  if {$master ni {BUFx2_ASAP7_75t_R BUFx3_ASAP7_75t_R}} { error "NORM_CAPTURE_SIZE: unexpected $master for $plain" }
  dict set ot_nt_size_targets [$driver getName] $driver
}
set ot_nt_size_count [dict size $ot_nt_size_targets]
if {$ot_nt_size_cts && $ot_nt_size_count == 0 && $ot_nt_size_early == 7} {
  puts "NORM_CAPTURE_SIZE: defer until post-CTS hold repair"
} else {
  if {$ot_nt_size_count != 7 || $ot_nt_size_early} { error "NORM_CAPTURE_SIZE: incomplete measured driver set ($ot_nt_size_count, early $ot_nt_size_early)" }
  set ot_nt_size_n 0
  foreach name [lsort [dict keys $ot_nt_size_targets]] {
    set driver [dict get $ot_nt_size_targets $name]
    if {[[$driver getMaster] getName] eq "BUFx2_ASAP7_75t_R"} {
      if {!$ot_nt_size_cts} { error "NORM_CAPTURE_SIZE: unsized driver $name outside CTS; rerun actual CTS" }
      if {![$driver swapMaster [[ord::get_db] findMaster BUFx3_ASAP7_75t_R]]} { error "NORM_CAPTURE_SIZE: swap failed for $name" }
      incr ot_nt_size_n
    }
    set_dont_touch [get_cells $name]
  }
  if {$ot_nt_size_n} {
    # BUFx3 occupies a larger legal footprint; do not leave an overlapping ECO.
    detailed_placement
    check_placement -verbose
    estimate_parasitics -placement
  }
  puts "NORM_CAPTURE_SIZE: $ot_nt_size_n resized; seven final capture drivers verified"
}
