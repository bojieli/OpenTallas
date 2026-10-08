# Corner-true vclk sign-off of a spine die view (approved common recipe 2026-10-06, the stations stn_margin_sdc.py
# FF file adapted to the spine io_vclk_m SDC; read by corner_sta.py --post-sdc after set_propagated_clock, in each
# corner's own session):
#   SS session: unchanged (setup against vclk at the SS insertion the flow measured; the 150 ps die-arrival term
#               stays in the 0.2 T + 150 ps IO budget).
#   FF session (rule H1, h1-verify 2026-10-08): the neighbour's die-clock leaf is within this block's own leaf spread
#               +- 50 ps; the sender carries that term once -- outputs timed against vclk at the FF MAXIMUM insertion
#               (latest capture) + 50 ps IO hold uncertainty; inputs launched at the FF MEAN insertion, 25 ps.
#   both:       the die reset (rst / por) reaches only the wrapper's two-flop synchroniser rst_s: false path.
# Per-BIT port direction from the odb (views agent, 2026-10-06): OpenSTA types a bus port by ONE direction, so the
# input bits of a mixed-direction bus (r16g direction model; inout bits retyped per bit by inout_retype_post_synth.tcl)
# are missing from [all_inputs] (and output bits of an input-typed bus from [all_outputs]).  Measured on cmdproc
# cpss4: all 827 cSW bits report 'output' while the odb holds the 40+ input bits as INPUT, so the FF hold launch
# (inputs at the FF max insertion) and the io_min die-path credit never reached them: input-pin flops showed -155 ps.
proc ot_port_dir {p} {
  if {[catch {set bt [[ord::get_db_block] findBTerm [get_full_name $p]]}] || $bt eq "NULL"} { return [get_property $p direction] }
  switch [$bt getIoType] { INPUT { return input } OUTPUT { return output } INOUT { return bidirect } default { return [get_property $p direction] } }
}
proc ot_dir_ports {want} {
  set l {}; set seen {}
  foreach p [concat [all_inputs -no_clocks] [all_outputs]] {
    set n [get_full_name $p]; if {[dict exists $seen $n]} { continue }; dict set seen $n 1
    if {[ot_port_dir $p] in $want} { lappend l $p }
  }
  return $l
}
foreach ot_p {rst[0] por} { if {[llength [get_ports -quiet $ot_p]]} { set_false_path -from [get_ports $ot_p] } }
if {[llength [get_libs -quiet *_FF_*]] && [llength [get_clocks -quiet vclk]]} {
  sta::redirect_string_begin
  report_clock_latency -clocks core_clk
  set ot_s [sta::redirect_string_end]
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> ot_lo ot_hi]} {
    # RULE H1 (h1-verify 2026-10-08): the link hold term is carried ONCE, by the sender, at the LATEST capture: outputs are
    # held against vclk at the FF MAXIMUM insertion + 50 ps IO hold uncertainty (was the FF minimum: the earliest capture,
    # optimistic by the leaf spread).  The receiver's inputs launch at the block's nominal (mean) FF insertion with the
    # plain 25 ps hold uncertainty (was the FF maximum + 50: the latest launch, optimistic, and the 50 counted twice).
    set_clock_latency $ot_hi [get_clocks vclk]
    set_output_delay -min 0 -clock vclk [ot_dir_ports {output bidirect}]
    set_input_delay -min [expr {($ot_lo + $ot_hi) / 2.0 - $ot_hi}] -clock vclk [ot_dir_ports {input bidirect}]
    set_clock_uncertainty -hold 25 -from [get_clocks vclk] -to [get_clocks core_clk]
    set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
    puts "OT_VCLK_CT: FF insertion $ot_lo .. $ot_hi ps: outputs vs vclk $ot_hi + 50 (H1 sender), inputs launched at the mean (receiver, 25)"
  } else {
    puts "OT_VCLK_CT: no core_clk latency report at FF"
  }
}
