#!/bin/bash
# One DRT TRIAL, after independent full geometry + unaffected-master review.
# Submit through normal autopilot --mode trial; no canary/source gate bypass.
set -euo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish};MEM=${3:-16};CPUS=${4:-8}
[ "$GOAL" = finish ] || { echo 'HCPL trial runner requires finish';exit 3; }
python3 "$K/hcpl_trial_guard_2144.py" "$K"
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk")
R=$K/run/results/asap7/$NICK/base
[ ! -f "$K/signoff/signoff.json" ] || { echo 'immutable trial verdict exists';exit 3; }
docker run --rm --name "hcpl-drt-trial-$$" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" -e NICKNAME="$NICK" -e TRIAL_THREADS="$CPUS" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
R=/work/run/results/asap7/$NICKNAME/base
M=(make -o synth -o place -o cts -o grt DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$TRIAL_THREADS)
for f in "$R"/1* "$R"/2* "$R"/3* "$R"/4* "$R"/5_1* "$R"/clock_period.txt;do M+=(-o "$f");done
"${M[@]}" route
"${M[@]}" do-finish
"${M[@]}" do-generate_abstract
ODB=$R/6_final.odb PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py
chown -R 1000:1000 /work
' > "$K/route_trial.log" 2>&1
# Source cohort must remain immutable through the admitted run.
python3 "$K/hcpl_trial_guard_2144.py" "$K"
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image openroad/orfs:asap7lock > "$K/signoff.log" 2>&1
