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

## State 08:40 PST (supersedes earlier state blocks)
- ALL FOUR ROWS ARE IN THE D28 COMPOSE: KV-PLAN-R6 dry10 (16 rows) has R1, R1b, R5, R5c APPLIED (intake kv-plan-r6/d28/rows/: R1 9860691ee0da,
  R1b 74bdc3ee5a86, R5 6281f8f48b0a, R5c 6e86608e1250, helper kst_xstreet_v3_fkd.py 095576e60380). Its rehearsal rh8 (plan 97a61b154060) is the
  gate of record: G0 1 error = kv3_pv_v3 landing band (PV lane), bind errors = 60 R8_STALE / R8_UNCOVERED on the PV split (PV lane / plan lane).
  Nothing on my rows; hg findings there: routed_reach 18, station_core 10, tap_sink_cap 2 (hg_v3 clk_t52 5,347 and clk_t36 3,372 > 3000).
- My gates: gate_a1 GREEN (R1+R1b), gate_b3 GREEN (R1+R1b+R5 v2+R5c, plan 01eb79c44cd6, tree_a). gate_c3 / gate_c4 (tree_b, plan lane dry7
  compose) stopped by a foreign kv3_pv_v3 finding; abandoned in favour of rh8.
- Kit: kv3_io_cor_v1 sealed private kit on tree_a (plan 01eb79c44cd6), goal finish. Runner intel2 user unit fkd-kit-iocor-1122, log
  ~/tmp/fablekvdie/kit_iocor.log; work epyc8 .../kit-wave/qwen_kvsys/KV-D27d3/private/FABLE-KV-DIE/kv3_io_cor_v1_1122075221; place since 08:06.
  Durable waiters (re-run the same command to read them): ot-wait --durable --kit <work>/gen/kv3_io_cor_v1 --host epyc8 --stage place | finish.
- tree_a FEEDS THE KIT: never gate on it. tree_b (51 GB) is no longer needed: ot-delete refused it (lane dir protected by the private spec);
  retry after the kit ends. Also deletable then: leg1-3 plans, gate_* aside dirs, r5* trial dirs.
- No private hg / pv kit from me (posted 08:30: hg needs R6h + R5 bound = D28; pv waits on the PV lanes).
- NEXT: (1) read the io_cor_v1 kit (place -> finish; cancel only if measured unable to sign). (2) After D28 applies: first kv3_hg_v1p2 D28 kit GRT
  overflow vs 566k / 871k (FLOW-CLKGRT-R2); hg_v3 taps with TAP-GRID-R5. (3) D29 candidates still open at die level: pv in-tile re-floor (R3),
  hgi array north (R4), band re-site at pins for the lite rings (R2), sys_c place region (HUBC-SYSC-R2), street_rule tool limits
  (event JSON crash line 3073; cannot re-floor pv / hg / hgi). (4) Main: RING-LITE-2 e08eb28ae039 pushed; lane clone epyc8 fable-kv-die/repo.
