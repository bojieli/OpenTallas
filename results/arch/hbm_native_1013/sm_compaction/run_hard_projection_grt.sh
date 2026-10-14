#!/bin/bash
set -euo pipefail
variant=${1:?eg or wg}
case "$variant" in eg|wg) ;; *) exit 2 ;; esac
run_dir=/srv/opentallas-scratch/codex/hbm-sm-compaction-1013/grt_$variant
cd "$run_dir"
docker run --rm --name "codex_smh_compact_${variant}_hardonly" --cpus=8 --memory=8g -v "$run_dir:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 8 -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=$?; echo "$rc" > /work/run.log.exit; chmod -R a+rwX /work; exit "$rc"'
