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

## D29 rows (scripts epyc8 fable-kv-die/rows/, PLAN_IN PLAN_OUT form; apply in this order)
- R1  ROWS_FABLE-KV-DIE-R1.py: landing_ring_narrow on 44 unsigned types.
- R1b ROWS_FABLE-KV-DIE-R1b.py: landing_ring_lite {max_width 8, monitors 1, status_copy true} on 43 types. Needs main >= e08eb28ae039
  (RING-LITE-2, pushed 05:1x; unit tests + bench run_csc.sh pass).
- R5  ROWS_FABLE-KV-DIE-R5.py (COORD 04:5x hg central channel): 7 hg types, head e4/e5 + astk g_ex strips +43.2 um y via core_place
  --seed --no-search, then ft3 station banks rebuilt compact in the new street (y 561.6-602.1). RUDY H overflow v1p2 571k -> 239k,
  v3 516k -> 181k. env FKD_TREE / FKD_RT. Needs landing_remap + clksite_pinclear after it. kv3_hg (ft2, other corridor) NOT covered: open.
- R2 band re-site at pins (after R1b bind), R3 pv in-tile re-floor, R4 hgi array north: proposals posted to the family lanes.

## Gates (private fork tree_a = D28 work tree fork, plan base fcfa38bdb65b saved as base_plan_tree_a.json)
- gate_a1 (R1 + R1b, plan 6f866b1b34cc): launched 04:58 PST, unit via intel2 ~/tmp/fablekvdie/gate_a1.otrun.log; PRE PASS, ELAB 0; G0 + bind running.
  Summary lands in gate_a1/gate.sum.  tree_a tools carry the RING-LITE-2 patch (originals in gate_a1/aside).
- gate_b.sh TAG = R1 + R1b + R5 + landing_remap + pinclear, same gates. Launch AFTER gate A ends (one bind per tree):
  ot-run --mem 64 --threads 10 --disk 60 --priority plan --plan-job bind --hosts epyc8 --dir .../fable-kv-die
  --stage <D27d3 tree> --stage kv-d23-compose8/gatein --stage <d16 tree> --stage rt/3fc234318d37 -- bash gate_b.sh gate_b1

## Next
1. Read gate A: bind errors, LITE ring count (bind_of_record reset placements ring_lite), LATCHECK, BPC. Post.
2. Gate B. Then hand R1/R1b/R5 to KV-PLAN-R6 (ROWS-READY FABLE-KV-DIE <sha12> types=...), copy scripts to kv-plan-r6 intake as it asks.
3. Sealed private kits on the bound plan (kit_wave.py private-spec --tree tree_a --plan ... --bind-out ... --lane FABLE-KV-DIE --goal finish;
   run-item; ot-wait --durable): kv3_hg_v1p2 (compare GRT overflow with FLOW-CLKGRT-R2 566k / 871k), kv3_io_cor_v1 (LITE variant next to
   IOPC-R4's proof), one hgi / pv after D28 seals with the HGI-R6 / PV-R7 rows (tree_a dry5 lacks them).
4. After D28 seal (12:00 PST): re-run rows on the D28 final plan, re-gate, hand over for D29.
5. Open: kv3_hg ft2 corridor (y 213-232 over e0/e1); street_rule legalize cannot re-floor pv/hg/hgi (tool limits listed in the report).
