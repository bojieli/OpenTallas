# HBM-CORES-R7 (2026-10-27 05:54-06:40 PDT)

Base: claude/hbm-cores-r6-1027@53fcb2b801 (FF-binding fix) + claude/hbm-kits-1-1027@afe566ce09 (hub-only branch, kit tools).
Data: intel2:/srv/opentallas-scratch2/claude/hbm-cores-r7/{kits,logs,views,slices,vmdel_trial,ep_render}.

## 1. Kit wave on planU6b (fixed generator)
- Plan choice (CHECKED, views_cmp_U4f_U5er_U6b.json, `scripts/cmpviews.py`): QUAD-6 planU6b pin tables == planU5e_r for all
  77 views; 18 differ from U4f (QUAD-5 re-pins). Kits use planU6b (latest pin tables).
- 76 modules (+ pinless keybuf = 78 designs); 9 excluded with reasons (wave_order.json `excluded`): ep (R6 rp2), collar (a4),
  hcp_sys1/argmax (R5 RTL not on base), xcal/sfustore/programme_store (outline re-pack pending), gq_land/pc_ctrl_leaf (LEC NEQ RTL).
- 67 generated, SU-first (`scripts/mk_kits.py`, KTAG _k2): 21 OK; 46 BLOCKED in the generator (mk_kits_result_U6b.json):
  NO plan clock entry 17, NO_RECIPE 13, PORT_MISMATCH 12, MAP_AMBIGUOUS 3, exp-family macro placement missing 1.
- Every launched kit: config.mk OT_VCLK_FF == sdc_lint.json insertion_ff_ps (202.5) checked before launch; clock port
  re-snapped onto the M5 track (`scripts/clkpin_snap.py`: main master_slice.py writes .048x.48 but 0.024 off track).
- Launched (`scripts/launch_wave.sh`, ot-run staged kits, intel1/intel2/epyc2): 16 kits (14 GOAL=place, 2 GOAL=synth for
  >0.45 mm2: vms_glue_nw_t, split3 opstore_b) + pslice _k2mp. Held: vmdel (trial), serdes (IP_DECLARED),
  side_rest/side_softplus (clock port is the bus clk_side[*], plan entry names clk_side -> plan/RTL).

## 2. programme_pslice_c5 explicit macro placement
`scripts/pslice_mp.py` -> pslice/pslice_c5_macro_placement.json + pslice_c5_mp_plan.png (viewed): 100 SRAMs, 8 stacks on the
4.32 lattice (pitch 116.64, 21.816-um pin channels; SRAM pins are on the W/E edges only), abutted in y on the row grid
(41.31), boustrophedon by g_c column, N std-cell band 549.7..756 under the 2470 N-face pins, clock island in the
stack-3/4 channel clear of halos. Kit ..._k2mp place RUNNING.

## 3. vmdel_lane_n outline re-plan (TRIAL, plan owner decides)
`scripts/vmdel_trial.py`: height 108 is W-face pin-limited (564 M4 pins); width 257.04 -> 142.56 with the two SRAMs
stacked (x0 30.24, y0 17.28/58.59), W band / S band / E channel. Trial kit placed, LEC EQUIVALENT 3648/3648,
std-cell area 1038.8 um2 / free core 5518 = 0.19 (plan outline 0.06). Render vmdel/vmdel_r7t_placed.png (viewed).

## 4. Collected
- collar attempt 4: NOT SIGNED. Only reason drv slew TT 32 / FF 25 (worst 369.06 vs 320 ps, all u_banks bank9/4/8
  payload word AO21 A2 pins; SLEW_MARGIN 20 was applied in 3_4 but the violating nets are not fixed). TT setup +23.43,
  FF hold +0.77, pin insertion TT 261.83 / FF 202.76, pair skew 32.7/30.4, DRC 0, antenna 0, PG open 0;
  routed LEC EQUIVALENT 9393/9393 superset all_shown true n_extra 0. (chain had no kit signoff.py -> R7 bundled main
  signoff.py and ran it on the routed view at 06:13; signoff.json 06:19 > 6_final 06:10.) collar_a4/.
- ep rp2: placement done (PROBE_PLACE rc 0); GRT probe in extra iterations (overflow > 0 at it 12/50, 06:19) -> verdict
  pending. Render ep/ep_rp2_placed.png (viewed).
