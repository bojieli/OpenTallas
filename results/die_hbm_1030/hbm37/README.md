# DIE-HBM-37 (HBM die owner, 2026-10-30 12:02-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-37.
Tools: branch base db22a258fa5 (tools = main 16f2590f75f, same as DIE-HBM-35 d35a gates).

## d35b = d35a + collar_idx256r signed-view pins (COORD RULINGS 12:03 (1) (A)) -- CHECKED
mk_d35b.py BASE=d35a OUT=d35b DEF=signed view (intel1 hbm-cores-kits-27/collar_s30wl 6_final.def; 6_final.odb sha 93bc75ef).
Only the collar (root u_col_idx, origin 976.32,734.4, outline 88.992 square, R0) changes:
- clk    (88.872,44.424) C -> (43.224,43.2) M5 C; clk_in (0.096,52.584) W M4 -> (44.664,43.2) M5 C. Both inside the plan
  centre clock entry island already in clock_entries.json (u_col_idx xy 43.2,43.2, island 38.88-47.52, merged clk+clk_in):
  the plan clock entry is unchanged, the stale pins file now agrees with it.
- c_done: d35a already used the W pin (pin_select {c_done: c_done__W}, W M4 0.096,52.968) = the view's c_done position.
  d35b names that pin c_done, drops the unused N-face c_done (60.696,88.896) and the alias, removes pin_select.
  -> no parent-side connection moves.
- 4 island FT ports of the view (mp_isl0_ck_i/o, mp_isl0_rst_i/o, M5 inside the island) recorded as die-owned FT sidecar
  cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b_die_owned_ft.json (schema core_die_owned_ft.v1, as QC vmr).
Pins file cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b.json (1559 pins, sha 59da3314...);
die_plan.json sha 9349ccf9...; sidecar sha 0d5252ff... (plan_of_record/d35b, gz + SHA256SUMS; other files = d35a).
Gates:
- pincmp v2 (SIGNOFF-SPRINT-2 /tmp/pincmp_sp2.py) view vs d35b pins + sidecar: MATCH 1563/1563, outline 88.992 OK,
  0 moved >0.25 um, 0 layer diffs; vs pins alone: only_view = the 4 FT ports (pincmp_*.txt).
- G0 FAIL 6 err/918 warn and G0C FAIL 14 err/128 pending/910 warn on d35b = IDENTICAL finding set to d35a on the same tools
  (0 new, 0 gone; g0_d35b/*diff*); d35a rerun = DIE-HBM-35's d35a report exactly. Collar-related findings: only the 2
  inherited WARNs (core_pg LEF path, u_hb_idx__selector.k face orientation).
- Neighbour pins: the moved pins are interior (centre island) and c_done keeps its parent position; the collar has no
  partition-face pins; G0C core_faces unchanged. Render viewed: collar_d35b_pins.png.

## (1) V-A G2 probes on q_b010 (DIE-HBM-36 docker dhbm36-g2-*, intel1 die-hbm-36/g2) -- verdict PENDING
- The 30-iteration runs (base/va12/va12t part_q_b010) were at extra iteration 4/30, 3/30, 2/30 at 12:23 after 55-75 min
  (~20 min per iteration) -> final overflow expected ~21:00-23:00. Not killed (adopted). Collect part_q_b010/grt.log
  "Final congestion report" (run.sh writes grt.json via wt/die-hbm-36 g2.py; keep that worktree until then).
- Initial GRT (q0_*, 0 extra iterations, CHECKED grt.log): total overflow base 889,963 / va12 1,352,609 / va12t 1,534,740.
  Per layer base: M2 86.7k, M3 413.7k, M4 47.4k, M5 256.8k, M6 42.0k, M7 43.3k (V-dominated, usage only 13.4%).
  va12 - base: M2 +125.8k, M4 +138.2k, M6 +164.6k (H), M3 +13.8k, M5 +13.4k, M7 +6.9k -> V-A's own cost is horizontal.
- Where (congestion report = first 20,000 violations only, so a sample; bins CHECKED on that sample):
  base: ~65 % of sampled overflow is L28x2 (1616 b: E face y 2912-3206 at 5.5/um -> 3 stations -> N face x 559-828), the
  vertical run y 3200-3800 x 600-800 through the staggered hard-core field (218x187 cores at x 587-806 y 3292-3479,
  x 484-702 y 3637-3825 / 3992-4179; cores obstruct M1-M5, only M6/M7 pass): no straight M2-M5 N-S channel wider than
  ~23-28 um exists between x 469 and 829 above y 3290.
  va12: extra H overflow at y 1200-2100, x 0-300 = the W core column (25.9-276.5, cores 268 um tall, y 17-2886, five
  103-um gaps): W-face through bits cross it only in the gaps (M2/M4) or on M6 over the cores.
- Capacity estimate (UNCHECKED, adjust 0.5): W column in the corridor y 950-2908: gaps 515 um x M2+M4 ~12.5k + M6 over cores
  ~15.3k = ~27.8k tracks vs ~11k existing W-face bits + 11.9k V-A = ~22.9k (82 %) before station pin access.
  L28x2 turn: M3/M5 gaps ~51 um ~1.2k + M7 270 um ~2.1k = ~3.3k vertical tracks for 1,616 b + L167/L168 traffic.
- Smallest plan changes if base does not reach 0 (proposals, UNCHECKED, not built):
  (a) L28x2: move its 1,616-b N exit window from x 559-828 to the core-free columns of the N face or split it over
      two windows (x 236-250/469-483 are only 14 um) -> realistically: re-site the one core at (587.52,3291.84) 120 um
      west/east to open a 120-um N-S channel x 700-829 from y 2900 to the N face (one intra-strip core move, no neighbour).
  (b) V-A: do not run the W face at 12/um across the W core column; keep V-A through bits on M6/M7 over the cores with a
      per-face budget of ~8/um in y 950-2908 and route the remainder through an N-S die_ft_band (DIE-HBM-36 turn model).

## (4) V-A route lengths for TOK-12 (CHECKED arithmetic from DIE-HBM-35 est_gaps on the HH bind, plan d32q geometry)
tok/va_route_lengths.tsv: 68 pairs with unplanned bits (42,282 b), path_um along the b0xx strip chain, hops at 405 um,
cycles_est. Max path 17,975.5 um (b100->b102, 2,777 b/half, 47 cyc); hub->b113 2,277 b 30 cyc; b113->b112 1,662 b 46 cyc;
b113->b110 1,534 b 44 cyc; bit-weighted mean 34.5 cyc.

## (3) NW hub LOAD relays -> hard transport cuts (ESTIMATE, UNCHECKED)
NW soft count 375,862 + LOAD relay 165,362 FF = 541,224 > 400k. Moving localbank (107.5k) + fill (33.0k) relays into hard
cuts leaves 400.7k (still over); + packet (16.6k) = 384.1k (4 % margin); all LOAD relays (165.4k) = 375.9k (6 %, recommended).
Form: 8 cuts per hub (one per LOAD lot, natural boundary), ~20.7k FF each ~ 0.012 mm2 at 50 % util (~111 um square).
q_hub_nw north band y 2880-4320: hard-core cover 41.8 %, 6.87 mm2 free, 160-um free windows across x 0-8057 -> area fits
(CHECKED plan geometry); cut pins / station hops not built. Goes into the d37a event.
