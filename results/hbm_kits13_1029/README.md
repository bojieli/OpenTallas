# HBM-CORES-KITS-13 (2026-10-29): ring driver ECO, HNX m10b island-pin snap

* Ring ot_hfd_coll_q2_hard_v8g__ring_ag (epyc2 /srv/opentallas-scratch2/claude/kits10-1029/ring):
  * V2 (retained CTS, GRT slew/cap/hold margins): signoff.py NOT SIGNED, TT +86.33 / FF +2.83, 2 TT slew pins (ring_v2_signoff.json).
  * V1b = V1 + driver upsize ECO (`v1b_eco.tcl`: place9855/place9915 BUFx3 -> BUFx6f, u_ctl.pin_p[1][251] DFFHQNx1 -> x2),
    full DRT: signoff.py SIGNED, TT +80.04 / FF +1.41, pair skew 47.0/43.2, DRC 0 (ring_v1b_signoff.json).
  * V2b = V2 + same ECO on its 2 slew drivers (`drv_eco.tcl`, `run_v2b.sh`): still 1 slew pin -5.79 -> NOT SIGNED.
  * Post-route LEC of v1/v2/v1b 6_final.v: KEEP FAIL (all compare points proved, 0 differs; 21 declared-kept
    g_lane[1..7].u_state.cap_tx_tag flops absent: yosys left them unloaded in 1_2_yosys.v, ORFS eliminate_dead_logic removed
    them). V1b is NOT signed off until that is fixed (ring_v1b_lec_routed.json).
* HNX hnx_lane_x m10: DRT-0255 on mp_isl0_ck_o; the 4 mp_isl0 ft pins are off the M5 track grid (offset 0.024, pitch 0.048).
  `isl_snap.tcl` snaps them +24 nm; `run_hnx_m10b_drt.sh` reruns DRT -> finish -> abstract -> signoff.
