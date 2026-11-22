# FABLE-KV-DIE handoff (Fable die-level lane, KV qwen_kvsys). Updated 2026-11-22 04:45 PST.

Goal: remove the KV die stall with ONE die-level D29 change; hand rows to KV-PLAN-R6; launch sealed private rep kits (top 3 families).
Report: lanes/FABLE-KV-DIE-1122.md. Posts: lanes/posts/FABLE-KV-DIE.md. Client logs intel2 ~/tmp/fablekvdie/.
Work dir epyc8 /srv/opentallas-scratch2/claude/fable-kv-die:
- check/ street_rule check of D27d3; leg1/ leg2/ leg3/ = street_rule legalize DRY runs (private, --no-bins); sr_wrap.py = JSON-safe wrapper.
- repo/ = lane clone (main 58ebc21a50 + RING-LITE-2 patch, NOT pushed yet): clock_landings.py, schema.py, die_plan.schema.json,
  test_landing_ring_lite.py, rtl/test/meso/lite/{tb_lite_csc.sv,run_csc.sh}. Tests: t1/ (bench csc + lite), t2/ (pytest).
- tree_a/ = ot-tree-fork of kw45/src_kv_d28_work_r6 (D28 work tree, tools rt 6d2e187f0d65, plan dry5 fcfa38bdb65b). Gate runs go here.
- tmp/ scripts (ringcount.py, difft.py, patch_lite.py). Local scratch copy of rows: scratchpad kvdie/rows/ROWS_FABLE-KV-DIE-R1.py.

## Findings (posted 04:3x, bb10f4a1d7)
Area is not the stall; per-lane landing rings (1,188 of 2,006 bands <= 16 bits, 1-bit ring = 811 cells / 200 flops, LITE = 88 / 18) and
tiles 3-5 reach lengths across with cores 9-17 um off the edges are. street_rule legalize cannot re-floor pv/hg/hgi automatically.

## D29 rows
- R1 landing_ring_narrow on 44 unsigned types (script ROWS_FABLE-KV-DIE-R1.py PLAN_IN PLAN_OUT).
- R1b landing_ring_lite {max_width 8, monitors 1, status_copy true} on the same types; needs the RING-LITE-2 tool change on main.
- R2 band re-site at pins (after R1b bind). R3 pv in-tile re-floor, R4 hgi array north: geometry proposals to the family lanes.

## Next
1. t1/t2 green -> commit in repo (trailer Fable 5.2) -> ot-push-main.
2. tree_a: patch tools (tmp/patch_lite.py + dump-schema), install R1+R1b plan, PRE (baseline = tree plan before rows) + G0 + elab +
   strict bind --all-gaps + LATCHECK + BPC (KV-PLAN-R6 d28 gate scripts as the form; --priority plan --plan-job bind).
3. Read bind: LITE ring count per type, cells. Hand ROWS + evidence to KV-PLAN-R6 (ROWS-READY FABLE-KV-DIE <sha12> types=...).
4. Sealed private kits (kit_wave.py private-spec --tree tree_a --plan ... --lane FABLE-KV-DIE --goal finish; run-item under systemd-run;
   ot-wait --durable): hgi_v4, hg_v1, one pv (ask SINKSPREAD which). Do not duplicate family lane kits.
5. Fix doc: leg2 applied = 14 types (not 13).
