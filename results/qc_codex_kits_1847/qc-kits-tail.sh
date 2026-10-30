#!/bin/bash
set -euo pipefail
D=${1:-/srv/opentallas-scratch2/claude/codex-qc-kits-1847};K=$D/kit
M=/srv/opentallas-scratch2/claude/die-qc-37-vmr/main_sofix/tools/die_plan
B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base
# Route caller must have exited successfully before tail runs.
bash /srv/opentallas-scratch2/claude/codex-qc-kits-1847/finish.sh "$K"
docker run --rm --memory=8g --cpus=2 -v "$K":/work -v "$D":/eco openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ODB=$B/5_2_route.odb openroad -python -exit /work/m6_census.py" > "$D/m6.log" 2>&1
grep -q "'other'" "$D/m6.log" && { echo 'LAYER_SEP FAIL';exit 8; }
set +e
SIGNOFF_DOCKER=docker python3 -I "$M/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$D/signoff" --image openroad/orfs:asap7lock > "$D/signoff.log" 2>&1
SO=$?
docker run --rm --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -v "$M":/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /eco/lec" > "$D/lec.log" 2>&1
LR=$?
docker run --rm -v "$D":/eco openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /eco
echo "TAIL_DONE signoff=$SO lec=$LR"
exit "$SO"
