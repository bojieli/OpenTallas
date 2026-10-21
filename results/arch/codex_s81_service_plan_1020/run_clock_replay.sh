#!/bin/bash
set -euo pipefail
D=$(pwd)
python3 clock_replay.py /srv/opentallas-scratch/claude/s81-die11/mu7v2c/case "$D/mu7v2c_ck2"
C="$D/mu7v2c_ck2"
docker run --rm --name s81-clock-replay-$$ --cpus=8 --memory=64g -v "$C":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for corner in tt ff; do /usr/bin/time -v openroad -threads 8 -no_init -exit /work/sta_${corner}.tcl > /work/sta/sta_${corner}.log 2>&1 || exit $?; done; chmod -R a+rwX /work/sta'
python3 "$C/classify.py" "$C" tt ff > "$C/sta/classes.txt"
echo CLOCK_REPLAY_RC=0
