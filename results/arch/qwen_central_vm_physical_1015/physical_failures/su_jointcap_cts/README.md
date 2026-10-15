The exact 695-row joint-capture source passes the full two-SRAM reference miter
(all initialized rows, 4096 randomized operations, masked writes, read-before-write,
reset preserving SRAM). Capture bypass and input-bit corruption mutants reject.
The actual hybrid-CTS gate failed because the hard child u_ctrl/clk no longer had
one direct top source after CTS. The preserved log is authoritative. This variant
is not routed or selected for adoption. No clock-ownership guard was relaxed.

The direct nine-root successor hardens all existing register stages together,
with seven real local CTS roots and two direct raw-SRAM entries. It removes the
additional hard register boundaries while keeping the exact original bank RTL,
four bank edges, SRAM count and all max/min path checks. The earlier positive and
mutant proofs for that RTL remain authoritative. Full routed/native bank evidence
and global M6/M7 capacity are still required before source-parent adoption.
