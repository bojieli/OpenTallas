# qwen_kvsys die plan (PLAN-KV, TOPDOWN-PLAN)

Inputs: `asbuilt_rtl6_e33504a6f.json.gz` = `extract_asbuilt.py` on the rtl6 GEN case (ep5 `codex-kvgen-2140/run_main_rtl6/case_kv`, source e33504a6f).
Rebuild (tools/die_plan from claude/plan-tool-1023):

    python3 build_plan.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out /tmp/stage1.json.gz
    python3 emit_plan.py --stage1 /tmp/stage1.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report.json
    python3 tools/die_plan/gen.py latency die_plan.json --inplace
    python3 tools/die_plan/check.py die_plan.json --png
    python3 kv_params.py /tmp/stage1.json.gz > kv_params.json

## v2 (PLAN-KVv2, 10-23) -- die_plan.json is now v2 (v1 at 1bf4cda41)

Regular die-row lattice on PLAN-TOOL's 8.64-um grid: 16 rows x 1520.64 um (4 HBM PCs per row), 7 columns
PHY | PC | HG | PV | HG | PC | PHY; W/E quads are MY copies, the N half is MX about a 1.2-mm centre band (hroot x4 +
centre control hub: kvs_ctl, kvs_attn, host, ahub, pvfin, emb, seq, pvw ctl/RH, astk ctl/zn); sys row on top (sys_W
UCIe/d2d, sys_core pll, sys_E serdes). 120 partitions / 24 types, no channels or strips (the v1 hgrp|PV lane strips are
ft slots of hg/pv). PHY sliced per row (1520-um slices). astk ep/owner folded into the hg rows (owner chain follows the
physical slg order). S-quad hsl chains re-headed at hsl_31 (qkd_hslice_dn, the N-quad form) so pc rows share one type.

    python3 plan_v2.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out stage1_v2.json.gz
    python3 emit_v2.py --stage1 stage1_v2.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report_v2.json
    T=<plan-tool>/tools/die_plan; python3 $T/gen.py latency die_plan.json --inplace --out gen; python3 $T/check.py die_plan.json --png
    python3 kv_params_v2.py stage1_v2.json.gz > kv_params_v2.json

Open: pv rows stay positional (9 types; vport vo all-gather keeps natural widths, a constant-width trunk costs ~3
cycles/row of RL); sys<->hub traffic shares the hg_WN pass corridor; bus leaf bindings not yet declared (G0 WARN).
