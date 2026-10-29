HEAD-START-2 (2026-10-29): placed START vehicle reach + full-body census (plan hk4 = plan_spine_raw_rx_tx, confirmed by DIE-HEAD-24 06:01)

Vehicle: Codex final5 (localhost /srv/opentallas-scratch/claude/head-start-mapped-0251/final5, copied to
intel2:/srv/opentallas-scratch2/claude/head-start-2/in) = 14,680 mapped START cells (1356 stages, 5299 FF, local raw-wavefront
resets) + 3,690 per-branch BUFx8 data chain cells (driven/) + legal1 clock tree (10,850 cells, 735 taps) + NEW: one local
clock-entry BUFx8 per stage (1356), placed by tools/s81_head/head_start_local_clock.py from codex/head-kits-0251@735403ad0
(WIP, not on main; run unchanged, output physical_lc.json.gz). 0 FF / 0 explicit cycles added.

Census (start_reach.py, every net driver->each sink on body centres; stage clock net split at the local BUF8):
  tree->tree 10849 max 341.28 | tree->local BUF8 1356 max 197.586 (b768->r1158_0 stage, clock taken from node A pin)
  local BUF8->FF CLK 5299 max 20.034 | START cell->cell 18405 max 186.462 | last cell->START out pin 351 max 183.341
  raw reset relay->cell 4072 max 328.317  ==> 0 hops > 405 um.
  Bodies 30,576 (start 18,370 / clock 10,850 / local BUF8 1,356): 0 full-XY overlaps (LEF heights), 0 off 0.27 row phase,
  0 off 0.054 site grid, 0 START/BUF8 orientation != row parity, 0 area intersections with hard-core+2.16 halo / PHY domain,
  all corners inside partitions/channels. (A corner-point SiteMap.legal test flags 24 legal1 clock cells whose edge ABUTS a
  halo edge exactly: float equality, 0 area -> legal.)  verdict PASS (geometry only; no route, no timing).
Renders png/: overview, root, worst_* per hop class, rows_root / rows_worst_lclk (native rows, bodies). Viewed.
Not done: GEOM independent review, GRT50, related-pair TT/FF STA, routed re-plan of START offsets (still PLANNED, head_start_1_1029).
