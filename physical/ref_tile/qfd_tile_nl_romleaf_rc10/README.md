# qfd_tile_nl_romleaf_rc10 -- QW-CB16A0-2 (10-20) A0 rc10, CRITICAL (critical_tiles.txt: gate PNG + checklist review only; no REVIEW.json / submit)

Base kit: qfd_tile_nl_romleaf_rc8 (same outline 820.8 x 907.2, 19 hard children on the 43.2 lattice, pins, pin/reset landing, hub/tx fences).
RTL: REGROOT_MODE 9 (branch claude/qw-a0-rc10-1020): rtl/physical/ot_qw_land4.sv, rtl/hdc/ot_qwen_w12_matvec.sv,
rtl/hdc/ot_qwen_rom_tile_w12.sv. Generator tools/qwen_romleaf/rc10/gen_rc10.py; MCP SDC tools/qwen_romleaf/rc10/land_mcp.sdc.

## Why (rc9 evidence)
NK rc9b r2 FAIL: CTS hold repair 10,801 endpoints -> ~30k hold buffers -> DPL-0033. Classification of the 34,239 hold
cells in the NK rc9 4_1_cts.odb (OpenROAD walk hold cell -> endpoint / startpoint, ep5): rung 0 (hub ck + ck_dw/de ->
ck_tx[g]) 4,458 EP + s2_x 1,485 SP; ROM group roots gs/gn (ck_rsw/rnw/rs/rn) 3,787 SP -> mq_wrom (ck_dw/de) 2,284 EP;
leaf u_lh -> outland 1,339; x delay-line shift chain 968 EP / 1,599 SP; ports -> pin regs 3,205 (input hold, unchanged).
The hub root ck itself measured TT 527.8..988.6 ps (2,937 regs spread over the tile: s2_x broadcast to the 8 leaves,
fault landings beside the leaves, the x delay line).

## Structural change (REGROOT 9)
Three LANDED crossings (4-slot ring on the source root, read on the destination root, K = 2; LANDING-CONTRACT L1-L7;
static calendar, no ready/credit; MCP setup 2 / hold 3 ring -> read in clock.sdc + signoff.sdc):
- L1 ROM group words: rings u_qlw1{sw,se,nw,ne} replace the gs/gn group registers on their group roots; reads
  u_qlr1{sw,nw} on ck_dw, u_qlr1{se,ne} on ck_de; group OR after the reads.  +2 memory cycles (RX), x and KV follow.
- L2 rung 0: one shared hub-word ring u_qlw2c on ck ({v, first, split, round/mask selects, raw x}), per-leaf weight rings
  u_qlw2w (ck_dw) / u_qlw2e (ck_de); reads u_qlr2{c,w,e} on ck_tx[g] beside the leaf.  +2 leaf cycles.
- L3 return: ring u_qlw3 on ck_tx[g] captures the leaf result + fault pins (replaces outland + fault landing); read u_qlr3
  on ck (hub).  +2 leaf cycles (faults are status only).
- x delay (u_xm, ME_EXTRA deep shift chain) -> ring ot_qw_ring_delay (D - 1 slots + output register).
Priced latency: t_out is 6 edges later than REGROOT 8 per matvec op (fill latency only; issue rate unchanged) -> the die
schedule takes A0_TOUT_ADD = 6 edges (QW compiler / die schedule record owed with the adoption).

## Proof (Verilator 5.050, fleet)
rtl/test/tb_qwen_a0_rr9.sv via tools/qwen_a0_safe/bench_rr9_all.sh: dut REGROOT 9 vs golden rp1 (t_out 1 + 6 edges later)
and vs REGROOT 8 (t_out 6 later, engine issue/memory interface same edge, every cycle, 30k cycles, 71 random ops incl.
20 KV): A0_RR9_PROOF_PASS MUT0 checks29899 valids10536 nonzero10264.  Mutants MUT60..64 (pinned read slot, pinned
write pointer, never-warm result read, pinned x-ring pointer, never-warm hub-word read) must all FAIL (logs
results/arch/qwen_a0_rc10_1020/bench_rr9/).

## Safe-design checklist (pre-gate; layout facts added in the COORD review packet)
1 Pins - PASS (unchanged from base: every pin registered; reset 2 kit stages, 16 kept copies).
2 Reach - PASS by construction: no new single-cycle long wire; the long hops (ring -> read, up to ~400 um hub/operand ->
  leaf) are 2-cycle landed paths; ring and read each sit in their own region (fences: tx[g], rsw/rnw/rse/rne, dw/de, hub).
3 Fanout - census in-flow (gate GATE_NATIVE_CENSUS, binding): per-24-bit-chunk KEPT one-hot pointers (<= 25 loads), per
  instance KEPT reset relay -> <= 22 chunk rq; shared hub-word slot bits -> 8 reads; x ring 16-bit chunks.
4 Depth - ring read = 4:1 AND-OR + valid gate before the read register; no new deep cone.
5 Storage - FIXED: the x delay shift chain becomes a ring (item 5); landing slots are 4 x <= 512 b per instance (< 2 kb
  per chunked ring, no runtime-indexed flop array: one-hot rotating slots).  u_mt / u_mtt tag delay lines (<= ~100 b)
  remain shift lines (pending, small).
6 Floorplan - unchanged from base (lattice, bands, pins <= 5.2/um, aspect 1.105).  New cells fenced as above; per-leaf
  weight rings unfenced (would overfill the 15 um dw/de strips).
7 Clock - regional roots as base; the inter-root seams are now landed (hold window D - 1 = 3 cycles), so the measured
  insertion differences between roots no longer need hold buffering; pin-flop spread <= 80 TT+FF to be read from the gate.
8 Schedule - static; +6 edges t_out per op, recorded above (no dynamic stall).
