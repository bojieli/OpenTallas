#!/bin/bash
set -eu
for v in e7 p8; do
  set +e
  docker run --rm -u "$(id -u):$(id -g)" -e VIEW="$v" -v "$PWD:/input:ro" opentallas/orfs:asap7lock-grtoff bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad -threads 2 -exit /input/ap.tcl' > "$v.log" 2>&1
  rc=$?
  set -e
  echo "$v $rc"; tail -10 "$v.log"
done
