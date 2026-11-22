# FAM-QC-SLWSLE-R1 handoff (Sonnet 5.5, started 2026-11-21 18:50 PST)
Family: QC sle_hc0/slw_hc0 splits, sle_su_c, slw_su_c*, (cbx_q10 stays with FAM-QC-FEFW).
## Census 19:05
- hc0: sle_hc0 pvcaa93304 and slw_hc0 cl4f54b7a3 SIGNED (signed.tsv). V2 plan lists 4 split children (sle_hc0..pv1c2f9baa__pv6e886d59/pv48712631, slw_hc0__cl4f54b7a3__pvde134a90/pvd0aa3ddc) that sat OUTSIDE kit_wave only_items (no row, unowned). Added via kit_wave_edit e32dad13ecbd; plan --probe now lists pv6e886d59 + pvde134a90 eligible (the other two follow).
- cbx_q10: FAM-QC-FEFW owns it (OWNERS-SWEEP); wave relaunched gen of cl89936551 + cl94a12200_h at 18:2x. Not touched.
- sle_su_c: V2 place INFRA (command never started, auto INFRA-RETRY); plus STRUCT-CARRIED stop: V1 GRT flat overflow 38588 (8.8 h). V2 changed nothing for sle_su_c, so the same overflow is expected: structural fix = R3 su_delta sites rows.
- slw_su_c cl92142dac: V2 place INFRA not-run, auto retry. slw_su_c cl19bb38ef: V2 kit ENQUEUED (geom passed); old FAIL route FLOW is V1.
## Rows (V3 candidates, from FABLE-FIX-QC-SLE-R3 su_delta, V2 plan, sites only)
lanes/handoff/FAM-QC-SLWSLE-R1-V3-su_c-rows-*.json: sle_su_c rows b84307a2499d (0 cycles); slw_su_c__cl92142dac 194c89fb6df9 (0 cycles); slw_su_c__cl19bb38ef s3 3d3a7f3498e7 (+1 cycle on lanes sl_W0_su_c__x_su_c_su_l0/_su_l0_p1/_su_l1_p1, needs bind). Keep the E/W pad rule (su_l1 arrival - su_l0 st/landing E==W).
## Proof
private-spec sle_su_c: spec /home/ubuntu/coord/autopilot/private_specs/FAM-QC-SLWSLE-R1/qwen_compute_sle_su_c_1121190443/spec.json (plan p_v2_s2.sle_su_c.json on epyc7, env=wave, V2 tree), run-item pid 1138306 on intel2, log intel2 /srv/opentallas-scratch2/claude/FAM-QC-SLWSLE-R1/run_item_sle_su_c.log. Fleet drain: epyc2/8/10 draining, epyc7/9 99% disk.

## 19:15 proof result
sle_su_c private run-item FAILED at kit_topology: KIT_TOPOLOGY_BIND_STALE (private plan p_v2_s2.sle_su_c.json differs from the V2 wave native bind). Needs a private strict bind + LATCHECK on that plan (pattern: QC-PLAN-R9/R10 chain_b15*.sh, bind_v3b.sh) then re-run private-spec with --bind-out of that bind. Not started (fleet drained: epyc7/9 99% disk). Rows still go to QC-PLAN-R12 for V3, whose bind will cover them.

## 19:30 sle_ctl (COORD asked; QC-SLE-R5/LOCKUP-STATION-R3 resumed 18:2x so I take ONLY the V3 station + tap rows, no duplicate builds)
- su_c: R12 ACK 19:15 (SU-1..3; sle_su_c rows == V2 no-op). I struct-lifted the sle_su_c V1 carry stop; wave RETRY-INFRA relaunches it on V2 (first build with the su_delta sites). Private bind b1 still running (epyc7 oth-ubuntu-2180779-1795317101).
- sle_ctl V2 kit placed_scan (epyc7 .../items/sle_ctl__cla4f6f12f/geom): 10 groups over 405 um, 3 NEED-STATION (u_rrl_254 -> u_rp g_wgrp rs1/rst 733 um x4+4 bits, clk_t250 -> fclk_out_x_hc1_st_b_o 895 um), measured station_rows in lanes/handoff/FAM-QC-SLWSLE-R1-V3-sle_ctl-station-rows.json. These are reset-relay and clock-pin legs, not data buses: the 907 um r2r of the 19:10 GEOM is the reset relay u_rrl_254 fan-out. Tap: clk_t193 8053 sinks; tap_split.py (TAP-GRID-R5 3c2f3758f4) leaves sle_ctl PARTIAL 1378 (sinks under macros).
V4 rows from FAM-QC-SLWSLE-R1 (lever 3, Fable closure strategy 210831182d1e):
sle_ctl__cla4f6f12f: FAM-QC-SLWSLE-R1-V4-sle_ctl-lever3-type.json (= FABLE-FIX-QC-SLE-R3 rows_v2b 25b35b0b8ae9; replace the type): u_tap core moved off the 8.64-um tap-ctl slit (the (400,300)/(400,400)/(600,300) hot bins = slit between u_tap and u_ctl), b_hw_hc*_o and b_tw_data_st_a_o stations re-sited core-free (0 sites in core, worst hop 291 um), 0 cycles; needs strict bind + LATCHECK (core move).
sle_su_c: sites rows b84307a2499d (== V2, no-op) already carry core-free routes; hotspot (900,200)/(600,300) = x_su_l*_p*_o and x_su_l*_i_b near u_suvm_u_vm8q_u_cl (933,60..277) and u_suvm_u_vm8q_u_vc; refined row follows the geom cong.rpt.

## 23:2x su_c refinement status
V2 sle_su_c attempt_2 AUTO-GEOM GRT did NOT finish (grt_note "GRT did not finish", 5 of 50 iterations; no cong.rpt), so fcs_cong.py had no input. AUTO-GEOM FAIL: r2r 1058 um (794 captures), channel_h 2.64, channel_v 1.68, col_v 1.55, clock_tap_sinks 6054 (19 grid taps over cap). Fable bins (900,200) and (500..600,300..400) = the 121-um street (y 276-397) that su_delta routes ALL of x_su_l0_o / l0_p1_o / l1_p1_o / ctl_o / sc_o through, plus the cl core edge at x 933. V4 su_c row NOT yet written: needs su_delta re-run with a per-band bus cap (<=2 buses per street band, spill l1_p1_o / ctl_o to the E margin and top half, which is free) - owner FAM-QC-SLWSLE-R1, next step; applies to sle_su_c and both slw_su_c.
