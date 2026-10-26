# qkd_hp_or2 -- KV health-plane join (KV-HEALTH 10-19)

`q <= a | b`, one core edge, **no reset**. The KV die health plane (tools/qwen_kv_die/kv_health_plane.py) uses it for
every 2-input join; stickiness lives in the sticky sources (landing ring faults, DCAL) and in explicit sticky
`qkd_astk_fault_join` cells (non-sticky sources and the final sink beside kvs_attn.ufh). Because the joins have no reset,
the plane adds **no reset fanout** (the v4 install adds one reset load, the sink); after a reset the plane flushes by
data while the sink region is held by qkd_rst_region_pr_h273 (HOLD 273 >= plane depth 183 + source clear).
Benches (Verilator 5.050, fleet): HP_OR2_PASS (4000 cycles, all input pairs); MUT1 (b dropped) -> HP_OR2_MISMATCH
(witness results/arch/kv_health_1019/tiles/tb_or2_m1.log).

## Gate (--cts --remote auto): WARN (util only), PNG reviewed by Claude KV-HEALTH
GRT overflow 0; setup WNS +382 ps, hold WNS +92 ps; clock 1 sink, insertion 0.6 ps, spread 0.0 TT/FF.

## SAFE-DESIGN checklist
1. Pins: output q is the registered stage; a/b are one OR deep into it (pin regs opted out: they would change the priced
   plane latency, same as the closed qkd_astk_fault_join). No reset port -> no reset landing needed. PASS (by design).
2. Reach: tile 21.6 um; die wires bounded by the installer's 405 um audit (v4: 0 inputs > 405 um). PASS.
3. Fanout: 1 flop, fanout 1. PASS.
4. Depth: one OR2 (depth ~0 ps per gate report). PASS.
5. Storage: none. PASS.
6. Floorplan: no macros; full std-cell band; square 21.6 x 21.6 = the closed qkd_astk_fault_join slot (the plane
   geometry and the die lattice use it). Util 0.2 % WAIVED: a single-flop pin/slot-limited cell (the closed
   fault_join and qkd_rlys_1 sit at the same order of util).
7. Clock: one sink, spread 0 TT/FF; io_hold_margin 0.03. PASS.
8. Schedule: one edge per join, priced in the plane leaf latency (health_plane.json), no credits. PASS.
