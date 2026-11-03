#!/bin/bash
set -uo pipefail
K=$(pwd)
mkdir -p run
C=codex-hroot-ff-place-2338-$$
printf '%s\n' "$C" > container.txt
docker run --rm --name "$C" --memory=12g --memory-swap=12g --cpus=2 -v "$K":/work -w /OpenROAD-flow-scripts/flow -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make -f /work/own.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 hroot-place-only
rc=$?
if [ "$rc" = 0 ]; then openroad -python -exit /work/guard.py; rc=$?; fi
chown -R "$HUID:$HGID" /work/run /work/*log /work/*json /work/*tsv /work/*odb 2>/dev/null || true
exit "$rc"
' > place.log 2>&1
rc=$?
printf '%s\n' "$rc" > exit.txt
exit "$rc"
