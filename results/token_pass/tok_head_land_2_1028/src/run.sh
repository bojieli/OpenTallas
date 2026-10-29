#!/bin/bash
# $1 = obj tag (e.g. TT), $2 = run tag, rest = plusargs
R=/srv/opentallas-scratch2/claude/tok-head-land-2; o=$1; tag=$2; shift 2
I=${IMG:-/srv/opentallas-scratch2/claude/tok14-head-fw/img}
cd $R && exec ./obj_$o/Vtb "$@" +DIR=$I +OT_ROM_DIR=$I +NPOS=2 +GAP=10357 +GO_AT=400 +MAXC=24000 > $R/run_$tag.log 2>&1
