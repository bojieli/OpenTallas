# CODEX QC P3 / STM 2026-11-17 04:33 PST

Existing lane E10 /srv/opentallas-scratch2/claude/fable-fix-qc-hcfe, source src/, claude/fable-fix-qc-hcfe-1115.

## P3 changed-cause all-net GRT
Original p3_hold6_1116/route.log DRT0255 preserved. Correct actual-PG query p3_hold6_1116/guide_pg_diag_1117 (unit4069204 exit0) replaces broken $sb getBox with direct xMin etc. Actual PG and guide_pg_intersections.json:
- failed XL2_0 wd568 M6 guide y161.88..162.45 overlaps VSS161.664..161.952 and VDD162.048..162.336;
- failed XL2_4 _06259_ M6 guide y326.04..326.61 overlaps VSS325.824..326.112 and VDD326.208..326.496.
These are existing PG-cap zero-capacity rows. Previous helper re-GRT selected only14HB4nets, retaining369kbaseline guides. Confirmed stale-guide policy mismatch; whether this fully explains DRT0255 remains pending changed-route measurement.

RUNNING p3_fullpg_grt_1117/run.sh, E10 unit oth-ubuntu-4114904-1794918157,40GB8T; latest pinaccess100kgroups healthy. Same ins.odb,9HB4,RTL,placement,PG/clock/SDC;0cells/cycles. Clears ALL guides, ordinary all-net GRT under same PG cuts. Actual guide/PG image personally LOOKED, guide_pg_review.png + review.json.

NEXT terminal OT_P3_FULLPG_GRT_DONE + overflow0, python3 -I p3_fullpg_grt_1117/check_guides.py; render/LOOK fresh guides before DRT. p3_fullpg_drt_1117/run.sh + drt.tcl STAGED NOT LAUNCHED; guards fresh_guide_review_PASS.json. Then canonical finalRCX833 TT/FF; old final_gate.sh must be adapted to new routed.odb path, not yet done. Never infer old failures absent without measurement.

## STM BF16 exact candidate + fullshape paired CAD
Old Q6D STM51137f9010c7: true internal TT-53.45 wd_q97->lane_c317 deep33bit BF16 carry ladder. FF-99.49 is input feedthrough parent advisory; shown internal reset-removal rs2_g1->de_k0 -3.40. Current RTL retains old rounder.

Opt-in OT_QFD_BF16_CARRY exact low16 rounding predicate + parallel upper16 prefix increment; same rounding for ALL32bit patterns,0cycles/state/clock sinks/ports. Unified uarch_model.qwen_stream_bf16_carry_model BEFORE RTL. Pushed existing branch92245d98726. Defaults old RTL, NOT ADOPTED.

Actual-extracted RTL function SAT PASS plus wrong-tie mutant CAUGHT: src/results/qc_stm_bf16_carry_1117/actual_function_miter.sv,prove_actual.sh,actual_proof.log,actual_mutant.log. Independent identity proof also passes. No fullsystem simulation.

FULL production stream8lanes/4banks/32functional converter outputs,16621mappedFFs,6947pins,0macros; not reduced rounder, NOT parent STM physical qualification.
Paired frozen runs E10 /srv/opentallas-scratch2/claude/ref_gate/qfd_stream_bf16_{carry,base}_1117-20261117-122711. Controller PIDs4185901/4185902,24GB8T via ot-run, unlimited synth; ordinary2_4PDN healthy04:33. Same259.2x380.16 shape/budgets/clock; macro off/on only. Golden833/0/25; legacy route833/60/25 stricter. Old signoff.sdc833.333 is NOT release.

Mapped only: base50795cells/8005.70um2 vs carry50859/8017.79; +64cells/+12.09um2(~0.15%). Same741async+15880plainFF. Timing PENDING; mapped_pair.json.
Planning image personally LOOKED src/results/qc_stm_bf16_carry_1117/plan_review.png; review src/results/geom_review/qc_stm_bf16_carry_plan_1117.json. No new bus/macros/state; W/E259.2registeredrelay.

Controller bin/bf16_gate_scratch2.py fixes only obsolete root scratch path and exports image-extracted lane PDK. ctrlbin/ssh,ot-run relay via intel2 with preserved quoting. Source/helper snapshots frozen. R1..r7 infrastructure refuses retained; no prior CAD to duplicate.

NEXT collect CTS/GRT + specific wd_q->lane_c path paired timing. If slower reject. If beneficial: actual placed image review, ordinary paired DRT/final833 TT/FF, then parent-context source event before adoption. Default remains off.

## Other failures
Three ctl variants cl372cea1c/cl503337ff/cla4f6f12f share coll_core reset source identity mismatch; collcore worker owns class.
Parent QC owns coll_ucie attempt15 diagnostic.
No OWNER question or Fable review claim.
