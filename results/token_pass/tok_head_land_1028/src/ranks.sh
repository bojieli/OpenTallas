#!/bin/bash
# TOK-HEAD-LAND-1 step 1: rank 1-3 HEAD tile images (row-map bases/TEN) + per-tile native run on the TOK-14 exe
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-head-land-1; O=/srv/opentallas-scratch2/claude/tok-head-land-1/ranks
export DSROM_1M_SNAP=/srv/opentallas-scratch2/claude/ref/DeepSeek-V4.1-Flash-dba1be0a-partial
export DSROM_1M_HEAD_REF=/srv/opentallas-scratch2/claude/ref/ctx1048576_seed20260930/ctx1048576_head.npz
EXE=/srv/opentallas-scratch2/claude/tok14-head-fw/build/obj/Vtb_head_partition_token
cd $W; echo START $(date) code $(git rev-parse --short HEAD) dirty $(git status --porcelain -uno | wc -l)
for R in 1 2 3; do
  mkdir -p $O/r$R
  python3 -I tools/s81_head/head_native_fullweight.py gen $O/r$R/img --rank $R --jobs 16 > $O/r$R/gen.log 2>&1; echo gen r$R rc=$?
  python3 -I tools/s81_head/head_native_fullweight.py run $O/r$R $EXE --jobs 16 > $O/r$R/run.log 2>&1; echo run r$R rc=$?
  tail -c 900 $O/r$R/run.log; echo
done
echo END $(date)
