# s81ctrl_rg3sw: dsfd_ctrl_rg3 wide re-floorplan (S81-COLLECT/RG3 10-21; MU.BAL.SX.3)

Successor of s81ctrl_rg3 / s81ctrl_rg3s after their regate @464c7f801 FAILED CTS (owner rule: structural re-floorplan, no squeeze).
Kit = ref_tile gen of physical/s81_ctrl_rg3/spec_rg3sw.json; same RTL, defines, benches, mutants and witnesses as s81ctrl_rg3.
Failure classified (remote logs ot-epyc5 ref_gate/s81ctrl_rg3{,s}-20261021-04*): 2x2 SRAM plan at 388.8 x 324 left a 29 um N band and a
43 um S band for 3.1k face pins + 4 io-flop columns; GPL routability overflow 36.7% of tiles; hold repair stuck 1,000 iterations
(rg3 k_rdy->krq_c -23.7 ps, rg3s ld[0] -71 ps) with buffers growing, CTS step killed.
New plan: outline 561.6 x 324 (aspect 1.73), two abutted N-S SRAM stacks (one per PC, x 86.4 / 345.6; u_q R0 y 64.8 pins S, u_r MX
y 165.522 pins N, bare touching faces, on track), full-width macro-free bands S 64.8 um / N 57.7 um + 144.7 um centre column.
Pins: N n32s 1,246 = 2.3/um; S 2.3/um; rrq 92 W, rrd 544 E (M4 1.8/um).

SAFE checklist (pre-gate):
1 Pins PASS: RTL face flops (rrq/rrd, PHY k_*/kr_*, svc rq/rd) unchanged; reset_landing 2 stages.
2 Reach PASS (verify post-GRT): half-perimeter 885.6 um; macro-pin to face <= 65 um; centre column for cross-PC glue.
3 Fanout PASS: native census as rg3 (results/rtl/s81_idx4kits_1020/native_ctrl3s; gate mapped census limit32 PASS max 32).
4 Depth PASS: census depth 283-338 ps.
5 Storage PASS: landing FIFO 1,056 b/PC flops; 4 FIFOs SRAM.
6 Floorplan fixed: was FAIL (face bands); macros abutted stack (at_exact on track, 2.16 lattice off by design for the abut),
  faces <= 3.4 pins/um, fill 27% recorded as fill_reason.pin_bound (measured), aspect 1.73, full-width std-cell bands.
7 Clock PASS (re-measure at gate): K8 regional clk roots + hclk split hooks unchanged; io_hold_margin 0.03.
8 Schedule PASS: no added cycles (floorplan only).
Die slot changes from 388.8 x 324 to 561.6 x 324 (LEAD-S81 notified).
