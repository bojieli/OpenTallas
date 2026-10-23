# qwen_kvsys die plan (PLAN-KV, TOPDOWN-PLAN)

Inputs: `asbuilt_rtl6_e33504a6f.json.gz` = `extract_asbuilt.py` on the rtl6 GEN case (ep5 `codex-kvgen-2140/run_main_rtl6/case_kv`, source e33504a6f).
Rebuild (tools/die_plan from claude/plan-tool-1023):

    python3 build_plan.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out /tmp/stage1.json.gz
    python3 emit_plan.py --stage1 /tmp/stage1.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report.json
    python3 tools/die_plan/gen.py latency die_plan.json --inplace
    python3 tools/die_plan/check.py die_plan.json --png
    python3 kv_params.py /tmp/stage1.json.gz > kv_params.json
