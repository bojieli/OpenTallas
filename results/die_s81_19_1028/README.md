# DIE-S81-19 (2026-10-28): plan_s12 = plan_s11e landings re-composed with the ACTUAL S81 observer

Labels: CHECKED = run/read by this lane today; UNCHECKED = estimate or copied.

## plan_s12 (for TOK-S81-3 strict bind)
- Plan: `intel2:/srv/opentallas-scratch2/claude/die-s81-19/plan_s12f.json` sha256 **804dcbe81c51** (82 MB, not in git, like plan_s11).
  Base = plan_s11e 306816ce4437 (= plan_s11 + rom _gb taps 419/313 + bf_col 390/291 + 11 tap_note dropped; the go16 plan).
- Manifest: `physical/die_plan/s81/bind/asbuilt_b178_coll_s12.json` (sha 355c20d9a9de) = TOK-S81-1 `asbuilt_b178_coll_s11.json` +
  `clock_landing_table` = `physical/die_plan/s81/s12/landed_sidecar_s12.json` (c45c446936fa) + the PD7d observer opt-in copied
  verbatim (define `S81_HOSTB_LAND_OBS`, dissolve `dsdv_hostb_seqhost_mux`, its straps one level down, `dsdv_mu_hwin.sv`) +
  `substitute_inst` of all 864 as-built `ot_v41_rom_elem_q_qxpq_w10` -> `ot_v41_rom_elem_q_qxpq_w10_gb` (scripts/mk_manifest_s12.py).
  The regex is exact per frame variant (12 col_h10 + 60 col_h9 frames from inputs/die_b178.v, frames_b178.txt; element indices from
  frame_lp/plan/col_h{10,9}_l4_lp_plan_kit.sv): `u_e` also names `dsfd_bf_front_roots` at other indices (h10 r1 u_e5/u_e10, h9 r1 u_e8),
  so a blanket `u_r[0-2]\.u_e\d+` would have swapped bf_col roots. _gb ports = master minus input `xs_sv` (CHECKED diff) -> variant_removed.
- Run: `bash physical/die_plan/s81/bind/bind_s81_current.sh <plan_s12f.json> OUT` with `MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll_s12.json`
  (new elab: defines/dissolve/files changed, REUSE_ELAB not valid).

## How it was built (scripts/recompose_s12.py, CHECKED)
1. Un-compose plan_s11e exactly: 58 landing cohort clones fold back to their 24 base types (clones identical once compose-only
   fields are removed: landing_contract, fclk_* edge clocks), landing_network dropped, reset.in_sites renamed -> 171 base types.
2. Main `clock_landing_plan.compose` (unchanged tool, monitor=reset) with the SAME r98 table (die-s81-2/reg/landed_crossings.json, 98
   regions, +3/crossing), observer_part `seqhost`, observer `dsdv_hostb_dstat u_u_dst fault vid_ri / ready alive_i`.
   Result: 205 types, 2306 ports, 1700 infra edges, 271 active monitor parts, boot ready 502 cycles (was 405 at s_4S_L3), 18 band
   placement failures (same count as r98).
3. Round-trip proof (`--check-roundtrip`, compose with the ORIGINAL root s_4S_L3 on the un-composed plan): type names, partition->type
   map and every non-landing field of the plan identical to plan_s11e (roundtrip_diff.txt); only compose-derived fields differ
   (landing_contract collector trees / pin points, 6 of 1700 monitor child indices) because plan_s11's contracts were computed on
   r98 geometry and never refreshed after the s5..s11 deltas. plan_s12 carries contracts recomputed on the current geometry.
4. post_s12.py: 36 dead_inputs proofs -> proof_closing_1028.json (as TOK-S81-1 plan_s11b); **COORD 22:45 / TOK-S81-2**: the 30 abutted
   svc ring hops (dn/up/pr/sg/ss) lanes get fixed_cycles so plan = as-built 3 stages (30 lanes 2 -> 3, svc_lanes_fixed_s12.json).
5. gen.py latency --inplace: 873 lanes, sum 11,918 -> 11,948 (only those 30 lanes change) CHECKED.

## G0C (check.py --completeness, CHECKED): plan_s12 24 ERRORs vs plan_s11e 21
- The 21 are pre-existing (2 >400k cell types, 12 cut ratios, 6 pg_domain lk_ES0/ES1, 1 reset wavefront lk_WN1 IN pin 630.3 um from
  the nearest rst_o). The 3 new = `cland_mon_{ready,fault,clk}__lk_WN1` hop 617 um > 405: the SAME lk_WN1<-lk_WN0 reset edge (it was
  334 um on r98; the stale s11 contract hid it). Not caused by the observer (edge and orientation identical with the old root).
  Fix at source = move lk_WN1's reset IN pin (serdes__t1 in_site) next to lk_WN0's W-face rst_o, then re-compose (plan event).

## TOK-S81-2 dead x_f chains
- dead_xf_chains_96.json: the 96 x_f_* relay chains with no die sink (x-forward rewire) are DECLARED DEAD for L0 (0 L0 ops read them);
  they stay BLOCKED in bound_data. Removal at source (asbuilt_s81.py relay emission) = later event.

## bk_sel structural form (ESTIMATE, no build, UNCHECKED): bksel_forms_est.json
- Slope of cal residual vs root->tap path wire from DIE-S81-18's three go15 points: 0.057-0.081 ps/um TT, 0.053-0.072 FF.
- 51 taps over 4108 x 1048 um. Two roots (S81-18) 102-144 TT. 4x1 local trees 68-96. **8 local trees 4x2 (1027 x 524 um, ~6-7 taps
  each) 51-72 TT / 47-65 FF** <= 80. 6x2 40-56. Proposal: bk_sel = 8 local trees fed from the die H-tree/mesh nodes (MSCTS v4.6), no
  snake > 680 um; pairs that cross sub-trees add the feed/mesh skew between the 8 sub-roots (no S81 mesh measured, UNCHECKED). Decide
  after go16 refit: if the calibrated residual slope falls by >= 2x, 4x1 is enough.
