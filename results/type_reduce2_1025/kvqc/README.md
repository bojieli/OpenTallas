# TYPE-REDUCE-2 / KVQC (2026-10-25) -- qwen_kvsys + qwen_compute
Base origin/main 190ebb428. Census: kvqc_census.tsv (156 rows = OWNERS.tsv qc 83 + kv 73; reason per row).
Rules: OWNER option B ID straps (tied at parent, false path, no case analysis); fixed pin table per template; FT
architecture unchanged (stations <=405 um, M7 and below; M8/M9 die clock/reset/power).

## Delta (claude/type-reduce2-kv-1025 only)
- Odd head eighths: e3 -> master e1 (strap_bsel 2'b01), e7 -> master e5 (strap_bsel 2'b11); e1 00 / e5 10.
  g3/head_master_odd_tr2.py (+ .json report): module/pins_file re-point, straps on hard cores, core_conns + stations
  lane names g_t_6/7->2/3 and 14/15->10/11; strap_bsel[1:0] pins N face M5 x=107.976/108.072 on e1 and e5 tables.
  0 pins move (e3==e1, e7==e5 tables after lane-neutral names). 0 schedule cycles.
- Kit: gen_core_kit_kv.py --head-strap-odd (cores/harden/head_strap_odd.py), unit test test_head_strap_odd.py.
- KV plan_items 73 -> 71 (head cores e0, e1 x256, e2, e5 x256, e6). G0 4E -> 4E, G0C 4E -> 4E (same hgi_WN_7 faces
  errors, identical error sets). QC: no delta (G0 3E/G0C 3E = sparse-checkout PHY .lib only).
- Equivalence: RTL substitution proof (master with strap tied == old variant, kits38x RTL) IDENTICAL for e1,e3,e5,e7;
  mutant (.hid slice) caught. Kit-level LEC (lec.py, synthesised master vs old RTL) owed when the master kit is built.

## Proposals (NOT in the delta)
- KV (3) head e5-table -> e1-table at MX: 544 pins move, max 212 um, 68 pins S->W -> one odd master (71 -> 70).
  e2 -> e6 table at R0: 891/1358 move, max 345.8 um, 269 N->S (-> 69). Heads 0-3 are on PATH-KV: PATH-KV call.
- KV ft-population: hgi_v* (8) + io_ft_v1 -> uniform FT lane bank template (max of variants, unused lanes chained,
  never tied): up to 9 -> 1-2 types. Proposal only.
- QC (3) su_lane_w: 7 tables -> 1 (83 -> 77). Displacement vs lane0: lane1 max 425.04 um (>405, 219 S->W), lane2 339,
  lane3 367, lane4/5 25 (MY), lane6 349, lane7 340. Port widths differ (c_o 247/219, sc_o 10/9/1) -> superset ports
  needed. PATH-QC C6 cores: record only.
- QC ft-population 23 items: recorded only (QC path, no FT merge).
