# qkd_kvs_hroot_s32v4b -- parallel fallback of qkd_kvs_hroot_s32v4 (KV-RST3 2026-10-20)

Identical to s32v4 except OT_HROOT_FENCE_HALF_UM=45: 90 x 90 um centre fence (util ~28 %, less boundary congestion);
worst stage L1 = 390.24 um < 405. Bind whichever of s32v4 / s32v4b closes first under the checklist; cancel the loser.

## SAFE-DESIGN checklist (pre-gate)
1. Pins: PASS. Every data pin captured / launched in RTL (pin anchors), reset_landing 2 stages at the W face.
2. Reach: FIXED (structural). Stages are face -> centre -> face; worst face point to far fence corner L1 = 390.24 um < 405 (90 x 90 fence).
   Post-gate audit owed: results/rtl/kv_hroot_safe32_1020/placed_reach_union.py on the gate CTS ODB must show max <= 405.
3. Fanout: PASS. Netlist identical to s32v3: actual ASAP7 BUF/INV terminal census max 30, 0 role errors
   (results/rtl/kv_hroot_safe32_1020/v3_native_terminal_census.json); POST_SYNTH asserts every non-clock net <= 32.
4. Depth: PASS. 123.4 ps textbook depth, no comb pin->pin.
5. Storage: PASS (with reason). No runtime-indexed storage. The 3 relay words (capture/mid/launch, 777 bits) are a spatial
   relay -- each stage sits at a different place (N face, centre, E/S face) -- not a delay line in one spot.
6. Floorplan: PASS. No macros, full std-cell rows, square, pin-limited outline (N 5.29 / S 5.06 pins/um); centre fence
   s32v3 mapped area 2265.9 um2 / 8100 = 28.0 %.
7. Clock: W-face root as s32v3 (s32v3 gate spread 62.5 / 61.9 ps TT/FF); hold margins 0.03; spread must be re-measured.
8. Schedule: static. HROOT_LAND_EDGES = 2 (+1 vs old landed k1) on each of the four word chains (es head h->o_pc, fan
   i_ctl->o_c*/o_kg/o_ch0, gather i_g->o_ctl, PC31 return i_r->o_emb); reset release +1 matched edge. No change vs s32v3.

## Reset protocol (settled from the RTL, KV-RST3)
Fully synchronous, sampled, fixed latency -- the same contract as every reset_landing tile (ot_pin_regs.tcl: plain
posedge registers rst_n__ot_rl0 -> rl1) and as the old core: rst_n -> rl0 -> rl1 (face landing, 2) -> rst_root[c] (1)
-> region rn (1) -> async-clear pin of q. rn is a register output, so the async clear only ever changes right after a
clock edge: assertion AND release both take 4 edges from the port, sub-cycle pulses are ignored (offphase witness: 104
short pulses ignored by old and new, 41 held assertions match, tb_offphase.sv). Production obligation: the die reset
source holds rst_n asserted >= 1 full cycle before the HROOT flushes (die reset controller holds hundreds; RST_HOLD=273),
and the startup calendar counts HROOT reset release = 4 edges (2 landing + 2 core; s32v3 identical; old k1 view
= 1 edge, rs_q only, no face landing -> +3 edges once at reset vs the k1 binding). No asynchronous
assertion is required or provided anywhere on the KV die (static schedule, regional landed resets).
