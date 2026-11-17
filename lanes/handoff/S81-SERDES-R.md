# S81-SERDES-R handoff (S81 SerDes forms H / J3->J4 / G3; split from S81-CORES-R 11-16 18:1x PST)

L = /srv/opentallas-scratch2/claude/fable-fix-s81-serdes (per host). Launch logs: intel2 ~/s81-serdes-r/. My probes: L/probes_serdes_r_1116 (E8, E2).
Source: claude/fable-fix-s81-serdes-1116 @5136be5e356 (approved r387/r392). Gate: DRC 0, TT >= -42, internal FF >= 0, visual review before sign-off, export to both stores.
Earlier history: lanes/handoff/FABLE-FIX-S81-SERDES.md, S81-CORES-1115.md (SerDes sections).

## 18:2x PST state
### H (serdes__t13) - route running E2 (unit oth-ubuntu-2519465, kit E2 L/H/serdes__t13/gen/serdes__t13; pre-GRT FF hold repair)
- MEASURED on a copy of 4_cts.odb after TT repair (E2 L/probes_serdes_r_1116/H_cts/h_worst_{TT,FF}.rpt, placement RC):
  - TT setup: 40 endpoints < 0, 24 below -42, worst -147.62. NONE go through clk_t17 / clk_t26.
    25 = u_txl.g_reg.r[1][*] -> u_txl.q[*]: launch tap clk_t29 insertion 543 ps (14 BUFx24 levels) vs capture clk_t23 184 / clk_t30 276 ps; data ~620 ps. Pure cross-tap insertion skew (359 ps).
    8 = u_rrl_N/q (negedge) -> state (posedge) half-cycle pairs across taps (t4->t11 -146.7, t29->t22 -135.5, t33->clk -76, t20->t20 -73.4, t20->t21, t4->t13).
    6 = u_txl.q -> u_ptx macro (t29, -24, inside gate).
  - FF hold (pre-repair, information): -312.77, 3894 endpoints. Classes: io_pma_rck domain 400+ (lpl r.o -> u_chn -260, q_d -> face_q_d -236, face_q_d -> rm.mem -215: rck tree skew ~280 ps); FT cross-tap t43->t42 -188, t43->t26 -155; ft*_i ports 365 (advisory); t17/t26 appear in 18 endpoints (txl r->q t39->t17 -145, capture on t26 from t42/t43).
- So the t17/t26 north-strip trees are a hold-side contributor only; the TT limiter is clk_t29. Form fix for both = tap balance (pair/own tap), not ECO.
- H kit copy staged E8 L/H2/serdes__t13/gen (rsync of E2 kit without 5_*/6_*) for an H2 CTS successor (E2 scratch has 43 GB < 50 GB floor: no new E2 jobs).

### J3 -> J4 (serdes__t14)
- J3 combined probe: PASS after two probe-only fixes in my copy (E8 L/probes_serdes_r_1116/J3_proof/combined2.tcl): (1) clocks of a port via get_property sources (STA-0562); (2) one DB per process: phase 1 = 1_synth snapshot to file, phase 2 = 3_place (ORD-0047); (3) master compare by cell family: 4690 FF drive-only upsizes (DFFHQNx1->x2/x3, DFFLQNx1->x2/x3) from 3_4 resize, 0 family/polarity change, 0 functional ancestry mismatch on 38706 FF clock pins.
  Results (J3_out/combined.ph2.log): native global 50 -> clk_t12, 8 banks x 65 single root (t15/t14), ingress d0 1874 -> clk_t22, ENC backend 5414 -> clk_t23, rt_e on t23. TX0 pairs: 544 drivers, max 754.11 um, 230 over 405 um (known p_d -> TX0 class, still open).
- J4 = copy of J3 kit, E8 L/J4/serdes__t14/gen/serdes__t14, clock_taps.tcl + config.mk from the clock packet (originals kept *.J3_before_J4), resume start cts. CTS running E8 unit oth-ubuntu-3762086 (J4_run_cts.out).
- Before J4 route: stage the approved HOLD-SDC tuple (intel2 L/approved_hold_sdc_be1) as H did (H_hold_packet_stage.json).

### G3 (serdes__t1__clb45db5be)
- t48: the TT 11.14 / FF 8.19 ps +3 fF figures are REPLACED by the die owner's decision (S81-DIE-R handoff section 3, epyc10 E/t48/t48_feed_decision.json): clk_t48 at [1992.6, 228.96] is a second sink on the clk_t13 leaf net (b30607), so t48 takes the clk_t13 window (measured t13 TT 7539.163/8540.111, FF 6681.067/7610.113), model bound pair <= 0.2 ps, common shift <= 1.81 ps TT.
- But the fresh G3 pose does not fit a single t48: the 570 native read FFs span x 1774-2686 (1014.6 um); every bank of 68 spans 600-900 um in x. One pin at x 1992 leaves ~700 um reach (> 405). t48 as one fixed group is not used in G3.
- G3 CTS running E8 on the reviewed 3_place with the existing 48 ports (unit oth-ubuntu-3768458, G3_run_cts.out; resume.json start cts, old one kept resume.json.place).

## Next
1. H clock dump of all 44 taps (E8 probes H_cts/clk_all.txt) -> H2 tap rows: txl r[1]/q pairs on one tap, rrl q/state pairs on one tap, north strip own tap. H2 CTS on E8 from H 3_place.
2. H routed TT/FF when E2 returns; J4 / G3 post-CTS TT + FF census with the same h_worst.tcl.
3. Best form -> route -> visual review -> sign-off -> export AGIdock + rtx-pro.
