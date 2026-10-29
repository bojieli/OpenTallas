# DIE-QC-33 BIND (2026-10-29): QC functional candidate strict bind FAIL242 -> PASS (0 errors)

Inputs: narrow extract of results/token_pass/qc_functional_0845 from codex/qc-functional-0845@63d7fd532 (no other
ancestry); tree = main f483150e0. Elaboration reused from Codex elab2 (unit 3507624, b409cccdd; rtl/ and tools/die_plan
bind code identical to main except bind_elab.py + one KV-only file), copied to the run dir with the source-path prefix
relocated to this worktree (original sha256 list kept in the run dir elab_orig.sha256).
Run dir: epyc2:/srv/opentallas-scratch2/claude/die-qc33-bind (ot-run --hosts epyc2, 48 GB). Failed runs kept:
failed_1 (plan copied without its plan-relative hard-core pin tables -> ResetError, fixed by the cores symlink) and
failed_2 (1 error, below).

## Chain (run.sh, status.txt)
P  prepare_paired.py = Codex prepare.py + TOK-QC-2 generator rule ca_pair_rule.py on the native CA bind_clock before
   annotate_table, then count_align_bind.verify: identity/loop errors 0, window violations 0, margins 108.0/341.1 ps.
   RS0 9->10 (1 step), RS1 8->12 (4), RS2 8->12 (4). CA ports changed vs raw plan 225, aggregate -159 port-cycles
   (Codex unpaired: 234 / -168; aggregate port cycles are NOT token latency).
0  gen.py latency --inplace (canonical latency.lanes rebuild): 213 lanes' clock_landing/cycles re-derived (CORRECTED 10-29 by NUMBER-CHECK-QC-1; earlier text said 216 = the error count).
1  probe bind (recipe minus land_align/land_r8_extra/param_regen): 0 errors.
2  gen.py latency --groups probe/bus_groups.json -> fresh r8/ (9050 members, 2237 padded, 900,320 pad FF, max pad 20).
3  base bind (fresh R8 + INNER witness candidate_inner.json + coll_regen): 0 errors.
4  cb16_pads.py on base -> cb16_pads.json (336 members, 232 INNER, 864,548 pad FF).
5  final bind --strict (fresh R8 + fresh CB16 + INNER witness): **0 errors**, 377 parts / 119 types / 1921 crossings /
   790,393 bits, unbound/tied/undriven/multiply 0, 0 type splits (final_out/bind_report.json). CHECKED (own run).

## Root causes of FAIL242
- 216 LANE_LANDING_LATENCY errors (the latency regen rewrote 213 lanes, NUMBER-CHECK-QC-1): plan latency.lanes stale after the native CA update -> step 0.
- 25 TYPE_SPLIT (ibus) + 1 EMIT: stale R8 (r8_previous) / CB16 (cb16_previous) pads made per-instance in-bus pads
  differ; gone after the fresh R8/CB16 regen (steps 1-4); EMIT inventory follows.
- failed_2 (after the above): 1 PARAM_REGEN coll_regen RS0 core->face 20 vs face->core 21 stages: Codex prepare.py did
  not apply the TOK-QC-2 paired-direction rule to the native CA table -> fixed in prepare_paired.py (generator rule,
  no hand pad).

## Not done / not claimed
No bind verify / portbind / GEN / timing / physical claim; plan not adopted (Codex candidate status unchanged).
The pair rule adds +9 count steps on RS0-2 chains vs the unpaired native table; the model must price the RS relay
depth (coll_regen RS from final_out/param_regen.json).

## QC-IMPORT-3 clock polarity (cited, not re-run)
polarity_qc_import_3/polarity.json = copy of intel2:/srv/opentallas-scratch2/claude/qc-import-1/polarity/polarity.json
(sha256 3dde8a5f4c51...; that file is on no pushed branch): PASS, tap_A_true 921 + tap_Y_true 2,345 = 3,266 stages, 0
inverted-phase, 0 stage/partition/link errors, on bound odb 60d6fc07 (QC-IMPORT-3 own run, CHECKED by that lane).
