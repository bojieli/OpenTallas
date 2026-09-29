# ORFS step hook (PRE_CTS, PRE_GLOBAL_ROUTE) for the local K arbitration trunk cuts
# (tools/v41x_karb_local_pnr.py): repair_timing's default buffer budget (-max_buffer_percent 20, of the
# design's instances) is exhausted by millimetre trunks whose few hundred flops drive ~600 long nets
# (RSZ-0060 "Max buffer count reached").  Raise that tool budget only; clock, uncertainty, I/O delays and
# every timing constraint are unchanged.
if { [info procs repair_timing_helper] ne "" && [info procs ot_orig_repair_timing_helper] eq "" } {
  rename repair_timing_helper ot_orig_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_orig_repair_timing_helper {*}$args -max_buffer_percent 100
  }
}
