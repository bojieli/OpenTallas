# KV-101/SPLIT handoff (Claude, 2026-11-13) — DO_NOT_COUNT

Worktree: epyc7 /srv/opentallas-scratch2/claude/wt/kv-101-split, branch claude/kv-101-split-1113 (from 3952588291). LOCAL ONLY, not pushed.
Commits: 1bc269e87a (clock helper's uncommitted adapter edits, verbatim) | d025c5f1a5 feed root | 2fbc7638ab aux PV --table-landed | e3b810916f native_istations collects width errors | cc29522d0f bind: recorded core reset tap drives a 1-bit rst_n bus input (PVFIN open item) | 9c8e9a69ad kv_sd_raw_reset_form --types. Focused tests: test_kv_split_feed_ref (9), test_kv_pv_col_pads (+2; test_import_leaves_sys_path_unchanged also fails on base, py3.14), test_native_istations (+1, 20 pass), test_bind_core_reset_bus_tap (4), test_kv_sd_raw_reset_form_types (2).
S = epyc7 /srv/opentallas-scratch2/claude/kv-101/split. Logs: intel2 ~/kv101log/. Bind recipe: S/bind_s5.sh (env KV101_IN, KV101_OUT; ot-run --hosts epyc7 --dir S --stage <input dir>).
Inputs live inside the worktree (untracked) at physical/die_plan/qwen_kvsys/split_1113/: pin_pv4, pin_pv4_pruned, pin_pv4_r8_phy are byte copies of die-kv-100 W. They must be there because the asbuilt base ../../../../.. and the native-base resolve check need them inside the tree. Inputs: kv101_s5 = FCLK + col; kv101_sdprobe = probe only; kv101_s6a = generator bind (col extra only); kv101_s6b = s6a + SD raw + regenerated vport W table (latest).

## Strict history
phy2 (start) 91 -> s5d 45 (S/bind_s5d) -> s6a 15 (no V/W extras, stale 0) -> s6b 14 (S/bind_s6b/{diagnosis.json,bind.log}, src 9c8e9a69ad, stale 0, data proof all 0): PARAM_REGEN 1, R8_STRAP_PAD 3, TYPE_SPLIT 2, NATIVE_ISTATION_WIDTH 6, EMIT 2 (bundle width). NOT functional qualification: V-word table open (3c).
Note: R8_STALE lines are capped at 30 messages. Read bind_report.json lanes.landing_alignment.stale: 138,004 bits on phy2, 124,838 on s5d, 0 on s6a.

## Classes
1 START schema feed.root: CLOSED. S/start3/plan_c.json, root hub_C read from feed.json, schema 0, 63/63 types, PASS_SOURCE_GEOMETRY_ONLY. RAW mode NOT run yet. Inputs: start3 plan, the fresh native bodies of the final strict out/rtl (54 split bodies now emit), H/native_homes4p73.
2 FCLK54: CLOSED. reach_rules.py fix --rules 4 (R-REACH-4). It changed exactly the 54 EMIT types, only source_clock_port/tap. S/fclk_fix_report.json, S/fclk_verify.log. If the START/control inventory changes density taps, rerun it (idempotent).
3 aux PV column: CLOSED. Table S/aux_pv5/pv_col_pads.json: TRUNK_D 72 / FLAG_D 90 / C 18, 189 members, 9096 pad flops (+18 trunk cycles; token re-price owed).
3b vport W request pads: regenerated on s6a with S/vw_regen/vport_w_pads_split1113.json (16 vports, 12 padded, 315 stages, RL 153 unchanged). The 20 stale b5 rows are gone.
3c PV V-word pads (pv_v_pads_b4, 2022 members, about 125k stale bits): OPEN, structural. On the split bind the V members sit on native composites (native_composite_pv_*_pvg0_p0 port s0__pv2/s1__pv2). kv_pv_v_pads.py matches only pvw_*__u_s*_b* banks, so check/pads see 0 members and V-D-H is UNCHECKED. The old table renames through bind composition_alias but is stale after the split cuts. Fix: give kv_pv_v_pads a decomposed Bound view (composite port -> bank via the bind composition alias), regenerate on s6a, add the result to land_r8_extra. s6b runs WITHOUT a V table, so its count is not functional qualification.
4 PC cap31 (3 R8_STRAP_PAD + 2 TYPE_SPLIT): OPEN. The fix form is r8_strap_pad_max 31 on kv3_pc_v1__cl4ea58a5c / kv3_pc_v1__cl7f648944 only. Not applied: it waits for the final semantic table (memory helper).
5 SD raw relay: CLOSED. The probe bind (SD branches dropped) shows u_rrl_18 d rst_rl_17 -> rst_n_t5, so the relay numbering moved by one. kv_sd_raw_reset_form.py --types kv3_sys_SD re-traced it: 3 branches, base rst_rl_17/16, max hop 289.8 um, 0 data/reset cycles. S/sd_raw/{plan_c.json,report.json}, in kv101_s6b.
6 PAIR image: OPEN. Run physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh <final bind out> <dir>, then update bind/kvbind1025/pair_image_txdp.json (K 170/160/150/3, XDIE 91,91,89,89,89,77,77, HOST 156 on phy2/s5d). QC must bind the same image.
7 NEW split cut width (6 NATIVE_ISTATION_WIDTH + 2 EMIT bundle capacity): OPEN. kv3_pv_v1_x2 / v1n_x2 o_vport_W_N_vo_d2/d3/d4 bind 152 > plan 140; kv3_pv_x2 / v8_x2 i_vport_W_N_vo bind 153 > plan. Cause: type_split cut-pin sizing under-counts the bound payload by 12-13 bits; see pv_N_1_x2 -> pv_N_0_x2 L2321/L2334 width 140. Fix in type_split census, then re-split.
hub6 (COORD): DONE RC_HUB 0 -> S/event_in6h. Cause: pre_split2.json lacked its plan-relative pins/. Staged S/hub6_in, spec S/spec_hub6k.json.
PVFIN: binder fix cc29522d0f done. The rst2 form has no target in the split hub_C (no pvfin hard cores). KV-101 assigned the native-pair join into the split hub_C as the NEXT increment, after this burn-down: kv101_rst2_form on the split hub_C, then strict.

## Running jobs
None. All my units have ended (s6b oth-ubuntu-4031504-1794623509 exit 1 = 14 errors). The parent E7 PID 3205086 is gone (its hub6 had failed; my rerun is S/event_in6h).

## Review item (cc29522d0f, bus-input core reset taps)
On s6b the rewire touched 89 ports in 57 types, not only hub_C. Every core reset that the bind recorded but that arrived as a lane bit now takes its wavefront tap: PV join rst_n from ri_pv_u_g{0,1,3}_j_rst_n_q (64), ASTK ex rst_n from ri_astk_..._owner_rst_n_q (24, the kv3_hg family), hub_C kvs_ctl from ri_ahub_rst_n_q (1). The list is in S/bind_s6b/out/bind_core_resets.json bus_input_taps. Owner rule: the plan tap is authoritative. Before adoption, check that no data/reset alignment relied on the lane-carried release. If one did, narrow the rewire to declared cores.

## Next (in order)
1. kv_pv_v_pads decomposed view, regenerate the V table on s6a, then strict.
2. type_split cut width (class 7), re-split, rerun the FCLK fix + col/W/V regen, then strict.
3. Native pvfin pair join into the split hub_C (kv101_rst2_form; KV-101 assigned).
4. cap31 after the semantic table; PAIR run_mu833 on the final bind.
5. RAW mode of control_rederive2 on start3 + final bodies.
