#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/codex-su-1551
K=$R/expx_vL_base
T=$R/flow66/tools/die_plan
O=$R/expx_nominal_guard
mkdir -p "$O"
touch "$O/.keep"
test -s "$K/run/results/asap7/hbc_ot_hbm_su_pg_lane_exp_x_core/base/6_final.odb"
test -s "$K/run/results/asap7/hbc_ot_hbm_su_pg_lane_exp_x_core/base/6_final.spef"
set +e
python3 -I "$T/signoff.py" run --kit "$K" --base "$K/run/results/asap7/hbc_ot_hbm_su_pg_lane_exp_x_core/base" --out "$O" --margin-policy nominal --flow-tag flow-20261107-ed-hbm > "$O/driver.log" 2>&1
rc=$?
set -e
[ "$rc" -le 1 ] || exit "$rc"
python3 -I "$T/eco_loop.py" check "$O/signoff.json" > "$O/eligibility.log" 2>&1
cat "$O/eligibility.log"
