# QC-PLAN-R4 handoff (2026-11-20 ~10:05 PST)

## Live state
- QC live event s29q103S4Q9N46R4A4 (applied 09:35). Receipt lanes/handoff/qwen_compute_atomic_apply_1795196108749764477.json.
- Sealed bind epyc*:/srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_n46r4_a4_bind_1120085722: 133/133 types, OUT-SYNC hash 82aa5e602c0b on 6 hosts. all_items review-before-route fence kept.
- Wave adopted the tree 09:37. 31 A4 type launches from 09:43. Old-plan running kits are SUPERSEDED-KEEP.
- Cancelled coll_core-992477 (epyc10), recorded in lanes/CANCEL-UNSIGNABLE-1120.tsv.
- Diagnostic gen-only rerun for FLOW-NOADV-0915: intel2 ~/qc-plan-r3/kits_v0e/r4regen_e.log (epyc9 queue, current rt, RESET_IDENTITY detail).
- Leftover copy epyc10:/srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_n46r4_a4_postbind_1120090951 (ot-delete refuses a partial delete in the source tree). Asked FLEET-OPS-R2; do not remove it yourself.
- E3 rs_s1 51-site reseat is owned by QC-SUST-MACRO-1119: epyc7 .../r4_direct/gen_representative_a3_retry/sust_e3_s1_reseat_{shadow,evidence}. The st_a M5 halo route pilot follows its place-only result.

## V1 (cut ~11-21 09:30 PST, target strict 0)
Work dir epyc9:/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/n46/v1_cbc.
- Candidate: v1a_glue_x3_corrected_plan.json + v1a_glue_x3_corrected_sidecar.json.
- Strict script: v1a_complete_strict_a4.sh, launched by intel2 ~/qc-plan-r3/v1a_exact_strict_a4_launch.sh.
- Result: strict_v1a_glue_r4_a4 has 32 errors: PARAM_REGEN 1, R8_STALE 30, EMIT 1.
- Note: the strict script still copies the base snapshot qwen_compute_n46v0e_s2. The live base is now qwen_compute_n46r4_a4; switch to it.

### Error 1: fabric tree imbalance (PARAM_REGEN qc_fabric_transport W5 S; R8_STALE follows from it)
- Cause: the global300 repricing raised fixed_cycles on 168 of 288 c_*_b[nf]_* fabric lanes (+1 on 48 lanes, +2 on 36, +3 on 36, +4 on 48).
- Per join, the change between sibling legs (A4 to V1A) differs by only 1 or 2 stages at all 96 tree joins (epyc9 v1_cbc/r4_join_deltas.txt). The differences accumulate up the 4-level Morton tree plus the column entries to 14 stages at the root, so the fabric tree-balancing step's column pads (max 9) cannot balance it.
- COORD ruling: no 14-stage pads of 516-bit words. Pad a join only where the leg difference is 2 or less. Make the legs symmetric through placement plus spread/region rows.
- Options:
  - (a) Same-level uniform: give every leg at a tree level the max cycle increase of that level. This is legal under 300 um and adds latency, but no local imbalance.
  - (b) Placement: re-seat tree-node hosting partitions (c_<s>_bn_<cr>) so sibling legs are equal length under 300 um.
  - Check (a) with view-only pricing first. Tools: v1a_fabric_local_balance*.py and v1a_fabric_join_audit.py (Codex). The draft at fabric_balance_a4/local_pad_minimum_from_bound.json is rejected.
- Lane cycles are lanes[].fixed_cycles in the plan, for example c_W5_bn_11__a00 4 to 6 and c_W5_bn_01__b00 9 to 13.

### Error 2: EMIT cbf_q00__cl1b5a6458.y_o11
- A writer START raw reset rr_t102 drives an output port. Add a registered (non-port) relay in the plan (COORD ruled yes).

### Then, in order
1. First-rank seating on the remaining long hops (pattern: West FE attempt_5, 744 to 190 um, 0 added cycles).
2. Spread/region rows for the sle_ctl and coll_core x 300-600 GRT demand bands.
3. stm_v2 retap plus lockup.
4. cbn density taps.
- sle_ctl class (lanes/handoff/FABLE-SUPERSET-0415-step1-rows.json) waits for UNIFY-TOOLS step 1 on main.

## Rules in force
- 833 ps; one plan event per 24 h; G0 compared against control before apply.
- Apply only through publish_apply with bind-first seal and OUT-SYNC (see intel2 ~/qc-plan-r3/apply_n46r4_a4.sh).
- Post every 2 h. Next post due ~11:45.
