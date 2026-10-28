#!/bin/bash
# $1 = tag, rest = extra plusargs
tag=$1; shift
I=/srv/opentallas-scratch2/claude/tok14-head-fw/img
cd /srv/opentallas-scratch2/claude/tok16-head-rm && exec ./obj16/Vtb +DIR=$I +OT_ROM_DIR=$I +NPOS=2 +GAP=10357 +GO_AT=400 +MAXC=21600 "$@" > /srv/opentallas-scratch2/claude/tok16-head-rm/run16_$tag.log 2>&1
