#!/bin/bash
set -u
cd /srv/opentallas-scratch2/scratch/codex/hbm-clock-context-39d44c082
printf '%s\n' "$$" > run.pid
date -u +%FT%TZ > run.start
for corner in ss ff; do
  docker run --rm -v /srv/opentallas-scratch2/scratch/claude/hbm-abstracts/die/r23c/s_sta:/work:ro -v "$PWD:/context" -w /context openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 1 -no_init -exit /context/run_clock_${corner}.tcl" > "${corner}.log" 2>&1
  printf '%s\n' "$?" > "${corner}.rc"
done
date -u +%FT%TZ > run.done
