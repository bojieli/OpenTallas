# HEAD die spine/chain path SIMULATED on the generated die top (TOK-ALL-15, 2026-10-27)

NUMBER-CHECK of TOK-ALL-14's HEAD per-token 9,196 cycles. The die-internal part (x/GO down the spine, 12 chains with
turns, per-tile merge, spine argmax up to the root) was a paper sum in TOK-14; here it is simulated.

Vehicle: `tools/die_plan/gen.py rtl` of main `physical/die_plan/s81_head/die_plan.json` (main 542a4f321; wrapper
hashes in gen_sha256.txt), unchanged: 264 `ot_s81hd_tile_p` (native partition of results/token_pass/head_native_1351,
= generated wrapper + `ot_s81hd_tile_native`, real tile glue: x forward, chain/own compare CMP_STAGES 3, boundary
flops), 5 `ot_s81hd_spn` + `ot_s81hd_spn_end` (real spo/spr), 24 turn halves, all st_* station partitions, the ctl
wrapper (boundary flops, the ONE reset/START root) and the generated reset/START wavefront; rank-0 straps (253 active).
Substitutions (simulation only):
- ctl LEAF `ot_s81hd_ctl_core` -> src/ctl_core_drv.sv: drives x_o in the hsf0 sno_q format (go + null best, x slice m
  at go+5+m, SK 11, released golden x of the 1M token) and monitors b_i.
- each tile's `ot_s81hd_bundle_native` (the 5 ROM elements) -> MEASURED VIEW (src/mkbstub.py): go -> res_v after
  LB = 8,419 cycles, {row,bits} = that tile's RTL-measured argmax from TOK-14 per_tile.json (selected by the tile's
  own row0 strap). LB is calibrated AND checked: the TOK-14 lock-step bench (cal/tb_cal.sv = tb_native with
  {flt,bits,row} compared only while rv, x/go/xv/rv every cycle) against the real legacy reference tile on the real
  released ROM images of tE3b4 PASSES 9,003 lock-step + 180,420 FT checks at LB 8,419 with partition GO->result 8,429;
  LB 8,420 / 8,421 FAIL (cal/).
- off-path leaves (serdes_link, mesh_ep_core, host_ep_core, lep0N_noidx_core) -> header-only stubs (src/mkstubs.py).

Result (logs/): core x_o GO edge -> core b_i result edge = **8,691 cycles**, both of 2 positions (GAP 10,357), result
row 21946 bits 4173a558 = golden rank-0 argmax over all 253 tiles. LB 8,418 / 8,420 -> 8,690 / 8,692 (linear).
Controls: GO_DROP (tile) -> no result, CAUGHT; BOOST_ROW0=28160 (tW5o0, first tile of the deepest W chain, longest
merge path) -> 28167/7f000000 at the same 8,691 (spine merges the deepest W chain); same run with the golden
expectation -> FAIL CAUGHT; SPR_EARLY (spr fires without W chain) is NOT distinguishable: W and E chains are
symmetric and land on the same edge at every node (equivalent mutant under this plan), also with the W boost.

Paper rows for the same span (results/uarch/s81_head_die.json): x_fill_and_return 156 + bundle 8,429 (TOK-14) +
tile_merge_pipe 66 + spine_merge_fire 12 = 8,663 -> measured is **+28**.
Per token: xb_ingress 162 + 8,691 + rank_merge 361 + mtp/token 6 + out hop 4 = **9,224 cycles (7.69 us)**, calendar
window 10,357, slack 1,133. xb_ingress, rank_merge, mtp_seq, out_hop and the ctl-internal hsf0 issue/final compare
remain composed (not simulated here).

rank_merge re-derivation from the plan lane table (UNCHECKED, not simulated): one circuit = 2 macros, so the slower
macro lane bounds it. Worst ring path (west neighbour): m7S_tx 46 + coll_ES1_d 12 + D 251 + coll_WS1_u 13 + m0S_rx 51
= 373 (east: 372; EN diagonal 289) vs the model row 251+49+51+10 = 361 -> >= +12, before the best64 2-beat codec (+1
edge vs one beat) and mesh_ep/rank-compare internals. Lower bound per token: >= 9,237 cycles (7.70 us), slack <= 1,120.
Raw: intel1:/srv/opentallas-scratch2/claude/tok15-head-die (gen/, obj*/, run_*.log). Units: build oth-ubuntu-1986336,
cal 1973768, mutants 2649752/2649765, boost 2661422/2661427 (intel1, exit 0). Build ~1 min / <32 GB, run 2.2 s, 9 MB.
