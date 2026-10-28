#!/usr/bin/env bash
# usage: run.sh MODE NETS  (on intel2 via ot-run)
set -u
MODE=$1; NETS=$2
P=/srv/opentallas-scratch2/claude/pg-act-3-1027/qc_stack
K=/srv/opentallas-scratch2/claude/codex-rc-canary-1027/qc_ctltrial/runs/qwen_compute_7fd3cec6d_1027_093146_950078/gen/coll_ftm
docker run --rm --name pga3-$MODE-$NETS-$$ -m ${MEM:-80}g --cpus 8 -e PGA3_MODE=$MODE -e PGA3_NETS=$NETS -e PGA3_OX=0 -e PGA3_OY=0 -u $(id -u):$(id -g) -v $K:/old:ro -v $P:/p openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /p/${TCL:-stack.tcl}" > $P/${MODE}_${NETS}.log 2>&1
rc=$?; echo "EXIT $rc $(date -Is)" >> $P/${MODE}_${NETS}.log; exit $rc
