# TOK-DS / TOKEN / S81-ROWX / S81-UNBLOCK parked on explicit reset

Root explicitly ordered PARK at approximately 02:04 PDT. No new work/jobs/merges after that instruction. Running jobs left intact; no kills. This packet is the final source/job handback.

## Current strict functional S13 bind: PASS

All paths below are on intel1 unless stated otherwise.
Run root R = /srv/opentallas-scratch2/claude/codex-tok-s81-1028
- Strict output: R/bind_s13rfunc_reset/out; bind.rc=0.
- 398 partitions, 204 types, 873 crossings, 606281 crossing bits; errors/type_splits/unbound/tied/undriven/multiply_bound all ZERO. 10352 declared straps; 8508 instance-path selectors (864 added QX selectors).
- Source frozen /srv/opentallas-scratch2/claude/wt/codex-s81-bind-s13r-1029, branch codex/s81-bind-s13r-1029@e4ad09a663.
- Plan R/plan_s13r2.json SHA256 e4a0d4d83e5401f948e8276bfb9848495d363d00b99aca4c442074e613edd41d.
- Manifest physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json; sidecar physical/die_plan/s81/s13/landed_sidecar_s13.json.
- Dead-input proof results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json: actual reproof36 declarations/21 specializations, declarations+dependency_modules identical to prior closing proof; adds actual observer define. No geometry/data/cycle changes.
- Exact plan+concise summary already copied to intel2:/srv/opentallas-scratch2/claude/codex-s81-2340/source_s13r/{plan_s13r2.json,bind_summary.json}. S81 owner folds into next source candidate; do not confuse physical successor with new data cycles.
- Current bind CA/STA NOT RUN. Old go16/reach17 plan_s11e CA results are diagnostic only; S81 actual physical STA remains FAIL. No provider/full-token/signoff claim.

Failure chain handled: initial missing sparse dead-proof file; stale observer define proof (reproved); missing source-clock tap input; then terminal bootstrap raw reset naming defect. All retained in R/bind*, no repeated elaboration. Original fresh asbuilt R/bind/out/asbuilt.json reused.

## Shared source and results

Own narrow source worktree /srv/opentallas-scratch2/claude/wt/codex-forward-clocks-1029, branch codex/forward-clocks-1029 HEAD47108edd39692035aeb73fe7f7a2e2170f86ab21 (pushed to hub).
- ea2b8d7a6b: exact planned forwarded-clock-only input export opt-in, unknown taps/no opt-in fail closed; kit wrapper declares/connects once. Whole census187 types/488 type-port combos. Merged main b0fd1009b1.
- 5ecf4184cb: shared raw-reset resolver for monitor and collector; exact parent/XY, no arbitrary reset alias. Whole census155 missing raw references/115 types ALL existing bootstrap raw rst_n_tN outputs;0 new flops/current cycles/geometry. 40 focused PASS; merged main dd32b877cd (merge reports139 integrated PASS/1optional skip).
- 8273ed003e: results-only current strict0 record results/token_pass/codex_s81_strict_bind_1029/record.json. Exact patch intel2:/tmp/codex-s81-strict0.patch sent merge.
- 47108edd39: compile_layers.sh maps HEAD/head to CLI head and fixture HEAD; MTP/mtp_draft to CLI mtp_draft and fixture MTP. Preserves L0/L2/L14/L20. bash -n PASS plus actual successful HEAD/MTP invocations. Exact patch intel2:/tmp/codex-six-layer-runner.patch sent merge; final merge status should be checked, no new merge requested after reset.

IMPORTANT: this worktree has UNCOMMITTED candidate changes to tools/s81_dv/layer_prog/xs_calendar_pack.py and untracked tools/s81_dv/test_xs_calendar_pack.py. NOT READY, NOT COMMITTED, NOT USED by any running compile. Candidate coalesces adjacent phase reader intervals when no idle PRIME gap exists, retaining all original functional action edges and capacity/idle guards. Initial focused test result2PASS/1FAIL: the 'existing idle boundary' synthetic fixture leaves accept228 in an inactive gap after action200, so fixture itself violates existing accept-active guard; still needs real analysis/control/qualification before any adoption. Do not blindly commit or mark solved. Root requested unresolved L0 PRIME failure explicitly retained.

