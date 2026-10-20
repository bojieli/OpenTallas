# qfd_tile_nk_romleaf_rc4b — QW-A0-RC3 rc4b (10-19)

rc4b = rc3 channels/fences + a SQUARE-ISH hub fence 377.4-457.4 x 316-426 (80x110) + FREE land_top (u_g.u_tile.n_va / fault_q).
rc3 results (results/arch/qwen_a0_cluster3_1019/gate_failures/rc3_summary.txt): the free lanes fixed DPL-0033 (NL DPL PASS;
NK 8061 -> 1 stuck cell, the n_va pin-side flop that the hub regex claimed), but one ck H-tree over the tall narrow hub
(NL 44x845 -> 193.3 ps, 50x475 -> 147.6 ps) failed the 80 ps spread rule. A hub of <= 2:1 aspect gives a balanced H-tree.


CRITICAL prefix: gate PNGs + this checklist are reviewed via COORD-REVIEW-QUEUE; no REVIEW.json or submit by the lane.
Generator: `tools/qwen_romleaf/rc3/gen_rc3.py` (macros, pins, RTL REGROOT 7 identical to rc2). Pre-gate area/lane check:
`tools/qwen_romleaf/rc3/check_region_area.py` -> results/arch/qwen_a0_cluster3_1019/rc3/region_area_check.txt (rc2 FAILS it:
corridor free rows 0.11/0.27/0.12; rc3 PASS).

Why rc1/rc2 failed DPL-0033 (NL 1726 / NK 8061 stuck cells): the EXCLUSIVE fences tiled the west channel, the east channel
and the central column wall to wall. Only registers are group members, so the comb cones, the repair_design wire/slew
buffers and (NK) the n_a/n_b/n_y bus buffers had no legal rows near their drivers. Fence fill was only 3-8 %: area was
never the problem, the missing free lane was.
rc3 fix (structural, 0 cycles): every fence is a pin-side sub-lane (rsw/dw/rnw 216.4-231.6 beside the ROM0 pins; rse/de/rne
589.6-604.4 beside the ROM1 pins; tx0-3 359.4-373.8 at the LSLA pin face; tx4-7 460.8-474.8 at the LSLB pin face; hub fence 395-439 (NL full height 8-853.2; NK 8-426 under the node)),
and every corridor keeps >= 49 % free rows next to its fences (west 0.68, centre 0.49-0.66, east 0.55).
Outline is unchanged (820.8 x 907.2): reach plan node 388.8 um from the W pins and hub <= 385 um from the E tap pins.
A hub across the bottom band was rejected: hub copies feed ROM request relays up to y 860 and LSL rows up to y 788
(650-800 um > 405 reach).

## Safe-design checklist (pre-gate; gate facts are added from the gate PNG/json)
1. Pins — PASS (native): the RTL registers every data pin at its face (tap/tile_id on ck_fa4, n_a/n_b on ck_fa0/1,
   t_out/n_y launched on ck_fa2/3; spec pin_regs opt-out reason kept). Reset — FIXED: ref_tile `reset_landing` 2 stages
   on ck_fa4, last stage 8 KEPT copies spread by `reset_relay_split` max 32 loads; the single native `reset_q` sample
   (1 flop -> 104 loads in c1r9f) is not built under REGROOT 6.
2. Reach — FIXED by floorplan: n_a/n_b/n_y W pins -> node W face 388.8 um; tap E pins -> hub box <= 384 um; LSL 0..7 ->
   node <= ~250 um (node beside LSL rows 2/3, rows 0/1 below); ROM rnw -> dw adjacent in one channel. ROM -> LSL operand
   path keeps its existing landed rungs (XTX 2, ROM ARELAY 2). The approved +1 relays (NK lsl7->node, NL rnw->dw) are
   NOT needed in this floorplan (0 cycles). Gate wire_reach must confirm.
3. Fanout — FIXED in RTL (REGROOT 6, 0 cycles, same values on the same edges): split_r[3:0] -> 27 per-destination kept
   4-bit copies (round-step shifter halves, pr_a/kpad_a, kc_a, KV q/c per group, K-limit per group, e_split); wsrc_r -> 3
   copies; active/pend/j_last/k_last/t_last -> one kept copy set per loop address field group (cur, base_k, base_t, oa, ot,
   nb, nb_t, lb, wrom_addr); active -> 5 more (kv_addr groups, e_v/progress/idle); k_last -> 1 (tags). Every canonical
   next-state net drives <= 29 copy D pins. Mapped census (actual <=32 per register) is read from the gate 1_synth.odb.
4. Depth — unchanged logic; gate textbook depth reported.
5. Storage — unchanged (ROM macros; no new runtime-indexed flop arrays; copies are 1-4 bit registers).
6. Floorplan — FIXED: outline 820.8 x 907.2 um (19 x 21 lattice cells), aspect 1.105; every hard-child origin on the
   43.2 um lattice; channels >= 29.8 um; ROM rows on a 172.8 um pitch (62.6 um std rows); full-width std rows (41 um
   bottom band, 60.5 um top band, ROM-row channels); macro fill 323.0k / 744.6k um2 = 43.4 % (+ std ~9k -> ~44.6 %,
   inside 40-60 %); pins on full W/E faces at 0.192 um = 5.2 pins/um (tap was 0.096 um = 10.4/um in c1).
7. Clock — regional roots as c1 (ck, ck_rs/rn, rsw/rnw, dw/de, tx0..7, fa0..4) + hard-child entries; route
   hold_margin_ns 0.03. Pin-flop spread <= 80 ps TT/FF: from the gate CTS.
8. Schedule — static; data path +0 edges (copies); reset release +1 boot edge (2 kit landing stages replace 1 native
   stage: a scheduled constant, no token cost); REGROOT 5 output landing +1 data edge as already priced (XTD + 1).

Numerical: `tools/qwen_a0_safe/run_rr6.sh` (full 64-MAC / ten 4096x266 ROM / eight LSL + node native bench vs the
qfd_tile_nk_rp1 reference): positive PASS checks6399 valids2560 nonzero2560; MUT40 (wrom_addr copy) FAIL errors6247,
MUT41 (cur k_last copy) FAIL errors6089 (results/arch/qwen_a0_cluster3_1019/bench_rr6_run*).
Slot: die slot changes 457.92 x 1166.4 -> 820.8 x 907.2 (slot_change_request); die re-plan before adoption.
