# HBM bounded parent: q_spb2

Updated 2026-11-06 06:09 PST. Owner hbm_parent; canonical plan owner hbm. Two real signed xcal children; diagnostic local parent, no die/global-bind/token closure. ROOT=/srv/opentallas-scratch2/claude/codex-hbm-parent-1106 on hub/E2/E6.

## Current live attempt

Intel2 dedicated scratch2 PLACE unit **oth-ubuntu-1669213-1793975244**,24GB8CPU20GB, ROOT/prep2_epoch_reset/gen/q_spb2. Log local coord/tmp/codex-hbm-parent-1106/prep2_place.log. No route. Prior1164857 stopped at exact-bank epoch count; all passed native source/reset/2child assembly reused, no fullbind.

Successor GEN1565300 PASS. Strict Slang elaboration now PASS; actual full LEC against prior mapped netlist running1586479 at ROOT/prep2_epoch_reset/gen/q_spb2/lec_against_prior_synth. Previous frontend actual2/2signed children+20/20stations; same selected source/type and no cycle/geometry change. Exact partition freeze/pin hashes match previous viewed plan/detailed bank image; REVIEW.md in successor root.

Diagnosed actual failures and narrow fixes: schema native_width missing5736 now merged; stale wrapper dead-input receipt913 + explicit partition module inventory563 released28fc/bj. Actual first PLACE then failed because unused input epoch FF was pruned. Plan owner explicitly permits missing epoch ONLY after proving whole cone unobserved, while every payload FF remains required and W+1 site stays reserved.6045dad66a4 implements source-sealed proof, observed-epoch and missing-payload negative controls PASS. Actual L49/L83 epochs unobserved, output epochs observed. No KEEP clock/reset load or invented dependence.

LEC UNPROVEN was actual duplicate bound-only rst_o_0 vector last declaration/connection from canonical kit_rsync.1beec76e2dc fixes idempotent scalar/[0:0]/last-pin normalization; actual Slang now clean. Both1beec/6045 READY on codex/hbm-parent-resume-1106; merge owns release. Original failure receipts preserved; LOCAL/globalFAIL1 remains explicit.

## Previous actual result and remaining failure

E6 PLACE unit oth-ubuntu-1429122-1793955200 finished shell0 and async LEC0. SYNTH 69,585 stdcells+2 real macros; PORT_BIND12505/12505, FACE_GUARD0fails, fanout>64=0. Final actual DB ROOT/xcal_gen_rstport/q_spb2/run/results/asap7/dp_q_spb2/base/3_place.odb and rendered ROOT/xcal_actual_placement.png preserved. No route launched.

Actual reset subgate FAIL: isolated generation expected u_rst_root, while native source has relayed u_rst_in,23 taps and rst_o_0 at depth9. Correct next preparation uses original full reset context hbm-bind-9/m79fp/die_plan.json with entry relayed/depth8/release9. Shell0 never cleared that failure.

## Next preparation READY

Provider3b2dda053b4 + phase helper b9dccb67643 + consumer9e0ca4bb878 are merged in current main. New read-only component proof is explicitly LOCAL_COMPONENT/source_preparation_only; global g_t11m79f FAIL1 (unrelated q_hub_nw reset emission) stays verbatim. No native_topology receipt, borrowed top, global PASS or wave-route waiver.

Actual proof ROOT/component_q_spb2_v1.json PASS: original selected source,27ports, unique defaults82/83/210/211,23reset taps+out all depth9,104edges, phase-aware native contract. Actual kit emission from ORIGINAL g_t11m79f without bound_top PASS, narrow99->28 dead-input proof PASS, two sealed DD256/PAW11/PREL1/XSLOT1 BB joins PASS. UID/width/reset-shortcut mutants all refused. Source inspection and local preparation only.

Previous fleet prep handoff (superseded by current live attempt): Exact E2 overrides ROOT/q_spb2_component_overrides_v1.json: original g_t11m79f, above proof, bind_context ROOT/bind_context_banks20_taps/die_plan.json, original m79fp reset context, exact existing assembly contract. Prepared plan ROOT/xcal_subplan/die_plan_banks20_taps_TRIAL.json. KIT-owned stations require no80type rebind. Fleet coordinates actual disk reservation with TOKEN.

Released shared fixes: e88 native-width proof guard; d918 authoritative hard-child classification;607 actual selected BB staging before sealed assembly, all already on released source. Consumer preserves LOCAL/globalFAIL metadata and mandatory census/inventory. Prior v1 transport and v2 missing-local-BB failures retained and diagnosed.

## Reviewed geometry and cycles

ROOT/combined_banks_taps_DRAFT.json +PNG and banks20_taps_review/REVIEW.md are current.4275new FF slots incl epoch placeholders, actual .054site/.270row,1.404x.270 footprint; no mutual/original FF/197114actual WELLTAP/halo overlap.100 prior tap collisions repaired; old uniform-W output draft explicitly REJECTED. Cmd_ext exits E, kv_desc S.1770 actual soft FF sites frozen; loops_q13 moved+.54um clear of halo. Max payload L1 input385.311,L75267.246,L76271.620,L87305.748 <=403um. Remeasure actual placements.

Conditional stage vector L75+8,L76+5,L49+3,L83+3,L87+1,L40+0; never blanket+20/op. Physical L83 remains99, native28 with proven dead spares. HBM40 signed-shell+2 command/response and reset+2 remains separate; HBM42 stage/calendar price conditional. Owner alone adopts canonical event after actual phase/physical joins. Existing signed views unchanged.

After release: fleet prep -> inspect generated reset/stations/assembly and render -> actual LEC/PLACE after review -> measure landing/reach/reset. Approval is PLACE-only, no route. Internal route ceiling remains M7 if later authorized.

## Other join and cleanup

SU q_su21 retained old plain4 MLAT4 versus signed16lane1 MLAT5; prior attempted join yielded0actual lane1 macros. hbm owns phase/enable semantic proof, kit_assembly common composition; no invented outputs or false SU route.

Only own abandoned duplicates removed: hub old parent/station worktrees + narrowed remaining worktree (~.536GiB), E2 old own checkout (~.127GiB), E5 unused gen copies85.3MB. Final E6 PLACE/LEC, exact signed views, current source/model/proof and important failed joins preserved. No jobs killed. Active original m79f/m79fp/asbuilt closure must stay. Own current code tree hub /srv/opentallas-scratch2/claude/wt/codex-hbm-view-stage-1106 branch codex/hbm-parent-resume-1106.
