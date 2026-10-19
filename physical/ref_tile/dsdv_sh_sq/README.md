# dsdv_sh_sq -- S81 seq_host L1 sequencer leaf (S81-SAFE-FIX/SH 10-19)

Safe redesign after the exact gate @2fa5f8e9c failed trial GRT (overflow 285,158, M2 106 % used at util 48 %): the
calendar issuer is now `ot_dsdv_walk_issue` (an ordered walker over two SRAM copies) instead of `ot_dsdv_fixed_issue`
(9.7 kb flop calendar compared row-parallel every edge).  Branch `claude/s81sf-sh-1019`.

Gate 2 @76c2e0092 (`--remote auto --cts`): PASS 0 fail / 0 warn.  Trial GRT overflow 0 (M3 24.1 %), depth 461.8 ps,
6,009 flops, reg->reg +73.5 ps, reg->macro +82.0, hold +39.1 (TT placement RC), one root `ck` 6,011 sinks, insertion TT
290.8 / FF 244.6, pin-flop spread TT 47.6 / FF 45.6.  cts_native_probe: launch 163.7 ps (rn_o[16]) / capture 109.1 ps
(jd_i[0]), diagnostic PASS (`results/rtl/s81sf_sh_1019/gate_sq2/cts_probe`).  Gate 1 (@94902a8a0, evidence
`results/rtl/s81sf_sh_1019/gate_sq1`) failed on pin-flop spread TT 84.0 and macro->reg -62.5 ps; both fixed structurally
(lk single-root CTS clustering; SRAM output feeds only a next-word register).

Benches (Verilator 5.050, fleet): `run_seq_host_bench.sh` 4 seeds + 4 two-rows-an-edge seeds lock-step vs
`ot_s81_fixed_issue` PASS, collide / stdrop faults raised, mutants 1-10 FAIL (10 = unsorted calendar refused at seal);
witnesses `results/rtl/s81sf_sh_1019/seqhost`.  Compiled L14 programme (113 rows, 28 two-row edges) `SEQHOST_PROG PASS`
on this RTL (`results/rtl/s81sf_sh_1019/prog_L14`).

Calendar contract (compiler `tools/s81_dv/dv_layer_compile.py` `finish()`, seal scan code 3): issue non-decreasing, at
most two rows an edge on different engines, per-engine done strictly increasing, <= 8 commands of an engine outstanding
per context.  Edges are those of `ot_s81_fixed_issue` for every contract calendar.  Added cycles: 0 data edges; reset
release +2 (reset_landing); seal +1 boot edge (handed to MU-DIE-S81 INBOX).

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|------|--------|
| 1 | pin registers + reset landing | PASS: every input lands in a flop at the pin, every output leaves a flop (source-registered; recipe pin_regs opted out with that reason); reset_landing 2 stages on rst_n (fixed) |
| 2 | reach <= 405 um | PASS: tile 254.88 x 151.2; textbook reach 77.4 um; rung hop rn_i -> rn_o launch 163.7 ps |
| 3 | fanout <= ~32 in critical cones | PASS: the 128-row compare fan-out is gone (one 24-b compare per row slot, 2 per context); textbook lint PASS |
| 4 | depth <= 600 ps / ~20 levels | PASS: 461.8 ps; SRAM output -> register only; seal-scan row registered |
| 5 | storage > 2 kb in SRAM | fixed: calendar 128 x 76 b in 2 x ot_sram_1r1w_128x256 (row pairs); completion FIFOs 8 x 8 x 31 b flop ring buffers (8-entry, head read only) |
| 6 | floorplan | macros x 129.6 (43.2 lattice), y 23.76 / 86.4 (y 23.76 off the 43.2 lattice: the 20-um pin-face rule from the core edge), pins face W toward the logic, 21.6-um channel; pins N 1,296 / S 1,207 = 5.1 / 4.7 per um over full faces; aspect 1.69; one contiguous std-cell band. Util WAIVED: std 3,626 + SRAM 7,788 um2 = 31 % fill -- pin-bound (2,505 N/S pins need the 254.88 width) and macro-bound (stacked SRAMs need H >= 146); smaller breaks aspect <= 2; height = dsdv_sh_lk (regular stack) |
| 7 | clock | PASS: one root ck at the E mid (macro channel, beside the logic mass), pin-flop spread TT 47.6 / FF 45.6; io_hold_margin 0.03 (fixed) |
| 8 | static schedule | PASS: no credits / backpressure; calendar contract enforced by the compiler and the seal scan; added cycles handed to MU-DIE-S81 |
