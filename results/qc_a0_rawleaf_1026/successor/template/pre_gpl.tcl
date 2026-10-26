source /work/force_ff_pg.tcl
set ::env(OT_OFLOP_PORT_RE) {^(rst_n|v_d|first_d|split_d\[|w_d\[|x_d\[|t_out\[|fault_q\[)}
source /work/io_flop_at_pins.tcl

# PATH-QC 2026-10-25: release FF dont_touch AFTER the explicit PG connect and the io-flop anchor discovery.
# eliminate_dead_logic already ran at synth_odb (12030 FF present here), so DNT is no longer needed for retention;
# keeping it blocks timing-driven GPL / repair_design buffering of reset nets (RSZ-3006 on u_mul.rst_n).
# Retention is still gated by the post-DPL 12030-FF cohort check.
set ot_rel 0
foreach i [[ord::get_db_block] getInsts] {
  if {[string match DFF* [[$i getMaster] getName]] && [$i isDoNotTouch]} { $i setDoNotTouch false; incr ot_rel }
}
puts "OT_FF_DNT_RELEASED $ot_rel"
