#!/bin/bash
# HBM-R16/C17: station relax (--noadd) + G0 + G0C on the C17 plan (C16r 732240f89458 + hub core re-pin/orient)
set -euo pipefail
R=/srv/opentallas-scratch2/claude/hbm-r16-1027; Q=/srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
cd $R
sha256sum c17/die_plan.json > c17/pre_relax.sha256
python3 $Q/relax_route.py c17 400 405 --noadd > c17/relax_route17.log 2>&1
python3 $Q/relax_hop.py c17 400 405 > c17/relax_hop17.log 2>&1
sha256sum c17/die_plan.json | tee c17/die_plan.sha256
cd $R/c17
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
python3 $C die_plan.json --out gates/br_g0 > gates_br_g0.log 2>&1; echo $? > gates_br_g0.exit &
python3 $C die_plan.json --completeness --out gates/br_g0c > gates_br_g0c.log 2>&1; echo $? > gates_br_g0c.exit &
wait
