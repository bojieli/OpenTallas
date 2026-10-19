#!/bin/bash
# HBM-NEXT-DIE step 5 (10-19): relay-free GEN of the f4c_t8 case (IDX quarters in their idxs_<q> slots), then the DIE-P4
# chain S4..S8 (stations, relay/landing layer, splice/bind, lockstep, views, relayed GEN, GRT) on it.
#   local driver:  nohup bash hnx_t8_run.sh > /home/ubuntu/artifacts/hnx/die_p4/chain.log 2>&1 &
B=/srv/opentallas-scratch/claude/hnx/die_p4; W=/home/ubuntu/wt/hnx-die-1019; H=ot-epyc4
echo "STEP S3 case_f4c_t8 $(date -Is)"
/home/ubuntu/bin/ot-run --mem 64 --threads 2 --hosts $H --dir $B -- bash $B/hnx_case.sh f4c_t8 > /home/ubuntu/artifacts/hnx/die_p4/case_t8.otrun 2>&1
echo "CASE rc=$? $(date -Is)"; tail -14 /home/ubuntu/artifacts/hnx/die_p4/case_t8.otrun
grep -q GEN_OK /home/ubuntu/artifacts/hnx/die_p4/case_t8.otrun || { echo S3_CASE_FAIL; exit 11; }
scp -q $H:$B/case_f4c_t8/layout.png /home/ubuntu/artifacts/hnx/die_p4/case_f4c_t8_layout.png
TAG=f4c_t8 FROM=S4 bash $W/physical/hbm_next/die/hnx_p4_chain.sh
