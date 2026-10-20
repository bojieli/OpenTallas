# qfd_dv_s5_vm8c -- slice2 VM hardened block, single root, full W/E std-cell bands (QW-SUVM9, Q.STA.SLICE.2)

Successor of the VM half of qfd_dv_s5_suvm7 / suvm7b (claude/qw-slice6-suvm-1019 03ba379bf), whose gates were classified
FAIL: one 9.7k-flop root over 480 x 687 um, boundary pin-flop spread TT 217 / FF 201 (7b 381 / 337) ps, placement
reg->macro -519 (r_ce collision compare), in->macro -406 (tw_data -> PROG wd), reg->out -429 (cr_q extraction), depth
763 ps / 21 lv (SU lane address adders), 15 abutted macro channels < 20 um.  The SU issue control becomes a separate leaf
(next step), the slice2 parent lands the crossings.

RTL `rtl/qwen_dv/s5/qfd_dv_s5_vm8.sv` (qfd_dv_s5_vm8 = 3 clock ports; qfd_dv_s5_vm8s = single-root wrapper), generator
`tools/qwen_dv/s5_vm8_kit.py h|b`.  main qfd_dv_s5_vm8h = three regional related CTS roots (ck_wr S band, ck_rd W face +
VM/CROM logic, ck_su E face + PROG/BTAB logic) + 18 raw SRAM clock entries ckm0..17 (hybrid_entries; die delivers each
macro clock compensated); parallel fallback qfd_dv_s5_vm8b = same RTL via qfd_dv_s5_vm8s, one S-centre root.
Gate history (results/arch/qw_suvm8_1020/vm8/gate_054252_fail): r1 vm8 (multiple_cts_roots) FAIL at CTS -- OT_HYBRID
"CTS source ck_rd must reach only standard-cell clock pins" (SRAM clocks need raw entries) -> vm8h; r1 vm8b FAIL in-flow
native census: one vm_waddr[22] pin register 41 loads (flow ABC re-shared the window decode) -> 6 kept pin-register copies
of {vm_we, vm_waddr[23:22]}.

## Structure
- every input lands in a pin register, every output leaves one (no in->macro / macro->out / pin arc); rst_n rl0 -> rl1.
- VM write merge = vm7's landing decode (kept per-(bank, slot) one-hot registers) followed by a REGISTERED write stage per
  (replica, bank) beside each macro (wd / row / we / per-slot mask); the read-collision term compares two registers.
- table writes tw_* land twice (pin register, then one kept copy per macro group CROM | PROG + BTAB).
- read answers: capture flops at the macro read face -> kept one-hot bank / lane-offset selects -> answer pin register.

## PRICE (static schedule; NOTICE QW-GEN / TOKSIM-QW / slice2 parent)
reads (VM a/b/c, CROM, BTAB, PROG): answer 2 -> 4 edges (+2); VM writes (lane window 00, w16, w1): +3 vs qfd_dv_s5_suvm
(+2 vs suvm7), write -> read distance 1 -> 3; table writes tw_*: +2, table write -> read distance 1 -> 2; fault +1.

## Pre-gate native census (ASAP7 RVT TT mapped, macros blackbox; suvm7/native.sh in openroad/orfs:asap7lock, fleet ep7)
vm8 : 0 drivers > 32 (raw ports + reset included), max 32; rst_n 2 loads; 15,086 FF; roots ck_rd 8,077 FF, ck_su 3,850,
      ck_wr 3,159, ckm0..17 one macro each; depth 286.7 ps / 8 lv; in->out 0, in->reg 0 lv,
      reg->out 0 lv.  results/arch/qw_suvm8_1020/vm8/native_qfd_dv_s5_vm8/census.json (mapped SHA256 88900e4f44a01142...).
vm8s: same, one root 15,086 FF + 18 macros, depth 250.1 ps (native_qfd_dv_s5_vm8s, SHA256 e20676ca83f4dfc9...).

## Benches (Verilator 5.050, fleet; rtl/test/qwen_dv/s5/vm8/bench.sh)
vm8_eq: lockstep vs qfd_dv_s5_vm7 fed reads +1 / VM writes +2 / tw +2, every output +1, 60,000 cycles, random resets,
biased rows (RAW, same-cycle collisions, slot conflicts), random tables/programs: 59,620 compares, 0 mismatches PASS.
Mutants FAIL with committed witnesses results/arch/qw_suvm8_1020/vm8/bench/run_{coll,wpri,bsel}.log: coll (collision
suppression removed) 12,357 mismatches; wpri (earlier lane wins the slot); bsel (b answered from replica c) 53,333.

## SAFE-DESIGN checklist
1 Pins PASS (RTL pin registers both faces, reset 2-stage); 2 Reach PASS by floorplan (VM rows 0-2 <= 381 um from the S
band, table writes landed twice, read faces <= 259 / 216 um from their pins; gate checks 405); 3 Fanout PASS (census 0>32);
4 Depth PASS (287 ps / 8 lv); 5 Storage PASS (18 SRAM macros); 6 Floorplan PASS (x on 43.2, y on 8.64 lattice, every macro
channel >= 20 um, no abutted stacks, full-width S band 86.4, aspect 1.07, pins W 3.2 / E 1.2 / S 3.0 per um);
7 Clock: a three regional related roots (ck_rd 8,077 FF just above the 8k span WARN), b one root (fallback); judged on
pin-flop spread <= 80 TT+FF; io_hold_margin 0.03; 8 Schedule static, edges priced above.

## QW-SUVM9 vm8c (successor of vm8b r2; same RTL 2ef848421 qfd_dv_s5_vm8s, same native census, same benches)
vm8b r2 CTS (ep9 ref_gate/qfd_dv_s5_vm8b-20261020-070801, 4_1_cts.odb, placement parasitics): boundary 4,894 FF TT
726.9..827.2 (spread 100.3) / FF 595.4..683.7 (88.3) > 80 -> clock rule FAIL.  Per-sink dump (results/arch/qw_suvm8_1020/
suvm9/vm8b_ck_tt_sinks.txt): faces S 726.9..788.6 (2,136), W 731.0..764.7 (2,010), E 731.6..827.2 (748); every sink
> 785 ps is an E-face p_q (215) / ptw_data (32) pin register in the 43.2 um strip beside the PROG column.  Trace of
p_q[401]: level-8 tap clkbuf_8_188 legalised to (559, 221) inside the 28 um PROG channel, then a 110 um wire hop + leaf
(+107 ps vs a normal ~30 ps leaf).  Structural fix (checklist 6/7): full-height W and E std-cell bands 86.4 um (like the
S band): columns 86.4 / 302.4 / 518.4, outline 777.6 x 648 (aspect 1.20, +0.056 mm2), so the tree taps of every face
register mass land beside it.  
Checklist: 1 PASS, 2 PASS (read faces <= 302 / 259 um), 3 PASS (census vm8s 0 > 32, max 32, unchanged RTL), 4 PASS (250 ps
/ 8 lv), 5 PASS, 6 PASS (bands 86.4 W/E/S, 43.2 lattice, channels >= 20 um), 7 single root, judged TT+FF <= 80, 8 PASS
(no schedule change vs vm8b: price table above).
