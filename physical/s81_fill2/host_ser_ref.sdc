# FILL-S2 (2026-10-15): serial clock ckv (3:4 to core_clk = ck) of the static layer-die host dsfd_host_c: stage-program outputs t_sseq_pw / t_sseq_plen and sequencer status input f_sseq_st on ckv; same form as physical/s81_fill2/sseq_ser_ref.sdc (from physical/s81_ph_views/gather/gth_ser_ref.sdc).
# (leaves dsfd_wfc_vmx_w / dsfd_wfc_vmx_r, cluster dsfd_wfc_stg_cl) on port ckv, RELATED 3:4 to core_clk = ck (one die
# PLL, /4 and /3 of 3.6 GHz).  No clock group and no exception: every crossing arc is a flop -> flop wire of
# ot_ratio_cdc_fifo and is timed at the 278 ps VCO-tick window (setup) and at the coincident edge (hold).
# Serial-domain ports get the reference flow's 0.2 T boundary against ser_clk: plain while the clocks are ideal
# (clock.sdc), referenced to the propagated serial tree at sign-off (signoff.sdc: the same PINFLOP reference
# io_ref_skew.sdc uses for core_clk).  The flow hooks re-apply it after every boundary switch (gth_ser_ref.tcl).
create_clock -name ser_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {ckv}]
set_clock_uncertainty -setup 60 [get_clocks ser_clk]
set_clock_uncertainty -hold 25 [get_clocks ser_clk]
if {![catch {get_property [get_clocks core_clk] is_propagated} ot_sb_p] && $ot_sb_p eq "1"} { set_propagated_clock [get_clocks ser_clk] }
catch {unset_input_delay [get_ports {ckv}]}
set_false_path -from [get_ports -quiet {rst rsv rst[*] rsv[*]}]
set ot_sb_si [get_ports -quiet {f_sseq_st f_sseq_st[*]}]
set ot_sb_so [get_ports -quiet {t_sseq_pw t_sseq_pw[*] t_sseq_plen t_sseq_plen[*]}]
set ot_sb_io [expr {0.2 * [get_property [get_clocks ser_clk] period]}]
if {[llength $ot_sb_si]} { unset_input_delay $ot_sb_si }
if {[llength $ot_sb_so]} { unset_output_delay $ot_sb_so }
set ot_sb_ref {}
if {[info procs ot_pf_ref] ne "" && [llength $ot_sb_si]} { set ot_sb_ref [ot_pf_ref $ot_sb_si] }
if {[llength $ot_sb_ref]} {
  set ot_sb_lmax [get_property $ot_sb_ref arrival_max_rise]
  set ot_sb_lmin [get_property $ot_sb_ref arrival_min_rise]
  set ot_sb_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set ot_sb_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set ot_sb_hi [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  puts "OT_SER_BOUNDARY referenced: ser pin flop [get_full_name $ot_sb_ref] arrival max $ot_sb_lmax min $ot_sb_lmin, [llength $ot_sb_si] in / [llength $ot_sb_so] out"
  set_input_delay [expr {$ot_sb_io + $ot_sb_lmax + $ot_sb_sk}] -max -clock ser_clk $ot_sb_si
  set_input_delay [expr {$ot_sb_lmin - $ot_sb_hi}] -min -clock ser_clk $ot_sb_si
  if {[llength $ot_sb_so]} {
    set_output_delay [expr {$ot_sb_io - $ot_sb_lmax + $ot_sb_sk}] -max -clock ser_clk $ot_sb_so
    set_output_delay [expr {0 - $ot_sb_lmin - $ot_sb_hk}] -min -clock ser_clk $ot_sb_so
  }
} else {
  puts "OT_SER_BOUNDARY plain: [llength $ot_sb_si] in / [llength $ot_sb_so] out at $ot_sb_io ps against ser_clk"
  if {[llength $ot_sb_si]} { set_input_delay $ot_sb_io -clock ser_clk $ot_sb_si }
  if {[llength $ot_sb_so]} { set_output_delay $ot_sb_io -clock ser_clk $ot_sb_so }
}
