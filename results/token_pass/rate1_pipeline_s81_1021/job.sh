#!/bin/bash
# job.sh NAME MODE HOP RES EXPECT [PLAN_ARGS...]  (run from the tokb-rate1-1021 root on a fleet host)
set -u
R=$(pwd); NAME=$1 MODE=$2 HOP=$3 RES=$4 EXPECT=$5; shift 5
rm -rf "$R/out_$NAME"; mkdir -p "$R/out_$NAME"
cd "$R/stage" && XSTAGE=$R/xstage SOURCES=$R/sources.f CAL_DIR=cal LINKS=links_g4.json MODE=$MODE HOP=$HOP RES=$RES \
  EXPECT=$EXPECT PLAN_ARGS="$*" OUT=$R/out_$NAME JOBS=8 bash tools/s81_dv/tokfunc/run_wn_hop_replay.sh > "$R/out_$NAME/job.log" 2>&1
rc=$?; echo "JOB $NAME rc $rc host $(hostname)"; tail -3 "$R/out_$NAME/job.log"; exit $rc
