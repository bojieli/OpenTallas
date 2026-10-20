# qfd_n59_svc4 (QW-N59SVC, 10-20) -- svc3 + register-stage reach relocation (0 added cycles)

RTL, params, outline, pins, census, benches and mutants are IDENTICAL to qfd_n59_svc3 (R3k 107de9c40; README below).
Change: PRE_DETAIL_PLACE hook physical/qwen_die_masters/reach_reloc.tcl (+ reach_reloc.py): after global placement the
actual Liberty stage graph is built (every combinational function collapsed FF/macro/port -> FF/macro/port, clock pins
excluded, async reset pins kept) and every register whose longest stage endpoint span exceeds 390 um is moved to the L1
minimax centre of its stage neighbours (coordinate descent, 8 passes); DPL legalises.  Residual spans > 405 um FAIL the
flow (OT_REACH_RELOC_STRICT default 1), so a gate PASS implies 0 stage spans > 405 um at placement.
Offline proof on the svc3 3_5 ODB (qfd_n59_svc3-20261020-065454, same netlist): 284 spans > 405 -> 0 (279 registers
moved: rx pin regs -> mid-span hop toward the record codec, p_esq / p_ecq relays, dvf / fault, rq_c copies, reset rlv / cp
relays).  Final-ODB re-audit with results/arch/qw_n59_svc_stage_geometry_0720/stage_graph.py is owed before submit.

## Reach (checklist item 2) -- FIXED: forwarded hops on existing registers; schedule unchanged (SOFF3 / BOFF0 / ROFF4, 0 edges,
price 0).  Pin registers that moved off their pin leave an unregistered pin -> register wire inside the tile (<= ~250 um);
boundary timing is checked by the gate at 833 ps.  Census numbers unchanged (same RTL / mapped netlist as svc3).

# qfd_n59_svc3 (QW-N59-6 v3, 10-20) -- service child of the hardened native59 split (Q.STA.N59)

RTL: rtl/qwen_split/qfd_native59_svc.sv at R3k 107de9c40 (branch claude/qw-n59-svc-r3d-1020) = svc2 + RECV_INPUTS=1 +
LOCAL32=1 with the R3c..R3k same-edge publications (kept same-D copies of the pin / face registers, per-consumer begin /
request / beat publications, registered one-hot seat hits in the KV formatter, <= 16 enable bits per publication, a
native59-local codec copy exporting kept tx_valid copies).  0 added edges vs svc2 (SOFF3 / BOFF0 / ROFF4 unchanged).
Kit = qfd_n59_svc2 + PARAMS RECV_INPUTS=1 LOCAL32=1 + io_hold_margin 0.03.  Kit _b = unclustered H-tree CTS, -no_obstruction_aware (parallel fallback).
Output-exact (not register-exact) points, each verified by the lockstep benches: KV formatter word_data capture without
!fault / !err in its DATA enable (word_v and every KVN control publication keep them; the KVN seat captures word_data only
under word_v) and the seen-clear on its eb_r copy (a begin that fails eb_clear_ok makes the formatter fault sticky first).

## PRE-GATE NATIVE CENSUS (mapped netlist, strict refuse, hf 32 data AND reset, BUF/INV transparent)
* drivers > 32 loads (data AND reset, BUF/INV transparent): 0 (refusing checks: none; WARN only the clock-root guidance).
* 21,950 FF, 94,014 cells, 0 macros; lint depth 393.4 ps; tied output bits 0; flop families > 2048: 0.
* KVN target audit: 1523 nets, max 26, 0 offenders.  Pins: input landing g_recv + p_* (RECV_INPUTS=1).
* Mapped SHA ed914b2bd64177bfc64f5e51ee644993aaabbe3a7378b05a330ee7833dfa5806 (receipts r3k/receipts/synth_recv).
* Reach 405 um: not provable from synthesis; measured on this gate layout.
History (results/arch/qw_n59_service_r3_1020/r3c..r3k receipts): R3c 275 > 32 / max 528 -> R3d 430 / 216 -> R3e 453 / 368
-> R3f 75 / 122 -> R3g 71 / 58 -> R3h 14 / 48 -> R3i 2 / 48 -> R3j 1 / 39 -> R3k (above).

## Benches (Verilator 5.050, results/arch/qw_n59v6_service_1020/bench.sh legs)
default_rnd, local_rnd, local_reset8, local_mu (2458-edge lockstep, 4 users), local_dv (360-edge lockstep, 33 tx / 32 ar
bit-exact), component (KVN): all PASS at every round R3d..R3k.  Causal mutants (fail regex 'N59(DV|MU)_FAIL' in
out/wrapper.log, local_dv): ht0 (lane-0 seat hits off), cq0 (word_data group 0 slot copy off), bpub0 (service begin group 0
off), optag0 (s_optag quarter 0 off), emc0 (landing decode beat copy off), ddc0 (lane-0 dd copy off), qo0 (q_frame_tag
quarter 0 off), eba (formatter pos copy off), wac0 (formatter decode group 0 off): all REJECTED.  txvb (native_tx header
copy off) is caught by local_mu (REJECTED) but not by local_dv / local_rnd (header unobserved there): coverage note.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input lands in a g_recv face register then a p_* pin register (RECV_INPUTS=1); outputs are flops
  except the r1 2-slot AND-OR of slot flops (native_tx / completed, unchanged); rst_n 2 landing stages x 32 copies + the
  kept reset forest (fmt 288 / pin 128 / top 64 / svc 104 / rec 80 / land 56 / x3 80 / ctx 12 under LOCAL32).
2 Reach: PASS by construction -- 518.4 x 216 (svc2 outline / pins); measured on the CTS gate layout.
3 Fanout: FIXED in v3 -- strict census above (R3c 275 drivers > 32 -> 0).
4 Depth: PASS -- census lint depth 393.4 ps; every added copy is a same-edge register or a <= 3-level gate.
5 Storage: PASS -- no SRAM; formatter seat hits 2 kb of registered one-hot hits (pipeline registers, not a runtime-indexed
  array); no runtime-indexed flop array > 2 kb.  (Inherited LAND_EDGES 8 tag_pipe shift line stays a recorded RULEBLOCK item.)
6 Floorplan: PASS -- std-cell only, pin-bound, 518.4 x 216 (slot width; pin faces need it), full-width rows; FF count
  21.9k (svc2 19.4k).
7 Clock: one root ck at the N-face centre, own region in the landed parent (ck_svc); io_hold_margin 0.03 (svc2 0.0);
  rule = pin-flop spread <= 80 at TT and FF, measured by this gate.
8 Schedule: static; 0 added edges vs svc2 (all R3 copies are same-edge).