Compiler/functional worktree /srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028, branch codex/s81-frame-sub-1028@5948fb8881, currently frozen for active L14 compile. Contains PRIVATE S13 metadata; NEVER merge whole branch.
- Source extractor0b narrowed earlier as8d2e6487d4: real instance-specific substituted QX variants now selected in frame calendars (3 used masters h9x/h9nx/h10x), unused h10nx correctly rejected absent actual frame. Actual12GB stations/frame,72 total frames. Mixed/absent/unknown variant and wrong GO fail controls.
- CFG64ab/8a, QX81e/fad, production aliasesb2ef/001 narrow merged main61f103a8f9. Native compiler writer442 original images byte-identical+442 exact bound aliases over3 used masters; empty/wrong selector controls caught. Actual selector rule precedes leaf substitute, so QX rule targets predecessor ot_v41_rom_elem_q_qxpq_w10 and INSTANCE survives _gb substitution. No global BF namespace adoption.
- ca18d006d0 results-only native realboundframe: actual XS4 -> actual flattened h10 _gb/CGR0/GO_BOUNDARY1 frame -> CAP; actual CFG/QX bound names and fixture oracle.14 returns+4 checkpoints exact,0 faults,833ps,GO452 firstreturn732 last772 lastcapture855,GO-to-capture403cycles unchanged; corrupt input and wrong loaded weight FAIL caught. Uniform phase component only; no die transports/START or global provider qualification. Build594.635s/7488MB Verilator5.050. R/native_bound_frame/check.json and retained script/logs. Patch intel2:/tmp/codex-native-bound-frame.patch sent merge.
- 5948fb8881 ONE diagnostic hunk GAP_HEAD now says actual final-layer activation publication/transport/programme lowering absent, acknowledges existing HEAD RTL/receiving entry; preserves GAP. Patch intel2:/tmp/codex-head-gap.patch sent merge (merge says publishing with HEAD entry).
- Remaining partial lower_head diagnostic independently still says HEAD consumer no netlist. HEAD owner requests narrow correction later; preserve PARTIAL: actual missing composed16slice NX/rstd timing, crossdie publication/transport/global identities and programme integration. Do not confuse source stage0/401 HOST words with receiving HEAD stage81/legacy417 ABI.

## All six current programme fixtures and jobs

All use strict0 bound data above, source5948fb8881, selected s13pfunc manifest, actual current source frame calendars R/fs_s13pfunc_bound_variants_v2. Explicit candidate OT_XS_GB_PROVIDER_UNDER_TEST=1 and OT_XS_Q_CPR=1; production provider remains blocked. Same die source /srv/opentallas-scratch2/claude/tok-ds-12-1027/veh/tree_b178, fixtures /srv/opentallas-scratch2/claude/tok-ds-7-1027/fix_r0. Frame current cal source admission all3used masters PASS; physical source metadata-only r2 changes no lane cycles.

1. L0 compile TERMINAL FAIL rc1, intel2 launcher833974, intel1 unit oth-ubuntu-1465475-1793263848. Controller log intel2:/tmp/codex-tok-s81-compile-L0-s13r.log; R/compile_L0_s13r.log; R/cc_L0_s13r_current/cc_L0_su.err. Real failure CalendarFault at xs_calendar_pack.split_intervals for attn.wq_b phase0: end230, next launch229 (hi-20=209), no fixed20edge PRIME idle gap. No override/relaxation applied. R/compile_L0_s13r.sh.
2. L2/L14/L20 initial batch includes initial HEAD/MTP invalid labels. intel2 launcher915318, unit oth-ubuntu-1497655-1793264023; controller /tmp/codex-tok-s81-compile-remaining-s13r.log. Outputs R/cc_remaining_s13r_current; R/compile_remaining_s13r.log.
   - L20 TERMINAL FAIL rc1, SAME exact PRIME failure attn.wq_b/0/230/209.
   - L2 TERMINAL FAIL rc1, SAME exact PRIME failure.
   - L14 STILL LIVE at park, actual compiler PID intel1:1499363 (time parent1499355). No error at last check. Check R/cc_remaining_s13r_current/cc_L14_su.{log,err,time} and batch log. DO NOT KILL/DUPLICATE.
   - Initial HEAD/MTP rc2 argparse failures diagnosed: labels must head/mtp_draft; no compilation occurred. Retained logs in this batch.
