DIE-KV-2 / KV plan event D9b (COORD 10-27 20:38 ruling (a) option A: no FT move; hub_Wi FT face windows <= 8 b/um where both
sides are single-instance types; FT stations out of the hub_Wi core slits; judged by die GRT0).  2026-10-27, own runs.
Base: hm_r26q9 (sha256 90b72bc2..., claude/kv-plan-d9-1027@1d28c13b81).  Tools: that branch (die_plan md5-identical to the D9a run).
PLAN hm_r26q9b  sha256 dae191169d57c5b3b5d6b810a6545b958b35e5d16e808c6ab40d3d838f0d59de
  intel2 + intel1:/srv/opentallas-scratch2/claude/kv-plan-d9b-1027/pd9b/hm_r26q9b.json (pd9b = hardlinks of pd9 + the new plan)
  Event script d9b_event.py (+ iter.sh/upkeep.py keep loop), ledger ledger_d9b.json.

ESTIMATE (12.14b, est.json): hub_Wi x1 and all three FT neighbours hub_C / hub_Wo / hgi_WN_7 are x1 types, so every hub_Wi face
qualifies.  FT ports >=16 b over 8 b/um and the face room they need at 8 b/um (window_for, track_max 0.6) vs core-clear free room:
  hub_Wi|hub_C   E: 56 ports / 5,292 b, need  782 um vs free 1,575 um (edge 1,676)
  hub_Wi|hub_Wo  W: 47 ports / 5,230 b, need  755 um vs free 1,652 um
  hub_Wi|hgi_WN_7 N: 9 ports / 3,969 b, need  516 um vs free 1,253 um
  -> supply ~2x demand on every face; the binding constraint is REACH (hops <= 405 um to the stations on both sides), not room.

EVENT (one source, plan only):
 (1) F2 re-window: FT ports re-packed in face order at <= 8.0 b/um (window_for at the real position, PG-stripe aware), min-shift
     two-pass packing; a port meeting an obstacle is split over free spans (schema `segments`).  Iterated against G0C: ports whose
     lane then broke the 405-um hop rule are KEPT at their old window (keep.txt, 36 ports, mostly hub_C-side lanes whose hub_C
     stations sit ~390 um from the face; the L1449/L1450 hroot bundles are among them).
     RESULT: hub_Wi FT ports >=16 b over 8 b/um 77 (14,409 b) -> 36 (6,382 b); 41 ports re-windowed (7 multi-window), max centre
     shift 168 um, every re-windowed segment <= 8.0 b/um.  Entry-face register (regs_um[0]) refreshed on 14 slots.
 (2) Stations: every hub_Wi FT station whose bit-site bbox is < 10.8 um (1 gcell) from a hard core moved to the nearest spot >= 10.8 um
     from every core, not overlapping another station, and keeping its hop to the previous/next register <= max(395, old) um;
     if no rigid shift exists, the station's bits are re-laid as a k-column block (same 2.16 x 0.27 cell pitch).  Neighbour stations
     (hub_C/hub_Wo/hgi_v8) whose hop grew past the rule were repaired the same way (no core clearance demanded there).
     RESULT: 92 hub_Wi stations moved out of slits/core edges (incl. the 1,118-b ft5 station that sat in the 17-um slit between the
     phy_adp columns -> 48x24 block in the 52-um channel at y~340, and ft5 st3 -> 1-column in the 34.6-um channel x~297);
     9 reach repairs; 13 hub_Wi slit stations STUCK (reach-bound: ft15/17/22/23/26/27 1-bit stations in the x 389-406 slit, ft27 st3,
     ft14 st3, ft16 st4, ft28/ft29 st4 in the y 1175-1192 slit, ft4 st4 in the y 337-354 slit, ft10 st4) -> need a chain re-site
     (ft_corridor) or an extra station each.  Render hubWi_d9b.png VIEWED (left D9a, right D9b).
CHECKS (CHECKED-own, UNCHECKED-indep):
  schema validate PASS 0.  G0 PASS 0 errors / 1892 WARN.  G0C PASS 0 errors / 1892 WARN (iteration 0 had 40 hop/reach errors,
  g0c_iter0_report.json; the keep loop cleared them).
  Die GRT incl clock (chainD9b.sh = D9a chain: die_trial kit, c39 continuous mesh rebuild nx32 ny71, combo, -congestion_iterations 50
  -critical_nets_percentage 0; intel1 kv-plan-d9b-1027/clk/q9b): TT and FF overflow 0 on M1-M9, converged at extra iteration 3/50,
  EXIT 0; mesh unplaced 0, keepout viol 0, overlaps 0, shield ties 34062/34062, PG shorts 0, clock nets 4372; M7 usage 12.35 %
  (chainD9b.out).
  CAVEAT: die_trial has no FT station pins (KV-PLAN-DELTA-8 A/B), so die GRT sees the re-windowed face pins but not the station
  moves; the station effect is visible only in ft_station_probe coupons (not run here: lane time).
NOT DONE: hub_Wi/hub_C FT coupon (ft_station_probe --segmented) on q9b; the 36 kept ports + 13 stuck slit stations (station re-site
  in hub_C/hub_Wi via ft_corridor, a follow-up event); non-FT >8 b/um hub_Wi|hub_C ports (L501/L636/L644/... not in the ruling).
