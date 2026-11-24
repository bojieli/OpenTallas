# QC-HC1-CLKENTRY handoff (lane memory)
Job (COORD 20:4x): sle_ctl group 2 x_hc1_st_b_i -> u_cland_x_hc1_st_b_i (404 ends, -55.83 rcx) + cws2 (181, -40.35) same class; conditions 1,2,4 of FABLE-RC-QC 20:48 (3 = QC-LANDCORE-SWEEP). Report ROW-REBASED to QC-ALLFIX (agent a19642e09aa8ab59f).
- Step 1: C1-noSU 12b66c0e4829 ctlclk row does NOT cover (moves hc-side fclk_in_b_hw_i only; sle_ctl byte-identical B1/C1-noSU/C1c).
- Cause: half-cycle (fall) hard cland, in_max 245 (hc1 ft ring) / 195 (cws2) + 192 ps port->pin vs 416.5 + fclk - setup 84; clands ~300/225 um from pins.
- Row SLECTL-CLKENTRY-SEAT: epyc7 /srv/opentallas-scratch2/claude/QC-HC1-CLKENTRY-epyc7/row_clkentry.py IN OUT PINS [rpsel.json]. hc1 origin -> (507.168,1257.12), cws2 -> (1114.344,1257.12); band/tap/rst group shifted; hop 228->35, 122->27. No overlaps, no plan sites in new rects.
- Plans: plan_nosu_seat.json 3f9c963d4ff2 (row only on C1-noSU), plan_nosu_seat_rpsel.json b4a03a2e900f (+ SLECTL-RP-SEL 24 relay seats), plan_c1c_seat_rpsel.json 8052bdd95837 (on C1c 3b12251bfd6c; sle_ctl type identical in C1c, only latency table differs -> same delta).
- Cond 1 (V2 4_1_cts, out/v2.qhop): q-side worst slack today +380 (hc1, to u_ft_x_hc1_st_b_o) / +551 (cws2, u_ft_cws2_o); first-consumer hop now ~70/110-143 um -> ~195-309 / 290-373 um from new seat (full cycle). fclk leg today 35.9 / 4.2 ps; fclk port pins at x551/x1159 N face sit directly above new seats.
- epyc11 /srv/opentallas-scratch2/claude/QC-HC1-CLKENTRY: chain.sh (fork C4 -> cS/tree, copy cC deltas, ot-run bindS.sh = PRE + elab + strict --types sle_ctl). logs chain.log, bindS.ot, cS/{pre,elab,bind}.log.
- Next: private probe (kit_wave private-spec sle_ctl from cS/bind, goal place->CTS) and census all 4 groups (QC-SLECTL-RESYN sta_sum_rcx.sh + census.py on epyc7).
## 21:50 PST
- PRE 1st FAIL TAPNAME (density base 266->259 after keepout move) -> epyc11 QC-HC1-CLKENTRY/tapfix.py (rename added taps clk_t259.., retap.repoint, run from cS/launch). Combined C1-noSU plan = plan_nosu_seat_rpsel_retap.json 18d22fbde479; C1c twin plan_c1c_seat_rpsel_retap.json eea24acd048a.
- PRE base-equal; elab OK; strict --types sle_ctl: 0 sle_ctl errors, 18 LATCH_EXCEPT on non-emitted cb types (probe artifact) -> no native_topology -> private-spec refuses. R8 table must be C1-noSU refreshed 63f65ef6924a (copied).
- Full strict bind running: epyc11 bindFull.sh cS -> bindFull.ot / cS/bindfull.log. Then private-spec (cmd in QC-ALLFIX-probe.sh form, --host epyc11 --goal grt --rt 70b6f0430ea9 --ab OT_TAP_ESCAPE_CLEAR_UM=0.30) + run-item; census via epyc7 QC-SLECTL-RESYN/sta_sum_rcx.sh + census.py.
## 22:42 PST ROW-REBASED 18d22fbde479 (full strict 0, LAT 1922/1922) posted + sent to QC-ALLFIX. C1c twin eea24acd048a.
- Probe: epyc11 ~/coord/autopilot/private_specs/QC-HC1-CLKENTRY/qwen_compute_sle_ctl__cla4f6f12f_1124064122 (run_item.launch.out). At CTS: census tools epyc11 QC-HC1-CLKENTRY/census (sta_sum_rcx.sh KIT ODB SDC OUTDIR TAG; copy sta_sum.tcl into OUTDIR first; census.py SUM). Read 4 groups vs V2 baseline (-93.27/-55.83/-40.35/-61.40).
## 23:56 PST
- Tap check PASS (false alarm withdrawn): reset solves on frozen reset.consumer_sites_um, NOT the clock tap_grid. Compare EMITTED bind/rtl/<type>.reset_tree.json (tree.relays). proof.py on epyc11. Clock side changed 332->325 taps, 3 fclk exports re-pointed.
- C1c twin eea24acd048a: sle_ctl byte-identical, PRE/bind not run on twin. QC-ALLFIX holds the row out until it decides.
- Probe live (runitem-sle_ctl__cla4f6f12f on epyc11, place). Census ETA 02:15-03:15: census/census_run.sh TAG on epyc11; 5 groups, chd_q_1 bits 518/519 split from bank data. KIT find in that script is untested.
- Row v2 (bank region) = QC-SLECTL-RESYN; I compose one sle_ctl delta SEAT+RP-SEL+v2+tapfix after C1e. No foreground sleeps; run tools via ot-run.
## 03:55 PST STOOD DOWN (successor SEAT-MATCH-AUDIT for the bank residual)
- CENSUS posted 03:51: plan 18d22fbde479, 4_1_cts.odb post-hook sha bee8eefa46c8 on epyc2 (CTS spilled there; same kit path), RC kit setRC_rcx.tcl. WS -276.21 TNS -3634.5, 57 viol eps ALL chd_q_1 bank data (select 518/519 = 0). hc1->cland 0, cws2->cland 0, u_tap rst_n 0, others 0. Hold pre-repair -121.46 / 2765 eps. Census tools: epyc2 /srv/opentallas-scratch2/claude/QC-HC1-CLKENTRY/census (run_cts.sh, cts/cts.rcx.sum, .hold).
- Row NOT adopted (COORD). Probe GRT left running as baseline (autopilot run-item, not a lane ot-run).
- ot-status otrun-viable-ram-965608 (epyc11, unit oth-ubuntu-966896-1795496270, bindS.sh) shows "running" but pid 965608 is dead: stale record, nothing live.
- For later ot-delete (not done): epyc11 /srv/opentallas-scratch2/claude/QC-HC1-CLKENTRY (cS tree + bind), epyc11 die-qc-103/rk2 copy, epyc2 .../QC-HC1-CLKENTRY/census, epyc7 .../QC-HC1-CLKENTRY-epyc7, intel1 census/.
- Probe chain ot-run otrun-viable-ram-1095518 (epyc11 unit oth-ubuntu-4119065-1795510602, log chain_a1.live.log; work spilled to epyc2) = GRT baseline, handed to SEAT-MATCH-AUDIT; cancel via ot-run --cancel if not wanted.
