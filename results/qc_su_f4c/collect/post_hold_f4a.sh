#!/bin/bash
# QC-SU-F4C resume: hold_route_f4a.sh exited 7 after HOLD_F4A_GATE PASS: drt_f4a.sh not executable (Permission denied). Runs the unchanged tail: DRT -> finish -> main signoff -> main LEC.
set -uo pipefail
K=$(cd "$1" && pwd); H=$(dirname "$0"); H=$(cd "$H" && pwd)
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
grep -q "HOLD_F4A_GATE PASS" $K/hold_f4a_gate.txt || exit 6
rm -f $K/run/logs/asap7/*/base/5_2_route.json
bash $H/drt_f4a.sh $K || exit 7
bash $H/finish_f4a.sh $K || exit 8
# sign-off with the main tools (63f0898a3: pg + ft_interface checks) and LEC of the routed netlist 6_final.v (main lec.py)
M=/srv/opentallas-scratch2/claude/qc-plan-f4a-1026/main_63f0898a3/tools/die_plan
SIGNOFF_DOCKER=docker python3 -I $M/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --ff-vclk auto --out $K/signoff_main --image openroad/orfs:asap7lock > $K/signoff_main.log 2>&1; so=$?
docker run --rm --memory=24g --memory-swap=24g --cpus=8 -v $K:/work -v $M:/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /work/lec_final" > $K/lec_final.log 2>&1; lr=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "CHAIN_DONE signoff rc $so lec rc $lr $(date -Is)" | tee $K/chain_done.txt; grep -E '^SIGNOFF|^  - ' $K/signoff_main.log | head -12; tail -n 2 $K/lec_final.log
exit $so
