# ORFS step hook (PRE_CTS, PRE_GLOBAL_ROUTE), drive-1013 2026-10-08: the INTERNAL-ONLY HA2 relay vehicle is a
# 1,088-bit flop-to-flop transfer with zero logic between launch and TX capture on different clock leaves (BC hold
# -29 ps at payload[208] -> send_data[208] before repair, 1,197 hold endpoints). Each bit needs ~2 hold buffers, which
# exceeds repair_timing's default -max_buffer_percent 20 of a register-only design (RSZ-0060 at 2,045 buffers;
# continuing past it then crashed CTS with SIGILL). Raise the cap; margins and constraints are unchanged.
if {[info procs repair_timing_helper] ne "" && [info procs ot_rsz_buf_orig] eq ""} {
  rename repair_timing_helper ot_rsz_buf_orig
  proc repair_timing_helper {args} { ot_rsz_buf_orig {*}$args -max_buffer_percent 100 }
}
