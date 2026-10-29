# QC-A0-KITS-11 (2026-10-29): A0 early-tap accounting, flow-release path, NL parent placement

## 1. Which signed views unblock which early taps
- g24 freeze gate (results/die_qc25_1028/g24_sta_gate.log, CHECKED read): early_core_taps 864, real view 84, missing 780 (TT and FF).
- Breakdown (DIE-QC-21 README, committed; I did not recount it): 720 taps on qfd_tile_nk_a0c, 48 on qfd_tile_nl_a0c, 96 on su_c.
  The su_c types now have views for 84 taps, so 12 su_c taps (btab) remain. 768 + 12 = 780.
- Taps unblocked by each view:
  - NK parent (qfd_tile_nk_a0c) signed view: 720 taps. Needs node + romleaf + rawleaf, all physically signed off now. The NK recipe is not generated yet (it needs node-collar/reset planning).
  - NL parent (qfd_tile_nl_a0c) signed view: 48 taps. Needs romleaf + rawleaf. Fresh-gate LEC FAIL 57 (stale correspondence), placement below.
  - node / romleaf / rawleaf: 0 taps directly. They are the parents' hard children.
  - btab (su_c): 12 taps. DIE-QC / CORES-EARLY owner, not this lane.

## 2. Flow release (autopilot resolve_provenance replicated: canaries.json watch + exclude + QC die_plans filter; CHECKED)
| view | AP id | src | watched flow identical to | QC canary on that commit |
|---|---|---|---|---|
| romleaf a0k7s | f6f8b3444406 SIGNED-UNVERSIONED | claude/qc-a0-kits-7-1028@02a7e51649 | main 410e940f4 (0 files) | qwen_compute_410e940f4_1028_200604_637036 NO-REGRESSION |
| rawleaf a0k7s | 53fcde6a6c40 SIGNED-UNVERSIONED | claude/qc-a0-kits-6-1028@9a80f1465b | main 8e38d8187 (0 files; the commit of flow-20261028-x-hbm) | qwen_compute_8e38d8187_1028_183558_148502 NO-REGRESSION |
| node a0k10t | none (AP ba7c5b18f1e2 was a GRT-only trial; routed via lane continuation) | view provenance src_commit d9716851c (kit generated at 662af204d) | nearest canaried main a87cab8e95 differs in 2 files: parent_trunk_insert.tcl (opt-in ICG_INST; not referenced anywhere in the node kit) and rtl_lint.py (opt-in OT_RTL_LINT_FLATTEN, default off; the node kit ran the 662af204d copy before synthesis) | none of the 58 QC canaries scanned matches 662af204d or d9716851c |

Node caveats (for an honest release record):
- Routed through lane scripts (results/codex_qc_a0_2340/node_tail/{final_tail.tcl,node_continue.sh} @d9716851c): warm GRT reuse plus a final FF hold repair with clocks frozen (56,548 clock guide rectangles unchanged), then the ORFS do-5_2_route..do-finish targets. This was not an autopilot finish, so there is no SIGNED-UNVERSIONED record for retry_unversioned to promote. It needs a narrow ROOT-MERGE record, like the KV e1 claim correction.
- The node kit's orfs_hold_mm.tcl is the pre-a615f444b copy (sha d8c3df3a). tools/orfs_hold_mm.tcl is not on the canaries.json watch list. This is INFO for FLOW: no new gate.
- Frames are not mixed: the standard-kit-frame TT +52.36 / FF +5.52 are the numbers of record. Raw FF SDC -34.43 stays as recorded.
- 0.665 V droop INFO (epyc2 codex-qc-a0-2340/node_droop_info/signoff.json, CHECKED): nominal SIGNED, droop TT -18.67 (delta -71.03). INFO only, not a gate. Node TT +52.36 is above 25, so the rule did not require this run.

## 3. NL parent placement (fresh reset-cleanup gate, diagnostic only; no CTS/route)
- Codex run unit1546057 failed at 3_5 with `missing anchor u_g.t_out[512]$_SDFF_PN0_`. The fresh synth removed the redundant reset mux, so t_out[513:512] are now `$_DFF_P_`. 2 of 14,257 anchor names were stale.
- Fixes (anchor_targets_vs_be5c065c5.diff, 21 rows): renamed 2 rows; moved 19 u_me.mq_wrom capture targets out of the pile at the macro corner (196.088, 653.44 / 657.9) into the free channel column x 201.5-213.5, y 628-640. All other targets are unchanged.
- Final AUTO-GEOM (geom_rules.py main, --all-kits, M7; nl_reset6_auto_geom.json, CHECKED; render nl_reset6_place.png VIEWED):
  r2r max 404.35, 0 captures > 405 (Codex old gate: 887 / 734.24), relay_collapse 0, pin_reg p90 9.0 / max 143.5, unregistered 0, cells_on_macros 0.
  Still flagged: aspect 2.528 (parent slot), partial_face E/W, channel_h 0.70, channel_v 1.50, col_v 1.82 at x 260 / y 527. The column flags are estimates; GRT decides. They come from the 1,024 mq_wrom ROM-weight captures that run down both edges of the central channel. clock_reach 762 is pre-CTS.
- Still open: no route or adoption until the fresh-gate full native LEC passes (57 stale KV-address correspondence hypotheses, intel1 codex-qc-nl-lec-1029/reset_newgate*).
