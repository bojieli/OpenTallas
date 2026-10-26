# PLAN-DELTA/KV 10-25: KV die plan v3.9 -> v3.9pd (TYPE-REDUCE KV, non-path types only)

Base: main 3947653943 (plan v3.9, G0/G0C PASS 0 err). Reproduce: `results/plan_delta_1025/kv/run_delta_kv.sh OUTDIR`
(`delta_kv.py` in place, idempotent; then gen.py latency, R8 chain with `r8_row_publish.py --family kv3_hg_v1_r2`,
`row_latency.py`, reset offsets, G0/G0C). `run_delta_kv.sh OUTDIR base` reproduces v3.9's R8 landing exactly (0 diffs).
`r8_row_publish.py` / `row_latency.py` are vendored from claude/kv-plan3f-1025 (KV-PLAN3F v3.9f, still pending; its
v3.9e-based plan has 326 [faces] G0 errors, so this delta is built on the G0-clean main v3.9 instead).

## PATH exclusion
Path partitions pc_EN_0, phy_EN_0, hg_EN_0, hgi_EN_0, hub_Eo, sys_c -> types kv3_pc, kv3_phy, kv3_hg, kv3_hgi_v3,
kv3_hub_Eo, kv3_sys_c (cores head_eighth e0-e7, qkd_ectlk, qkd_kvs_pc, qkd_kvs_pc_h_head_p, kv3_astk_EN/ES).
delta_kv.py asserts all six are byte-identical; no R8 landing member of a path partition changes.

## Types 49 -> 43
| survivor (definition unchanged?) | merged in | instances re-pointed |
|---|---|---|
| kv3_hg_v1_r2 (yes, byte-identical) | kv3_hg_v1_r1, r3, r4, r5, kv3_hg_v2 (bus i_efault_hg_Q_N_fault -> i_fch_hg_Q_N_q) | hg_*_1..6 (rows 1-6) |
| kv3_pv (renamed: {i,o}_fch_pv_S_N_q -> _V_N_q) | kv3_pv_v8 (renamed _N_ -> _V_) | pv_S_0, pv_N_0 |
hg 8 -> 3 (kv3_hg row 0 PATH, kv3_hg_v1_r2 rows 1-6, kv3_hg_v3 row 7); pv 13 -> 12.

## Per-row latency published (replaces R8 row pads)
`physical/die_plan/qwen_kvsys/lat_v39pd/row_latency.json` (+ lat pkg / latency json): 20 members, rows 1/3/4/5 x 4
quadrants: astk ep xi 267 b pad 3 -> 0 (landed 5 -> 2) rows 1/3/5; ectl cfg 5 b pad 2 -> 0 (12 -> 10 row 4, 10 -> 8
row 5). Die R8 pad flops 23,365 -> 13,673 (-9,692). Non-family changes 0. Row 7 (kv3_hg_v3) keeps its type-level R8.

## Gates (check.py, landing = r8/qwen_kvsys_r8_landing.json)
| | before (v3.9) | after (v3.9pd) |
|---|---|---|
| G0 | PASS 0 err / 1815 warn, 49 types | PASS 0 err / 1596 warn, 43 types |
| G0C | PASS 0 err / 1815 warn | PASS 0 err / 1596 warn |
Renders: png/die_v39.png, png/die_v39pd.png, png/type_kv3_hg_v1_r2_v39pd.png, png/type_kv3_pv_v39pd.png.

## Refused / deferred
- pc_v2 -> pc_v1: refused, not a rename on v3.9 (row-6 pin table differs from pc_v1 in 4,052 entries); needs a type-frame re-window (KV-PLAN3 v3.9e chan_windows).
- pv v9/v10/v11/v12 -> v1/v3/v5/v7: refused, ft_slots regs_um differ (and pv_v7/v12 pin table, 1,302 entries); needs a pv re-window.
- hgi 9 -> 6 E/W re-pack: optional, not cheap (re-pin), skipped.
- head_eighth e0-e7 8 -> 3 and astk EN/ES/WN/WS 4 -> 1 straps: PATH cores (hg_EN_0 heads, astk EN in hub_Eo), deferred.
- bind / port-bind not run (no core or pin change; renamed buses are on non-path types).