3. HEAD/MTP corrected-only rerun TERMINAL rc0, intel2 launcher937369, unit oth-ubuntu-1510488-1793264093; controller /tmp/codex-tok-s81-compile-special-s13r.log; R/compile_special_s13r.log; R/cc_special_s13r_current.
   - HEAD8ops,4PARTIAL/4GAP,98rows/98templates. Partial head.hc_pre+norm has existing80/80 rstop_xo egress but composed16slice NX/rstd dates only plan xfin16=234. lm_head/argmax/merge/token.return GAP final-layer publication/programme integration. Exact output R/cc_special_s13r_current/prog_HEAD_su/{lowering,schedule,manifest,bound_data_links}.json and prog/{calendar,ctl_templates,gunit_rows}.json. Sent HEAD/serdes full paths, no global authority or transport dates inferred.
   - MTP11ops/11GAP,0rows/templates. Missing actual draft programme lowering, same HEAD-family boundary.
   - R/compile_layers_six.sh is exact fixed runner; compiler source W2 unchanged.

## Actual native BoundDie control vehicle attempt (not legacy adapter)

After strict0, launched source inventory + current native BoundDie control composition (no elab). intel2 launcher1046197, unit oth-ubuntu-1565666-1793264414, controller /tmp/codex-tok-s81-native-control-s13r.log. TERMINAL FAIL rc1 BEFORE control compile, because guessed logical child paths u_s_N{S,N}.u_xg/u_xr are absent. R/native_inventory_s13r.sh, R/native_units_s13r.json. Uses R/native_local_timing.json copied from original measured results/token_pass/bound_control_1026/timing_all_v2.json, with actual source hash/define guards (not relabeled). No new timing adoption.

Exact diagnosis from emitted source: interior slice child comments include u_s_1S.u_lp.u_xg/.u_xr (and u_s_1N/2S/2N etc); end slices u_s_0N.u_sl.u_xg and u_s_0S.u_sl.u_xg. Need derive ALL exact paths from current selected source rather than blanket prefix, rerun inventory once, then source-qualified native control. No retry launched after park. Existing strict output has actual source path comments. Old logical tree used for data compiles emits141 legacy unlanded-vehicle warnings; those are NOT current strict binder failures and do not establish current RTL vehicle replay. NativeBoundDie is the next path to avoid treating old geometry as actual source. No current actual full-die RTL replay yet.

## Die owner handoff details

- Exact LP emitted intel1:R/bind_s13rfunc_reset/out/rtl/s81p_dsdv_slice_lepw_mus_LP__t2.sv:459:
  as-built u_s_0S.u_land; dsdv_mu_land #(.NB(80),.NS(1),.SRAM(1),.W(1104)) u_u_land.
  clk(clk), fault(w_u_land_fault), rc(unit_i0_q[10:0]), rd(w_u_land_rd), rst_n(lepk_i0_q[0]), rv(w_u_land_rv), wd(d2_u_lep_ml_wd[1103:0]), wv(d2_u_lep_ml_wv[0]). Sent S81 owner.
- Actual asbuilt natural child parameter read (no flatten/elab), job4165026 terminal0. R/natural_child_actual_params.json: ot_s81sl_kv_leaf g_kv.u_kv CNIK1/CNIK_MUT0/CP1/CP_MUT0/HARD_RQ0. Do NOT assume HARD_RQ1 natural hard children current. Four LP u_land actualinstances all1104/80/1/1.
- CGR0logical versus8physical exact current tuple proof owned S81/cores commit2cd2942ff:57044/57044 EQ,60125 statebits,43primary+ROMports; wrong-XOR gate control caught1unproven.0cycles. Earlier constant-gate mutant was INVALID KeyError, retained. Narrow qualified patch transferred by cores intel2:/srv/opentallas-scratch2/claude/codex-s81-cores-1028/cgr_2cd2942ff.patch; merger owns collection. No blanket param ignore/physical SIGNED claim.

## Open tasks and questions

No new OWNER decision needed from this lane. Existing ROWX map/lot/root-pair producer/storage questions remain with their existing owners and defaults OFF. S81 owner handles cut/PG domains/unsigned caps/physical hold. HEAD owner handles actual receiving entry/physical; token compiler still owns actual final-layer publication producer and transport composition. BF namespace remains unqualified where actual leaf electrical/reset mapping differs (h9 r0 u_e4 clock/x0 changed); do not add blanket BF INSTANCE rule. GB provider default guard stays blocked despite current frame component pass. New capacity/PRIME failure must be resolved with exact events/capacity/reader proof and priced if timing changes; do not disable CAL_SEGMENT or make unknown ages0.

Next priority for Claude: collect active L14; resolve whole-class PRIME reader segmentation failure (L0/L2/L20 same); derive exact native inventory paths and regenerate actual BoundDie control; then actual source/producer lifetimes and RTL token/component work. Safe committed source is already pushed; unfinished calendar candidate deliberately uncommitted and not READY.
