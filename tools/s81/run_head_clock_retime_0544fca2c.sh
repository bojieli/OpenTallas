#!/bin/bash
set -u
root=${1:-/srv/opentallas-scratch/claude/s81-dies/clockfamily_gather/retime}
src=$(cat "$root/kit/src_root")
for corner in tt ff; do
  if [ -e "$root/sta/sta_${corner}_v2.log" ]; then
    echo "Refusing to overwrite retrospective STA evidence: $root" >&2
    exit 2
  fi
done
for corner in tt ff; do
  /srv/opentallas-scratch/admit.sh 16 -- docker run --rm \
    -v "$root/sta:/run" -v "$root/kit:/kit:ro" -v "$src:$src:ro" \
    openroad/orfs:asap7lock bash -lc \
    "source /OpenROAD-flow-scripts/env.sh; /usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_init -exit /run/sta_${corner}.tcl" \
    > "$root/sta/sta_${corner}_v2.log" 2>&1
  rc=$?
  echo "$rc" > "$root/sta/sta_${corner}_v2.exit"
done
