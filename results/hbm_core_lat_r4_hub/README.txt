HBM-CORE-LAT-R4 HUB sub-lane (Tue Oct 27 01:30:08 AM PDT 2026). Ruling R3 (1): build only hub types whose pin-table hash is identical in B2o and planU2.
census_r4.txt (scripts/pinhash.py): planS2 (B2o, die_plan sha e876baf4) vs planU2 (epyc2 hbm-mu-quad-2-1026/planU2) and vs planU3
(QUAD-3 latest, epyc2 hbm-mu-quad-3-1027/planU3 01:02; nothing newer at 01:13): all 15 hub types IDENTICAL (hash + outline) in both. CHECKED.
Snap (scripts/snap_hub.py -> snap_report.json): along-face coordinate to 0.024+k*0.048; hub tables are already on lattice except
qcore_r13 (max 0.024 um). Same-point pin collisions in the plan tables (same layer/x/y): cxport_ij_q 280, gq_issue 190 -> plan bug.
Trial slices (slices/): centre ck_entry island + M5 clock pin at the outline centre (lattice); TRIAL-no-frozen-master-plan.
check-kit: clock entry placed by kit io at slice xy (1/1) for all 5; only issue 'core slice without pushdown section' (same as R3 trial kits).
LAUNCHED GOAL=place (sdc_lint/selrange/synth/face_guard/port_bind/LEC/floorplan/place; run_kit_hbm.sh skips cts for GOAL=place):
  gq_land@4e84c42519cf      intel2 unit oth-ubuntu-3198438-1793089773  16G
  qcore_r13@ebe3df4b204d    intel2 unit oth-ubuntu-3198442-1793089773  16G
  pc_ctrl_leaf_h9b@f667644f356a (pilot table p00, 8 inst; 10 tables total) intel2 unit oth-ubuntu-3198439-1793089773 16G
  sfustore_hw@e7982b24ac22  intel1 unit oth-ubuntu-3949786-1793089773  24G
  programme_store_r10@b0729904377c epyc2 unit oth-ubuntu-1745300-1793089773 48G
  kits: <host>:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-hub/kits/<module>_<pinsha12>-_r4 ; logs: <host>:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-hub/logs/<kit>.place.log
SKIPPED: qw_dec PORT_MISMATCH (plan bus x__E vs RTL; B2o table re-pinned) ; hc_subtree32_core NO_RECIPE ;
  cxport_ij_q, gq_issue pin collisions (plan) ; multi-clock-port types need a 12.8a entry decision (one centre entry per core):
  vm_wr_q_t_lanes4 (6 clk ports), inj_idx_join_rg (clk_r0/r1), cl2_bfqg (20), cl2_ctlx (clk/clk_cal), xq_pegress (5),
  kshare_splitstrap (hbm_clk + stream_clk, 2 domains).
Known die-plan issue (QUAD-3, not a core-pin blocker): R14 NE enclosed-pin FAIL for gq_land / pc_ctrl_leaf targets.
