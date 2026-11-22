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

## State 06:45 PST (supersedes the Gates / Next blocks of 05:2x)
- COORD rulings: R1 + R1b go into D28 (scripts copied to kv-plan-r6/d28/rows/, shas 9860691ee0da / 74bdc3ee5a86, in rows.json by KV-PLAN-R6;
  D28 tree tools now rt bc9603f67b09 >= e08eb28ae039). Gate B / R5 also D28 if green by 11:30 PST. sys_c: slot kept, region form (posted).
- Gate A (gate_a1, R1+R1b on tree_a): ALL GREEN (see report section 7).
- Gate B (gate_b2, R5 v1 on tree_a): PRE PASS, G0 PASS 0 errors, bind running. R5 v1 is NOT for hand-over (kt rows re-routed straight:
  routed_reach 14 -> 58). tree_a is busy until gate_b2/gate.sum has END.
- R5 v2 = rows/ROWS_FABLE-KV-DIE-R5.py c48d8112743f (+ kst_xstreet_v3_fkd.py 095576e60380 beside it; env FKD_TREE, FKD_RT): core_place seed,
  kt rows restored then re-routed with HGI-R6's x-street generator (collapse / restore of spread kst sites), tap legaliser (hg_v3 clk_t52),
  ft3 banks compact in the street. Tested on kv-plan-r6/d28/dry6/step08_out.json: rc 0, 11 kt rows per type re-routed, max bit hop 383.4.
- R5c = rows/ROWS_FABLE-KV-DIE-R5c.py f0a8603e5923: kv3_hg ft2 banks 2-4 into the row channel y 248-320; model H overflow 331k -> 116k.
- tree_b = second fork of the D28 work tree (tools bc9603f67b09), forking (unit oth-ubuntu-805177-1795357448, --crit because of the load cap).
- NEXT: when tree_b exists: gate C =
  ot-run --mem 64 --threads 10 --disk 60 --priority plan --plan-job bind --hosts epyc8 --dir .../fable-kv-die --stage <D27d3 tree>
  --stage kv-d23-compose8/gatein --stage <d16 tree> --stage rt/3fc234318d37 --stage rt/bc9603f67b09 --stage kv-plan-r6/d28
  --stage opus-fix-kv-hgi-r6/gen -- bash gate_c.sh gate_c1 <latest kv-plan-r6/d28/dryN/plan_D28.json> <ledger>
  (base = the plan lane's newest finished compose; gate_c.sh does R5 + R5c + ONE landing_remap vs base_d27d3 on all changed types + pinclear).
- Gate C green -> copy R5 / R5c / kst copy into the intake, ROWS-READY post, then the <250-word die-level report to COORD (owner relay).
- Then sealed private kits on tree_b (kv3_hg_v1p2 vs FLOW-CLKGRT-R2 566k / 871k; kv3_io_cor_v1 LITE variant). No further gate on a tree
  that feeds a kit.
- ot-run notes: non-crit jobs wait on the epyc8 load cap (load 130-150); --priority plan --plan-job bind and --crit start at once.
  ot-run needs --stage for every path outside --dir. cut_ledger.py flags a row PARTIAL if it prints skipped / dropped / ignored.
