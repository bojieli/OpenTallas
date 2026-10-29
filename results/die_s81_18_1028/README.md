# DIE-S81-18 (2026-10-28)
Shared READY (9e0f2cfb03): die_sta_related skew diag = arrival minus planned target (raw kept as skew_raw_max_ps);
tools/die_plan/fit_dme_stage_cal.py (reproduces DIE-S81-17 inv2_stage_cal_s81_go15.json exactly, CHECKED).

go16 (LIVE, epyc2 ot-run unit oth-ubuntu-361617-*, started 22:12:57): scripts/go16.sh, data epyc2:/srv/opentallas-scratch2/claude/die-s81-18/go16
(go16.status). plan_s11e 306816ce4437 = plan_s11 + rom _gb taps 419/313 + bf_col 390/291 (CORES-EARLY-6 PLAN, UNCHECKED) + 11 tap_note
dropped; --region-dme-stage-cal inv2_stage_cal_s81_go15.json, early 1.0/1.0 merge. Gate STA --clock-cal spice_edge, spice INFO; refit
inv2_stage_cal_s81_go16.json + refit.log (per-leg rms vs the built cal).

TOK-S81-1 bind items (root causes, see COORD-REVIEW-QUEUE 22:0x): landing table = die-s81-2/side.json (873/873 lanes match) but QC default
observer on s_4S_L3 -> re-compose with the S81 observer (seqhost dsdv_hostb_dstat u_u_dst vid_ri/alive_i) = plan_s12; TYPE_SPLITs = lane_pad
absorbing unbound landing cycles; reset leaf = plan _gb ROM master vs as-built qxpq_w10 -> substitute_inst.

bk_sel two-root ESTIMATE (bksel_est_bk_sel.json, UNCHECKED): one root resid 286 TT / 257 FF over 3.55 mm path wire; two roots ~140-160 TT.
