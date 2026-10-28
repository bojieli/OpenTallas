KV-PLAN-DELTA-9 (DIE-KV, 2026-10-27) -- result. Estimate first: ESTIMATE.txt (12.14b).
Plan dirs (one source, both KV forms): intel2 + intel1:/srv/opentallas-scratch2/claude/kv-plan-d9-1027/pd9/hm_r26q9.json
  sha256 90b72bc2c82e4d49f976b162229047ee4ec65fee73cff09c129398a1563a6270 (base hm_r26q5c39 41902469..; pd9 = qk-cores-7/pd + new
  cores/*_r26q9.json pin files, copies in event/).

EVENT D9a = LANDED (plan hm_r26q9):
 (1) KV-HOST-REGEN-1 pins (COORD 19:09 (b)): core_tx 3770 -> 3627 pins (-143 u_ctrl__cmd_hc[181:39]) = RTL 3627; phy_pad + phy_adp
     ck_phy[0] -> ck[0] (same xy); cdc_pc 2166 -> 2165 (ck_phy[0] dropped, it had no tap).  The 9 phy taps (phy_pad + 8 phy_adp)
     change kind landed/forwarded -> die-clock core sink (insertion 250): the b3 bind of record has ONE core clock, so the renamed
     ck[0] is the die clock.  Taps stay at the old pin xy (core EDGE, not a 12.8a centre island) -> see ASK.
 (2) host_qm FOLD (GEOM-REVIEW-35 / COORD 20:01): qkd_hr_host_qm removed from hub_Wi.hard_cores (+ its die tap); u_pacer stays in the
     hub_Wi partition with glue:qm_host/fence_host.  Shrink rejected in ESTIMATE (a 17.28^2 floor slot still fills ~0.07).
     KV-HOST-KITS-2: withdraw row 8dc03c466023 (no host_qm kit any more).  KV hard cores 1628 -> 1627 instances, core taps 521 -> 520
     (+9 phy core sinks; 0 landed taps left in hub_Wi).
 (3) G0C [cells]: the 11 PATH-KV-BIND explicit-split types (kv3_pv_v1n..v6n, kv3_hg_v1p2..p6) get type.cells = parent estimate
     (cells.py), same basis as LAND-KV-1 cells_fix.py, now in the one source.
 Checks (own runs):
   schema validate PASS 0.  G0 PASS 0 errors.  G0C PASS 0 errors / 1892 WARN (base q5c39: G0C FAIL 11 = exactly the 11 [cells] errors;
   the host change alone gave findings identical to base: 11 E / 1893 W).  CHECKED-own.
   Die GRT incl clock (D5 chainC recipe: c39 continuous mesh rebuild nx32 ny71, combo, -congestion_iterations 50
   -critical_nets_percentage 0, TT + FF): overflow 0 on M1-M9 both corners, converged at extra iteration 3; mesh build unplaced 0,
   keepout viol 0, overlaps 0, shield ties 34062/34062, PG shorts 0, metal shorts 0, clock nets 4372; usage M7 12.32 % max
   (event/chainD9.out). Run on plan dce0c69b (before (3)); kit for the final plan 90b72bc2 compared: 117/117 grt/clock/abstract/psm/sta
   files byte-identical -> GRT result holds for the final plan. CHECKED-own (cmp), UNCHECKED-indep.
   F1 station-pin flag: die_trial has no station pins (KV-PLAN-DELTA-8 A/B byte-identical), so it cannot change die GRT; it applies to
   ft_station_probe coupons only (none run here).
   Renders VIEWED: render/hubWi_d9a.png (host_qm gone, phy taps now core sinks at edge pins), render/base_row7.png.

TOOL (plan-schema change, COORD 20:04 ruling (ii)): multi-window hop ports.
   tools/die_plan/schema.py: port `segments` [{pins, window_um}] (pin order, epoch pin last; window_um = envelope); pin_positions places
   each segment on its own window with the GLOBAL bit layer parity (F1 class kept); validate: segments cover the pins, inside the
   envelope, no overlap; port_segments() helper.  check.py: pin_track_max judged per segment window.  Plain ports byte-identical
   (test vs a reference copy of the old pin_positions).  tools/die_plan/test_port_segments.py 10 PASS.

EVENT D9b (FT move + F2 + slit stations) = NOT MADE -- new structural blocker inside pv_S_7 (kv3_pv_v7), found once the face windows
 were solved with segments (event/d9_move_try1.log):
   windows found, all <= 8.0 b/um: L1449 whole on every hop; L1450 pv_S_7|hgi_WS_7 = 307 + 812 pins (11219-11258 / 11639-11741),
   hgi_WS_7|hg_WS_7 = 307 + 812 (10918-10956 / 11544-11646); L663 whole on 3 hops.
   Station siting FAILS: "ft57 (L1449 in pv_S_7, N->W, 1518 um): no chain within 403 um" -- the WHOLE (unsplit) bundle; the split is not
   the cause.  pv_S_7 has 20 macros in 4 columns x 5 rows; macro-free full-height columns x 4847-5107 (259), 5487-5590 (103), 5970-6229
   (259); full-width channels y 10644-10688 (43), 10878-10981 (104), 11172-11249 (78), 11422-11448 (26), 11638-11742 (104), 11932-12165
   (233, but its W face is full of existing ports).  The 231-um W-face span only meets 32 + 26 um of full-width channel; channel-aligned
   free W-face capacity ~1,250 b @8 b/um vs 2,238 b needed (UNCHECKED estimate from CHECKED geometry); ft_corridor builds only L/Z paths.
   => the approved move through pv_S_7 is infeasible without re-windowing existing pv_S_7|hgi_WS_7 ports or a waypoint corridor.
   F2 census: 373 KV FT ports > 8 b/um die-wide (event/census_f2.py); F2 + slit stations were scoped with the move (hub_Wi tile) and wait
   for the D9b ruling.
All numbers CHECKED-own unless marked; none independently NUMBER-CHECKed.
