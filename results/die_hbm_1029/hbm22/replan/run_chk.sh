#!/usr/bin/env bash
# usage: run_chk.sh VARIANT  -> G0 (chk/<v>_g0) + G0C --completeness (chk/<v>_g0c)
set -u; R=/srv/opentallas-scratch2/claude/die-hbm-22/replan; T=/srv/opentallas-scratch2/claude/wt/die-hbm-22/tools/die_plan; V=$1
mkdir -p $R/chk
python3 $T/check.py $R/$V/die_plan.json --out $R/chk/${V}_g0 > $R/chk/${V}_g0.log 2>&1 &
python3 $T/check.py $R/$V/die_plan.json --out $R/chk/${V}_g0c --completeness > $R/chk/${V}_g0c.log 2>&1 &
wait
