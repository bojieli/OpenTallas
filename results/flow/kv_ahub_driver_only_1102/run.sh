#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ahub-drv-0158
D=$R/driver_only
# Existing public MM recipe: no setup or hold repair; repair_design sees actual DRV scenes.
OT_PRD_NO_HOLD=1 OT_PRD_POST=0 bash "$R/source/tools/die_plan/post_route_drv/prd_run.sh" "$D" 8 16 1 > "$D/driver_only.log" 2>&1
grep 'hold: skipped' "$D/run/logs/asap7/hc_qkd_ahub__604_8x440_64/base/5_1_grt.log"
bash "$D/clk_freeze_check.sh" "$D" > "$D/final_clock.log" 2>&1
python3 "$D/clk_geom_diff.py" "$R/seed/run/results/asap7/hc_qkd_ahub__604_8x440_64/base/clk_freeze_pre.tsv" "$D/run/results/asap7/hc_qkd_ahub__604_8x440_64/base/clk_freeze_post.tsv" --json "$D/original_G_clock_diff.json"
cp "$D/config.mk" "$D/config_driver_only.mk"
cp "$R/seed/config.mk" "$D/config.mk"
bash "$D/run_kit_kv.sh" "$D" post 16 8 > "$D/fresh_post.log" 2>&1
