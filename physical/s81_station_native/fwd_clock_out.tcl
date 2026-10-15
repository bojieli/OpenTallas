# S81 FILL 2026-10-15: forwarded-clock station boundary (ref_tile boundary_tcl, re-applied after every io_ref switch).
# fo0 is the forwarded CLOCK output (kept ot_fwd_clk_inv of fi0), not a data pin: the io_ref SDC puts the data output
# budget on [all_outputs], which turned fi0 -> fo0 into a timed input->output data path (10:09 verdicts: stnh/stnv
# 3x1/10x1/70x1/86x1 FF hold -58 'I2O' pin register missing).  Define it as what it is - a generated clock, inverted
# from fi0 - and remove the data output budget from it.  The forwarded clock vs data skew is a die-level (hop) check.
if {[llength [get_ports -quiet fo0]] && [llength [get_ports -quiet fi0]]} {
  unset_output_delay [get_ports fo0]
  if {![llength [get_clocks -quiet fo0_fwd]]} {
    create_generated_clock -name fo0_fwd -source [get_ports fi0] -invert -divide_by 1 [get_ports fo0]
  }
  puts "OT_FWD_CLOCK_OUT: fo0 = generated clock fo0_fwd (inverted fi0), no data output budget"
}
