# Corner-true vclk sign-off of a spine die view (approved common recipe 2026-10-06, the stations stn_margin_sdc.py
# FF file adapted to the spine io_vclk_m SDC; read by corner_sta.py --post-sdc after set_propagated_clock, in each
# corner's own session):
#   SS session: unchanged (setup against vclk at the SS insertion the flow measured; the 150 ps die-arrival term
#               stays in the 0.2 T + 150 ps IO budget).
#   FF session (rule H1, h1-verify 2026-10-08): the neighbour's die-clock leaf is at this block's FF mean insertion
#               +- 50 ps (die clock plan); the sender carries the 50 once -- outputs timed against vclk at the FF mean
#               + 50 ps IO hold uncertainty (latest capture); inputs launched at the FF mean, 25 ps.
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
  set ot_ok [regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> ot_lo ot_hi]
  # [vm8] 2026-10-10: report_clock_latency adds the MAX source latency to the MAX network latency even when they belong
  # to different clock ports (per-port set_clock_latency -source on face taps, tap_fclat.tcl): vm8bfp_new lvt FF read
  # 251.9 .. 541.7 (= tap source 253.6 + core network 288.1, no such pin) and put vclk at 396.8 ps, ~110 ps late.  Take
  # the range from the register clock pins' own arrivals (identical to the report when the source latency is uniform).
  if {$ot_ok} {
    catch {sta::worst_slack_cmd max}
    set ot_plo 1e9; set ot_phi -1e9
    foreach ot_cp [all_registers -clock_pins] {
      set ot_a [get_property $ot_cp arrival_max_rise]; set ot_b [get_property $ot_cp arrival_min_rise]
      if {[string is double -strict $ot_a] && $ot_a > $ot_phi} { set ot_phi $ot_a }
      if {[string is double -strict $ot_b] && $ot_b < $ot_plo} { set ot_plo $ot_b }
    }
    if {$ot_phi > -1e9 && $ot_plo < 1e9} { set ot_lo [format %.2f $ot_plo]; set ot_hi [format %.2f $ot_phi] }
  }
  if {$ot_ok} {
    # RULE H1 (h1-verify 2026-10-08): the die clock plan aligns every block's nominal (mean) insertion to one instant, so the
    # neighbour's leaf is at this block's FF mean +- the 50 ps die-skew term.  The sender carries that term ONCE, at the
    # latest capture: outputs held against vclk at the FF mean + 50 ps IO hold uncertainty (was the FF MINIMUM + 50: an
    # earlier-than-nominal capture, optimistic).  The receiver's inputs launch at the FF mean with the plain 25 ps (was
    # the FF MAXIMUM + 50: a later-than-nominal launch, optimistic, and the 50 counted on both ends).
    set_clock_latency [expr {($ot_lo + $ot_hi) / 2.0}] [get_clocks vclk]
    set_output_delay -min 0 -clock vclk [ot_dir_ports {output bidirect}]
    set_input_delay -min 0 -clock vclk [ot_dir_ports {input bidirect}]
    set_clock_uncertainty -hold 25 -from [get_clocks vclk] -to [get_clocks core_clk]
    set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
    puts "OT_VCLK_CT: FF insertion $ot_lo .. $ot_hi ps: outputs vs vclk at the mean + 50 (H1 sender), inputs launched at the mean (receiver, 25)"
  } else {
    puts "OT_VCLK_CT: no core_clk latency report at FF"
  }
}
