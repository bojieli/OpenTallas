#!/bin/bash
# S81-PROUTE-2: gen_lint + kit_preflight as the kit wave runs them
set -uo pipefail
W=/srv/opentallas-scratch2/claude/s81-proute-2
SRC=/srv/opentallas-scratch2/claude/wt/kit-wave-15-s81b
K=$W/gen/slice_station__p7S_x11
PD=$W/plandir
rm -rf $PD && mkdir -p $PD && for f in $SRC/physical/die_plan/s81/*; do ln -s "$f" $PD/; done; ln -sfn $W/plan_proute_x11p.json $PD/die_plan.json
cd $SRC
python3 tools/die_plan/kit_gen_lint.py $K --plan-dir $PD --mem 8; echo GEN_LINT_RC=$?
python3 tools/die_plan/kit_preflight.py $K --plan-dir $PD --contract --out $W/preflight.$(date +%s).json; echo PREFLIGHT_RC=$?
