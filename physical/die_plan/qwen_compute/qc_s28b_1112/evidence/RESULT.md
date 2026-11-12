# QC-S28-B result (DIE-QC-99 s28 event, lane B)

Final plan s28b5 = plan_qc99_s28 2f0c17d5f1a3 + delta_s28b (plan 65890b60e579, sidecar_pv 602df6f1c70f; re-apply of the
delta onto s28 reproduces both exactly, 1049 ops, 0 conflicts). delta_s28b.json e5c095beb53d (gz 1c12fb37ecc9).

Die keys: budgets.cland_strip_density 1.0, clock.landing_ring_fanout_max 32, die.layer_budget.type_m8_grant {enable, ndr 4w}.
Types (16): 9 sl_sc (B5: ft_slots + landing band rect_um), 7 street-rule types (B2): slw_st_b_v2__pva66d0f22,
slw_st_b_v1__cl6357f1cc__pv6ace3e48/__pvffd43fdc, sle_st_b_v2__cl14c98df5/__clfde1249e,
slw_st_a_v1__clfc5867a6__pvf82a6c28/__pvdf8e5ca4. Sidecar: collector ops of the 2 slw_st_a_v1 types (18). coll_n untouched.

## Gates (s28b5)
schema rc 0 | G0 265 -> 265 errors (0 new) | G0C 365 -> 365 (0 new) | station_lint 0 | strict bind rc 0 (errors 0,
unbound 0, 377 partitions) | bus_groups.json = s28 (315252676904) | bind_latency_consumers = s28 (f42a6da4c760).
Cycles added: 0 (B3 PLACEREP is 0-cycle register copies, LEC 4292/4292; every cycle-adding B2 type was dropped), so no
EQ statement is needed.

## B1 strip density / facewin / banduse-step
506b5064f28d, 054e07a4c17b, b668370a6ef3 are ancestors of origin/main and in the build src. Only strip density has a plan
key -> budgets.cland_strip_density 1.0 (per-type rows stay floors). Facewin is automatic in kits (no key). banduse-step
is a resize-bands transform (no key); QC census: 43/1205 bands at use 0.51-0.52 with the reserve fitting, no resize needed.

## B3 PLACEREP fanout cap: clock.landing_ring_fanout_max 32 (118 landing types gain DSREP/RSTREP/PLACEREP copies in bind RTL).
## B4 M8 grant: die.layer_budget.type_m8_grant (= OT_GEN_M8_GRANT=1; QC free_frac 0.3407).
## B5 sl_sc form (type-level, no die re-floor): VL2QC-SC plan_sc_p + SC-REFLOOR-1 plan_scp_r ft_slots/band rects on 9 types.
GAP: N-face +54 um growth (die re-floor, G0 +256 abutment) is not in this delta; it needs a die event.

## B2 street rule pass 2 (STREET-RULE-1 legalize da9ad4d161 on stage 1, add_regs 2, pin_reorder, growth 100%)
32 applied by the tool; 7 kept after the repairs and gates. Repairs: pin_boundary.py (restores boundary geometry the
legalize moved), reanchor.py (re-records reset_tree_anchor on the bind's tree, same depth, <= tol 405), collector_reattach.
Dropped, with the error (each is a GAP for the street-rule tool / a die event):
- slw_su_l1 x2: p99 1.697 -> 2.084, residual 3 violations
- cbn_q00__cl622f65d2 / __cldbcda913: outline H +34.56 needs a die re-floor (their p99 1.656 -> 1.086)
- coll_n: owned by QC-S28-A
- glue: collector_reattach unreachable source (ctlm_flt_i) after the boundary restore
- sle_su_l1 x2: schema 'core chain flt_su_c_i u_lane6: 2 bit L routes enter hard macros [u_lane5]'
- coll_core: bind 'reverse collector rst_rl_35->rst_rl_34 465.652um exceeds 405'
- sle_st_b_v1 x2: reanchor 'nearest depth-2 relay 690.6 / 439.5 um > 405'
- slw_stm_v2__cl9beb65e6: reanchor 'nearest depth-1 relay 439.8 um > 405'
- slw_st_b_v1__cle6023ec2, slw_st_b_v2__pvc2ec5bfb: G0 collector_reach 414.7-433.5 um > 405
- sle_stm_v2__cl55be2264: bind 'forwarded clock source clk_t72 is not a planned physical tap input'
- coll_s, sle_sc_v1 x2, sle_sc_v3, sle_stm_v2__cl7b3062fa, slw_sc_v1 x3, slw_stm_v2__cl1ca9c415, tt_ctlm: G0C hard_cores
  origin off the 8.64-um lattice (the tool moves cores by 4.32). Snapping to the lattice (s28b6) puts 43 station
  slots under u_core and slw_stm_v2__cl1ca9c415 fails bind (clk_t69 not a planned tap input).
- not applied by the tool: st_a v1/v2 other types, sle_sc_v2, slw_sc_v2/v3 (ft hops over reach with growth)

Findings for STREET-RULE-1 (tool bugs; 1 also seen on its qc_f fd74db742e9b, where 30 types move boundary items):
1. the band remap moves boundary geometry (landing face pins, edge_clocks tap_um, collector root, local resets) by up
   to 103 um, and interior START pins (cland_tstart_in 9.75-23.5 um) that the die START provider binds by geometry;
2. core moves of 4.32 um break the 8.64-um hard-core lattice (docstring says the lattice is kept);
3. reset re-select leaves clock.reset_tree_anchor naming the old relays (bind RESET_ANCHOR on every moved type).

## B6 route_supply p99 (edge_outline), s28 -> s28b5
| type | s28 | s28b5 | structural form / missing |
|---|---|---|---|
| sle_sc_v1 x2 | 1.509 | 0.926 | B5 done |
| sle_sc_v2 / v3 | 1.325 / 1.337 | 0.895 / 0.879 | B5 done |
| slw_sc_v1 x3 | 1.144 | 0.914 | B5 done |
| slw_sc_v2 / v3 | 1.135 | 0.883 / 0.882 | B5 done |
| cbf_q01_s2 | 2.06 ring_H | 2.06 | GAP: landing ring form (stacked / y-column ring or split landing) |
| cbf_q00_s2 | 1.983 ring_V | 1.983 | GAP: same |
| cbf_q11 | 1.741 ring_V | 1.741 | GAP: same |
| cbn_q11 x2 | 1.737 ring_V | 1.737 | GAP: same |
| slw_su_l1 x2 | 1.697 ring_V | 1.697 | GAP: core_V hint; street form worsens it (2.084) |
| cbn_q00 x2 | 1.656 ring_H | 1.656 | GAP: street form needs +34.56 um H (die re-floor), -> 1.086 |
| sle_su_l1 x2, cbn_q00__cld7bf7197, sl*_su_l0 x5 | 1.14-1.404 | same | < 1.5 |
| B2 types | 0.856-1.215 | 0.856-1.218 | < 1.5 |
route_supply does not model the strip density (B1) or the M8 grant (B4), so B1/B4 gains are not in these numbers.
