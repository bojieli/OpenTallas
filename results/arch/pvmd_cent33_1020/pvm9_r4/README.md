# PVM9 r4 (HBM-PVM9 10-20) — per-lane valid/operand stage + lane reset leaves + 16 lane fences

Why: r3 (smatt6_r3) GPL RSZ-3006 — one `ov` register drove valid_in of all 16 dont-touch kernels, and rst_core_n[1+l/4]
spanned 4 lanes; those die-spanning nets ended on protected kernel pins and could not be buffered.
Source 5d4cc226a (branch claude/hbm-pvm9-lane-1020 from claude/hbm-pvm-smatt6-1020 97c8d4df9):
- core: kept per-lane `ot_pvm_lane_operand` u_opr (oa/ob 64 bits + own valid copy ov_l[l], same D mv / same edge as the
  former shared ov, async reset by the lane leaf) beside each kernel; kernels reset by rst_lane_n[l].
- wrapper: 16 third-level leaves g_reset_lane[l] (same release edge as every core group); groups 1-4 alias lane leaves
  0/4/8/12 (no dead leaf, no tie); second-level loads 29/28/27/27/28/27/28/26 <= 32. Parent-facing ports unchanged.
- delta: +16 lane leaves +15 valid flops -4 group leaves = +27 flops; +0 data/schedule/reset-release edges.
Benches (pvm9_bench/, Verilator 5.050, ot-epyc7): exact 240 chk/601 edges PASS, stopclk+XRAND 666 PASS, reassert1 PASS,
tight 192 PASS, legacy FAN32=0 PASS; new per-lane observer (every lane ov_l and adder valid_out == reference ov / valid at
+1 age; 597..652 lane edges). Mutants FAIL: MUT4 data, MUT14 async-only status (STOPCLK 65 ns), MUT15 lane-9 valid one
edge late (LANE_VALID_AGE_MISMATCH 47 ns), MUT16 lane leaf 9 synchronous (STOPCLK_RESET_NOT_PROPAGATED 65 ns).
Fences (physical/ref_tile/pvm_bindfirst_private/stages/pvm9_lane_fences.tcl, PRE_GLOBAL_PLACE): EXCLUSIVE region+group
23.76x34.56 per lane = kernel 3500 + u_opr + leaf; lanes 0-7 E band x 272.16/300.24 y 64.8..203.04 (their rd_out + wd_in
face), lanes 8-15 W band x 49.68/21.6 y 112.32..250.56 (their wd_in face).  Util check <= 0.70 in the hook.
Run r4 (ot-epyc6 /srv/opentallas-scratch/claude/pvm9-r4-1020, run_r4.py): original synth -> bind-first synth + native32 ->
bind-first transaction + persisted audit + fence dry run -> floorplan..GRT, PNGs, kernel_input_nets, post-GRT PG + native32.
Known residual: the global TIEHI _18312_ still feeds 112 kernel SETN pins across all lanes (reviewed tie-detach); if GPL
names it next, the kernel native needs per-kernel tie cells (native graph change).
