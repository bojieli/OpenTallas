# DIE-HEAD-3 d150 event (2026-10-27, own runs, UNCHECKED unless NUMBER-CHECKed)
- Map: feed_map.py --dmax 150 on sfb250c landed_ocv + box_fix -> 304 regions (d150/map_d150.json). fallback_land plan: 358 crossings,
  188,808 ring bits, head pass +108 cyc (9,282+108 = 9,390 vs 10,357). Estimate: ESTIMATE.md.
- Compose (fallback_land compose --monitor region, base physical/die_plan/s81_head/die_plan.json): OK, types 16->22, 0 placement
  failures, landing_contract 0 errors (340 pins/1116 edges), boot <= 314 cyc; latency regen 327 lanes; event sha 457b6c2d667e,
  FB1 variant d6cbbe0fcb7c (intel2:/srv/opentallas-scratch2/claude/die-head-3/d150/event).
- G0C (check.py --completeness): PASS 0 E / 14 W, 22/22 types clean (d150/g0c_report.json; render die_plan.png viewed).
- Die GRT incl clock (die_trial kit FB1, spine_fishbone rep 250, site slide; 50 congestion it, -critical_nets_percentage 0; TT+FF):
  overflow 0 on all layers, 0 GRT-0113/4 (grt_TT/FF.txt). Clock tree.json and arr_TT/FF byte-identical to sfb250c (render viewed).
- Count-aligned margins (ca3.py, arrivals x1.05, K from derated lag, PROVISIONAL until MESO-COUNT-2): 358/358 D4, worst low 104.1
  (chW0_t__2), worst high 1255.0, K1 195 / K2 163 (lat 2/3 cyc).
- Die STA related pairs (main die_sta_related, g021 AOCV, shared droop by region, data droop class): 30 in-region pairs,
  zero-logic TT +392.4 / FF -234.6; HB4 plan TT +8.29 / FF +9.25 (54 k cells), abutted +35.0 / +3.4. Limiter: spine sp5->sp4 (budget
  model). Real views (results/die_head_1027/views, signed elemA/elemB clockfreeze capsules, 1320/1320 instances): 6/30 pairs real,
  real-only TT +310.66 / FF +130.23 before HB4 (sta_real/d150_sta_real.log). Hyb2 on real views TT -64.4 -> rejected.
