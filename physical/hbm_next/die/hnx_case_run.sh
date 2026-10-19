#!/bin/bash
# HBM-NEXT-DIE (P3-DIE 10-19): relay-free GEN of the case <tag> (stand-ins), then the die chain S4..S8 (stations, relay/landing
# layer, splice/bind, lockstep, views (+ auto-synth of missing masters), relayed GEN, GRT) on it.  Generalises hnx_t8_run.sh.
#   local driver:  TAG=f4c_t9p3 nohup bash hnx_case_run.sh > /home/ubuntu/artifacts/hnx/die_p4/chain.log 2>&1 &
TAG=${TAG:?TAG}; B=/srv/opentallas-scratch/claude/hnx/die_p4; W=/home/ubuntu/wt/hnx-die-1019; H=ot-epyc4; A=/home/ubuntu/artifacts/hnx/die_p4
echo "STEP S3 case_$TAG $(date -Is)"
scp -q $W/physical/hbm_next/die/hnx_case.sh $H:$B/ || exit 9
/home/ubuntu/bin/ot-run --mem 64 --threads 2 --hosts $H --dir $B -- bash $B/hnx_case.sh $TAG > $A/case_$TAG.otrun 2>&1
echo "CASE rc=$? $(date -Is)"; tail -14 $A/case_$TAG.otrun
grep -q GEN_OK $A/case_$TAG.otrun || { echo S3_CASE_FAIL; exit 11; }
scp -q $H:$B/case_$TAG/layout.png $A/case_${TAG}_layout.png
TAG=$TAG FROM=S4 bash $W/physical/hbm_next/die/hnx_p4_chain.sh
