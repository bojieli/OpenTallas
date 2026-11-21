# PLACE-PRECHECK-2330 handoff (started 2026-11-20 23:2x PST)

Tool: tools/die_plan/place_precheck.py (main 8dc180ca4f), test_place_precheck.py (7 tests); hook: tools/precheck/precheck_hook.py posts a PLACE-PRECHECK line after every plan apply (--no-place to skip). Report only, never a gate.
Modes: `--plan PLAN.json [--jobs N --out DIR]` all types of a plan; `--kit KITDIR` generated kit (reads ft_bit_sites.tcl, istations.tcl, config.mk; with run/results/*/base/1_2_yosys.v also MPL-0020 + cone).
Run heavy via ot-run on the host that holds the plan (plan 60-150 MB, 6 jobs, --mem 48; needs --stage of the lane clone). Lane clones: epyc2/7/8/9/10 + intel2 /srv/opentallas-scratch2/claude/lane-place-precheck-2330.
Data/results: <host> /srv/opentallas-scratch2/claude/place-precheck-2330-data/<label>/place_precheck.{json,tsv}; kit copies intel2 .../kits.

## Determinism per emitter
- OVERLAP (kit_istations PACKED_EXACT_BANK_TCL via face_flops ff_hits_explicit): deterministic from plan (ft spread sites, exact bank sites, macros, core) - yes. Packed receiver form (u_lpad_*) confirmed only by bound RTL (plan mode is a candidate test).
- KNEE (is_knee_site): deterministic from plan pins/leaf; kit uses real BTerms, so +-2 um (plan 404.76 vs kit 404.712); NEAR band 397-403 reported.
- MPL-0034/overlap (kit_fit): plan. MPL-0020 (macro not in netlist): needs the SYNTH netlist (synthesis drops unobservable macros) - not decidable pre-synth.
- CONE (ot_pr_cone): needs netlist; since 124d829 an unseparable cone drops its region, not a kit stop. Approximate (FIRM cells unknown, 5926 vs 5925 members).
- Not static: PLACE-HPWL (global placement result), DPL-0033 (legaliser), infra kills.
## Validation
- 7/7 failed QC OVERLAP kits flagged to the coordinate (u_lpad_rs_s1 267.84 73.44 / 241.92 293.76 / 406.08 432, rs_s0 238.464 535.68); 3 QC kits that passed place not flagged.
- R4A4 plan: 11 OVERLAP types = the failed set; KNEE: sle_su_c, slw_su_c cl19bb38ef/cl92142dac (x_sc_o 404.76), sle_ctl cl67434795 403.122 (kit 403.122) - all 4 failed knee types.
- S81 serdes__t14 cone flagged (47408 vs kit 47400); svc_rs__t4 MPL-0020 flagged (g_m[2] wq mem).
## Current-event results (posted): S81 J5 live + J6 C1d/C2d/C3c/C1n (395 types each), QC V2b, KV D25e3/D26/D27c, HEAD r16: 0 plan-decidable findings; QC V1 R6V1: 3 fe types knee. Posted to QC-PLAN-R8, KV-PLAN-R3 (-> R4), S81-J6-ASSEMBLY. STOOD DOWN 11-21; rerun: ot-run on the host holding the plan, place_precheck.py --plan P --jobs 5 (mem 24 is enough). Open: MPL-0020 + cone need a synth netlist (kit-mode); not wired into G0 except via precheck_hook place_check.
