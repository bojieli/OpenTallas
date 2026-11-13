#!/bin/bash
# S81-R12BA-FIN 11-12: main-tools verify (origin/main 14685c8552d3 tools only, git archive in $F/main_tools) of the ready12b-A
# final bind, on a real copy of out_r12bA_dst (out_r12bA_dst_main).  Code tree = hardlinks of bsrc_r12bA_dst except tools/.
set -u
F=/srv/opentallas-scratch2/claude/s81-r12ba-fin; D=$F/bsrc_r12bA_dst; V=$F/bsrc_verify_main_dst; OUT=$F/out_r12bA_dst_main
P=physical/die_plan/s81/plan_r12bA6.json; AB=/srv/opentallas-scratch2/claude/s81-leaf-floor-2/asbuilt_ist.json
export PYTHONDONTWRITEBYTECODE=1
test ! -e $V || { echo "REFUSE $V exists"; exit 3; }
mkdir -p $V; for d in $(ls -A $D); do case $d in tools) cp -a $F/main_tools/tools $V/ ;; *) cp -al $D/$d $V/ ;; esac; done
cd $V && echo "tools $(cat $F/main_tools/SHA) plan $(sha256sum < $P | cut -c1-12)"
nice -n 5 python3 -I -B tools/die_plan/bind.py verify $P --asbuilt $AB --out $OUT --strict > $F/verify_main_dst.log 2>&1; echo VERIFY_MAIN_RC=$?
echo RUN_VERIFY_MAIN_DONE
