# H-NETLIST F1 2026-10-16: forwarded-clock FORK relay boundary (hbfd_rly_*_fc_f<N>; ref_tile boundary_tcl + sdc_extra).
# Same rules as fc_clock.tcl, per branch k: clk_out<k> = generated clock clk_out<k>_fwd (clk_in, divide 1), never a data
# pin; o<k>[*] setup 0.2 T against clk_out<k>_fwd and must trail it by >= the forwarded-hop min separation (85 ps for
# the > 256 b class, 55 ps otherwise); i[*] against clk_in (max 0.2 T, min the same separation).  After CTS: every
# clk_out<k> buffer input (taken off clk_in for CTS by fcf_pre_cts.tcl) is reconnected to the clk_in root net.
if {[llength [get_ports -quiet clk_in]] && [llength [get_ports -quiet clk_out*]]} {
  set ot_fc_wide [expr {[llength [get_ports -quiet {i[*]}]] > 256}]
  set ot_fc_ib [expr {[info exists ::env(OT_FC_IN_MAX_PS)] ? $::env(OT_FC_IN_MAX_PS) : 166.667}]
  set ot_fc_im [expr {[info exists ::env(OT_FC_IN_MIN_PS)] ? $::env(OT_FC_IN_MIN_PS) : ($ot_fc_wide ? 85 : 55)}]
  set ot_fc_ob [expr {[info exists ::env(OT_FC_OUT_MAX_PS)] ? $::env(OT_FC_OUT_MAX_PS) : 166.667}]
  set ot_fc_om [expr {[info exists ::env(OT_FC_OUT_MIN_PS)] ? $::env(OT_FC_OUT_MIN_PS) : ($ot_fc_wide ? 85 : 55)}]
  set ot_fc_ck [expr {[llength [get_clocks -quiet core_clk]] ? "core_clk" : [get_object_name [lindex [all_clocks] 0]]}]
  set ot_fc_nb 0; set ot_fc_no 0
  foreach ot_fc_cp [get_ports -quiet clk_out*] {
    set ot_fc_cn [get_full_name $ot_fc_cp]
    if {![regexp {^clk_out(\d*)$} $ot_fc_cn -> ot_fc_k]} { continue }
    unset_output_delay $ot_fc_cp
    if {![llength [get_clocks -quiet ${ot_fc_cn}_fwd]]} {
      create_generated_clock -name ${ot_fc_cn}_fwd -source [get_ports clk_in] -divide_by 1 $ot_fc_cp
    }
    set ot_fc_do [get_ports -quiet "o${ot_fc_k}\[*\]"]
    if {[llength $ot_fc_do]} {
      unset_output_delay $ot_fc_do
      set_output_delay $ot_fc_ob -max -clock ${ot_fc_cn}_fwd $ot_fc_do
      set_output_delay [expr {0 - $ot_fc_om}] -min -clock ${ot_fc_cn}_fwd $ot_fc_do
      incr ot_fc_no [llength $ot_fc_do]
    }
    incr ot_fc_nb
  }
  set ot_fc_di [get_ports -quiet {i[*]}]
  if {[llength $ot_fc_di]} {
    unset_input_delay $ot_fc_di
    set_input_delay $ot_fc_ib -max -clock $ot_fc_ck $ot_fc_di
    set_input_delay $ot_fc_im -min -clock $ot_fc_ck $ot_fc_di
  }
  puts "OT_FCF_CLOCK: $ot_fc_nb branches clk_out<k>_fwd; $ot_fc_no o<k> vs their clk_out<k>_fwd (max $ot_fc_ob / min -$ot_fc_om), [llength $ot_fc_di] i vs clk_in (max $ot_fc_ib / min $ot_fc_im)"
}
if {![catch {ord::get_db_block} ot_fc_blk] && $ot_fc_blk ne "NULL" && ![catch {$ot_fc_blk getInsts} ot_fc_all]} {
  set ot_fc_bt [$ot_fc_blk findBTerm clk_in]
  set ot_fc_rc 0
  foreach inst $ot_fc_all {
    if {![string match *u_fcb_ck* [$inst getName]]} { continue }
    set ot_fc_it [$inst findITerm A]
    if {[$ot_fc_it getNet] eq "NULL" && $ot_fc_bt ne "NULL" && [$ot_fc_bt getNet] ne "NULL"} {
      $inst setDoNotTouch 0
      $ot_fc_it connect [$ot_fc_bt getNet]
      $inst setDoNotTouch 1
      incr ot_fc_rc
    }
  }
  if {$ot_fc_rc} { puts "OT_FCF: $ot_fc_rc clk_out buffer inputs reconnected to the clk_in root net" }
}
