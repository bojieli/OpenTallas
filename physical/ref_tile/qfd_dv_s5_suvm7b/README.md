# qfd_dv_s5_suvm7 / qfd_dv_s5_suvm7b -- SAFE successor of the slice2 SU issue control + VM leaf (QW-SLICE7-LEAVES/SUVM, Q.STA.SLICE.2)

Predecessor qfd_dv_s5_suvm / suvmb (375403eb0) was never gated: its pre-gate ASAP7 mapped native census FAILED
(211 non-clock drivers > 32, 107 flops, 2 raw ports, max 1150 = su_go accept enable; VM stage-2 read selects 1024/512/256;
raw w16_we 651 / vm_waddr[3] 254). Evidence results/arch/qw_slice7_1020/suvm7/native_orig/census.json.
Same outlines / macro stacks / faces as the predecessor (generator tools/qwen_dv/s5_suvm7_kit.py a|b):
main qfd_dv_s5_suvm7 483.84 x 691.2 (2 abutted macro columns), parallel fallback qfd_dv_s5_suvm7b 691.2 x 561.6 (3 columns).

RTL: `rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv` (qfd_dv_s5_suvm7 + qfd_dv_s5_vm7 + kept helpers qfd_dv_s7_kff/kffr), same ports as
qfd_dv_s5_suvm (drop-in by module name in the slice2 parent; HARD 1 only).

## Structure (what changed)
- Reset: rst_n -> rs1 -> 6 kept rs2 replicas -> 10 kept rc replicas, each <= 32 async pins; same assertion/release edges.
- Issue loop: accept (su_go), active, v_last_r are kept replica flops capturing ONE shared next-state net; each enables
  one 12-bit field chunk (31 accept-only chunks + 23 stepping chunks). 0 edges.
- VM reads: capture flops at the macro pins kept (macro clk->q ~550 ps of 770 ps); stage-2 bank / lane-offset selects are
  kept replicas decoded one-hot, <= 16 bits per copy. 0 edges.
- VM writes (su lane window 00, w16, w1): LANDED (+1 edge); merge controls decoded from the raw pins into kept
  per-(bank, 32-b slot) one-hot lane / w16 / w1 / mask registers; mask replicated per VM replica.
- Table writes tw_* and every read answer: edge-for-edge qfd_dv_s5_suvm.

## PRICE (NOTICE QW-SLICE7 / QW-GRT4 / QW-GEN3 / TOKSIM-QW2)
+1 edge on VM write visibility (lane writes window 00, ctl w16 / w1): a VM read of a row written <= 1 cycle earlier is
now a collision (schedule write->read distance 1 -> 2); su_idle and vm_fault see the write bundle one edge later.
0 edges on every read answer (VM 2 edges, CROM 2, BTAB 2, PROG 2), gb/gv/lv1/pd1, su_nr, su_prog/rows, reset.

## Pre-gate native census (ASAP7 RVT TT mapped, macros blackbox; rtl/test/qwen_dv/s5/suvm7/native.sh, fleet ep7)
0 non-clock drivers > 32 (raw ports + reset included), max 32; rst_n 7 loads (2-stage landing); 8,655 FF, 18 SRAM macros;
std area 4,766.8 um2 (predecessor 4,564.2 um2 / ~6,700 FF: +4.4 % area for replicas + 830 b write landing);
TT stage estimate 590.1 ps / 18 levels; in->out 0 bits; reg->out 5 levels (read extraction mux, as predecessor);
in->reg 12 levels (sticky read-address fault check bad_vec, status only). Mapped SHA256
63549a3b61cb7fe5b1c19b1f432948763dbb91201fe524e6cae972552cec9015 (results/arch/qw_slice7_1020/suvm7/native/).

## Benches (Verilator 5.050, fleet; rtl/test/qwen_dv/s5/suvm7/bench.sh)
suvm7_eq: lockstep vs qfd_dv_s5_suvm HARD 1 fed with the write bundle one cycle late, every output every cycle, 40,000
cycles, random mid-run resets, biased rows (RAW / collisions / slot conflicts), random programs: 39,929 compares PASS.
suvm7_mut_loff (lane offset twice) FAIL 37,739; suvm7_mut_wpri (earlier lane wins the write slot) FAIL 20,776;
committed witnesses results/arch/qw_slice7_1020/suvm7/bench/run_{loff,wpri}.log.

## SAFE-DESIGN checklist
1 Pins: outputs flop-launched except the VM/CROM answers (capture flop + 2:1 x 8:1 extraction, 5 levels, as predecessor);
  VM write bundle landed in RTL; read requests drive macro pins (macro = input register) + stage-1 flops; rst_n 2-stage.
  WAIVED-with-reason: flow pin regs off (an extra read edge would break the lane round trip ML1/RD2); in->reg 12 lv is the
  sticky address-fault check only.
2 Reach: tile <= 691 um; macros abutted columns, logic in pin channels / S band; gate wire_reach checks 405 um.
3 Fanout: FIXED -- census 0 > 32 (was 211), kept helper hierarchy (keep_hierarchy) prevents merge-back (p1/c1 merged
  copies found and kept in n3).
4 Depth: 590.1 ps / 18 levels TT estimate (<= 600).
5 Storage: all > 2 kb state in 18 SRAM macros; flops are capture / landing / control registers (no runtime-indexed array).
6 Floorplan: macros at_exact on the 43.2 lattice, abutted stacks, pins W/E faces, full-width S band, aspect 1.43 / 1.23.
7 Clock: one centre-fed root from the S-face ck (8,655 sinks); judged on pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: static, no credits / backpressure; +1 VM write edge priced above.
