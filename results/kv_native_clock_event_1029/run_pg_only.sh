#!/bin/bash
set -euo pipefail
D=$(pwd)/pgkit02
docker run --rm --name codex-kv-native-pg-$$ --cpus=16 --memory=256g --memory-swap=256g -v "$D:/work" -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /work/psm/pg_only.tcl > /work/psm/pg_only.log 2>&1; rc=$?; chown -R $HUID:$HGID /work; exit $rc'
