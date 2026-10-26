# qkd_hr_core_guard_frc -- MU1 guard, SRAM marker FIFO, SAFE item-3 head-select fix (fallback kit of mu1s)

Owner lane: KV-HOST2 (LEAD2-KV), kit/source by KV-HOST/GUARD (`claude/kv-host-guard-frc-1019`, gate source a5201f50f).
Parent `qkd_host_root` is CRITICAL and untouched (report-only).

* RTL = mu1s (`qkd_hr_core_guard`, MU1 core `qkd_host_native_token_endpoint_cancel_mu`, W64 x 128 marker FIFO on one
  real `ot_sram_1r1w_128x64_m1_p192`) + head-buffer read select `fr` replicated as 8 KEPT copies, one per 8-bit dout
  slice (was one 305-load select).  Same outline / macro slot as mu1s (108 x 140.4 um, macro at 43.2/43.2).
* Benches (Verilator 5.050 fleet, source a5201f50f; results/rtl/kv_host_guard_1019/frc_bench + runs_guard2):
  MU1 lint + tb_mu_hroot_e2e PASS, ep1/ep2 mutants FAIL (witnesses committed); SRAM lint PASS; guard FIFO exact m0
  PASS 100,140 cycles; m1/m2/m3 mutants FAIL (witnesses committed).
* CTS gate (a5201f50f, ot-agidock128 `ref_gate/qkd_hr_core_guard_frc-20261019-122000`): PASS 0 fail 0 warn;
  reg->reg +64.4 ps, hold +37.3 ps; TT/FF insertion 239.3/199.7, pin-flop spread 29.2/29.2 ps; 6,201 sinks;
  trial GRT overflow 0 (M2 24.6 %).

## Reconciliation with the die-selected guard (KV-HOST2 10-19)
The frozen die (5f2ce19bc gen8v3mub, HOST_MU0) still selects the legacy MU0 guard whose marker FIFO is an 8192-bit
runtime-indexed flop array (SAFE item 5 FAIL, Codex model 579134a33 "old guard579 snapshot vs selected 8192b").  This
kit is the replacement: same ports as the MU1 guard view, marker storage in SRAM, exactness by the guard-FIFO m0
bench against the reference FIFO.  Adoption = KV-GEN9 selects this view (or mu1s, whichever closes first) for
`u_rank__u_guard` together with the MU1 host core (K.STA.MU); the MU0 8192b guard is diagnostic only.

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|------|--------|
| 1 | pins | PASS: pin regs on all data pins (58 in / 20 out, +1 edge each); reset lands in 2 stages; no comb in->out |
| 2 | reach | PASS: 108 x 140.4 um tile, corner-to-corner 248.4 um < 405 |
| 3 | fanout | FIXED head select (8 KEPT fr copies). WAIVED rest: Codex all-root census (579134a33) lists 155 roots > 32 (62 FF max 223, 93 comb max 338). All are local (tile <= 248 um reach), none in a failing cone: CTS reg->reg worst +64.4 ps on `quiet[4]`. Reset: 18 KEPT host_rst_n copies, relay split 256 |
| 4 | depth | PASS: textbook depth 441.8 ps |
| 5 | storage | FIXED: 8192 b marker FIFO -> one 128x64 SRAM; remaining arrays < 2 kb |
| 6 | floorplan | PASS (util waived, pin-bound): macro on the 43.2 lattice, channels >= 31 um, face pins <= 5.6/um; util 30 % synth; full-width std-cell bands, no islands |
| 7 | clock | PASS: one ck_core root on the W face beside the register mass, spread 29.2/29.2 ps TT/FF, io_hold_margin 0.03 |
| 8 | schedule | PASS: static, 0 added cycles vs mu1s (fr copies are same-cycle replicas) |

Visual review (KV-HOST2, 10-19 16:50): floorplan.png/density.png inspected -- std cells occupy the left two thirds
full height around the macro (continuous, no islands), red only in the W pin-flop column; right third sparse (E IO
flop column); clock pin W face lower third next to the register mass; macro centred on the lattice.
