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

GRT50 + START STA (grt/, GEOM-55 06:17 PASS-COND, diagnostic, no DRT). Run dir intel2:/srv/opentallas-scratch2/claude/head-start-2/r1
(ODB, guides, arr_*.txt, full reports). Base = tools/s81_head/head_strip_combo.py (main) on Codex localgrt2 raw kit (same md5 as the
out3 kit) + final5 clock; overlay = head_start_route_overlay.py (codex 735403ad0, inserts the 1356 local BUF8). ~1.5 min/corner.
  GRT50: overflow 0 (H/V), wirelength 50,593,755 um. Slew/cap: TT 0 violators (old out3 had 201 clock slew fails -> local BUF8 fixed);
  FF 16 data-pin slew 320.02..320.63 ps (<=0.63 ps over, START data B pins).
  GEOM cond 1: tree leg r97_0->b97 (341.28 um) routes on M8 (guide), above the core OBS; all ck_ nets on M8/M9 trunks.
  GEOM LL assertion (bbox_check.py on the imported ODB): 30,576/30,576 insts at expected lower-left, 0 orient mismatch,
  0 overlaps on ACTUAL bboxes, 0 off-row -> PASS.
  STA (OpenSTA propagated clock on GRT RC, CPPR on; TT setup: data cell x1.10 / net x1.05 droop + 60 ps unc; FF hold: 25 ps unc;
  NLDM, no spice clock-cal, clock AOCV 0.21%/mm NOT applied). ca_check.py classifies each of 5299 FF D endpoints by the stages in its
  netlist fan-in cone (reset ports excluded):
   - intra-stage 3944: setup min +158.24, hold min +24.30 (after 25 unc), 0 fail.
   - stage->stage crossings 1355 (= every non-root stage), as-built RTL edges, best whole-cycle J:
       513 FAIL (<0, min -145.05 ps; 400 EDGE_FALL / 113 rise capture stages), 944 <100 ps.
   - same crossings if the capture edge is re-chosen (half-cycle grid = --start-prev re-plan): 0 <0, min +90.11 ps, 22 <100 ps.
  Root cause of the as-built fails: plan J/EDGE_FALL came from the pre-legalization, unloaded-tap proof (codex-head-start-0251
  input/proof); routed node arrivals with the real START loads are +0.3..+149.8 ps later (median +40.7) along forwarded chains.
  => START offsets/edges stay PLANNED; step 5 re-plan from THIS routed proof is required (not a timing ECO).
