#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/codex-s81-dieplace
cand=$base/placement_diag/coll_safe2_parent_v3
cd "$cand/src"
python3 tools/s81_dv/coll_safe2_parent_table.py --table "$base/src/results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json" --root "$cand/src" --out "$cand/candidate_table_v3.json"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
export OT_VERILATOR=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
timeout 1200 python3 tools/s81_dv/dv_diecase.py --plan "$base/plan/plan.json" --out "$cand/bound3" --bind real --bind-table "$cand/candidate_table_v3.json" --land-plan results/arch/s81_dv_1016/landing/p4l3/land_plan.json > "$cand/bind3.log" 2>&1
echo STRICT_V3_CLI_COMPLETED
