# qkd_kvs_hroot_s32v4 -- SAFE32 HROOT with hard central stage fence (KV-RST3 2026-10-20)

Same RTL (qkd_kvs_hroot_safe32, rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_safe32.sv @ codex/kv-hroot-safe32-1020),
same pins, faces, outline (300.24 square), clock, SDC, POST_SYNTH tie hook and benches as qkd_kvs_hroot_safe32 (s32v3).
One change: `pin_hook_after_flops` = physical/qwen_kv_hroot_safe32_1020/central_fence_s32v4.tcl. After the pin flops and
hold stages are fixed, every other standard cell (intermediate captures cap.dat.q1, region ctl/sid/rn copies, relay *_mid,
head decode) goes into an INCLUSIVE 80 x 80 um region at the tile centre through a group (gpl honours groups).
Port-chain BUF/INV/HB cells, TIE cells and physical cells stay free. Fails closed on implausible classification or >60 %
fence utilisation.

Why: the s32v3 route (qkd_kvs_hroot_safe32-s32v3-e52c7bca5, CLOSED TT +212.5 / FF +18.6) placed the intermediate stage
freely: BUF/INV-traversed endpoint reach 517.2 um, 417 roots > 405 um (403 cap.dat.q0, 13 ctl_root, 1 sid_root;
results/rtl/kv_hroot_safe32_1020/placed_reach_union.json). These are real single-cycle flop->flop wires (N-face capture ->
S-region second capture), so SAFE item 2 FAILS; s32v3 stays diagnostic.

## SAFE-DESIGN checklist (pre-gate)
1. Pins: PASS. Every data pin captured / launched in RTL (pin anchors), reset_landing 2 stages at the W face.
2. Reach: FIXED (structural). Stages are face -> centre -> face; worst face point to far fence corner L1 = 380.24 um < 405.
   Post-gate audit owed: results/rtl/kv_hroot_safe32_1020/placed_reach_union.py on the gate CTS ODB must show max <= 405.
3. Fanout: PASS. Netlist identical to s32v3: actual ASAP7 BUF/INV terminal census max 30, 0 role errors
   (results/rtl/kv_hroot_safe32_1020/v3_native_terminal_census.json); POST_SYNTH asserts every non-clock net <= 32.
4. Depth: PASS. 123.4 ps textbook depth, no comb pin->pin.
5. Storage: PASS (with reason). No runtime-indexed storage. The 3 relay words (capture/mid/launch, 777 bits) are a spatial
   relay -- each stage sits at a different place (N face, centre, E/S face) -- not a delay line in one spot.
6. Floorplan: PASS. No macros, full std-cell rows, square, pin-limited outline (N 5.29 / S 5.06 pins/um); centre fence
   s32v3 mapped area 2265.9 um2 / 6400 = 35.4 %.
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
