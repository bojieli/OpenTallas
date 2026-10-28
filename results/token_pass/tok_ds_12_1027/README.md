# TOK-DS-12 (2026-10-27 15:58 PDT) current-main frame calendars + L0/L2 programme compile
Source 334f334efe = main 542a4f3214 + 81e8d81b35 (cherry-pick of Codex 8e79b798e: compile_layers returns failure rc)
+ per-frame plan landing-K gate (COORD ruling TOK-DS-11 (b)). intel1 unit oth-ubuntu-1567514-1793140808, exit 0.
- 4 as-built frame calendars re-extracted from RTL on current main (col_h10/h9 x/nx): all plan checks PASS, 0 fails;
  landing_lk 0x492 (E2) on all 4 = per-frame K=2 of results/s81_unblock3_1027/fi_seam/frame_lk.json for all 72 frames.
  (a) fi seams = 2 cycles (geometry, c3dd5ad1a); (c) h9 returns measured directly from RTL (old LP schedule retired).
- Vehicle tree_b178 die.v a5778b981be9. L0 (fix_r0): 65 ops 23 LOWERED / 41 PARTIAL / 1 GAP (attn.rows_allgather), 12m08.
  L2 (fix_r3new, OT_IDX_SHARD_DIE=0): 83 ops 27 / 53 / 3 GAP (attn.idx.topk_merge, attn.rows_allgather, substage_hop1), 14m06.
- Programme compile only: NO RTL layer replay, no G5, no cycles/token claim. Codex READY codex/l0-residency-0910@5f03678d7
  (not in main) removes rows_allgather GAP (L0 24/41/0) and substage_hop1 (L2 25/56/2).
