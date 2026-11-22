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

## State 08:00 PST (supersedes earlier state blocks)
- D28 intake (kv-plan-r6/d28/rows/): R1 9860691ee0da, R1b 74bdc3ee5a86 (in rows.json, APPLIED in the plan lane's dry7 / dry8),
  R5 6281f8f48b0a, R5c 6e86608e1250, helper kst_xstreet_v3_fkd.py 095576e60380 (ROWS-READY posted 07:5x; plan lane decides D28 vs D29).
  ORDER: R5, R5c after HGI-R6 + TAP-GRID + R1/R1b, before the landing_remap.
- Gates: gate_a1 GREEN (R1+R1b). gate_b3 GREEN (R1+R1b+R5 v2+R5c on tree_a, plan 01eb79c44cd6). gate_c3 on tree_b refused by a foreign
  pv_v3 finding; gate_c4 (pv_v3 at base) queued behind gate_c3's G0: intel2 ~/tmp/fablekvdie/gate_c4.otrun.log, epyc8 fable-kv-die/gate_c4/gate.sum.
- tree_a now FEEDS A KIT (do not gate on it again): sealed private kit kv3_io_cor_v1 (LITE variant), spec
  ~/coord/autopilot/private_specs/FABLE-KV-DIE/qwen_kvsys_kv3_io_cor_v1_1122075233/spec.json, runner = intel2 user unit
  fkd-kit-iocor-1122 (log ~/tmp/fablekvdie/kit_iocor.log), work epyc8 .../KV-D27d3/private/FABLE-KV-DIE/kv3_io_cor_v1_1122075221.
- tree_b = D28 work tree fork made by ot-tree-fork; the tool exited 1 at the very end (source bind_of_record moved by the plan lane during the
  copy); content equal by file count except bind_of_record, renamed from .forking-805612 by me, --verify OK.
- NEXT: (1) gate_c4 result -> post. (2) hg kit: private-spec qwen_kvsys kv3_hg_v1p2 --tree tree_b (has R6h reset rows) --host epyc8 --goal finish,
  run-item under systemd-run --user; compare 5_1_grt overflow with FLOW-CLKGRT-R2 (566k clock-first / 871k base). Only after gate_c4 binds.
  (3) ot-wait --durable on both kits. (4) After D28 applies: re-check hg_v3 taps with TAP-GRID-R5; pv R3 / hgi R4 geometry with the family lanes.
