#!/bin/bash
# L2H-GEN2D-FP 10-19: copy of forest_var/run_var_bound.sh with P0 (staged contract_pre.json manifest.json views/ on $RH), A and W as env.
# kits branch 5ddedcf7c (RTL 5ab727c0f) + bounded_route + --carrier-home-um).  Off ot-epyc4 (drained): inputs staged to $RH.
#  env RH=<host with staged forest_codex9d5a2c350>  LEFS=relay_views|relay_views_hard ;  $1 tag  $2.. reset_forest_layer args.
set -o pipefail
T=$1; shift; HS=${HS:-c107772e4}; RH=${RH:?RH}; LEFS=${LEFS:?LEFS}; XA=$(printf "%q " "$@")
A=${A:?A}; B=/srv/opentallas-scratch/claude/hd4g/gen2d; P0=${P0:?P0}; P=$B/fp_$HS/$T
W=${W:-/home/ubuntu/wt/hd4g-gen2d-fp-1019}; JC=/home/ubuntu/artifacts/hbm-reset-joint-corridor-1019
ssh -o ControlPath=none $RH "rm -rf $P && mkdir -p $P/loc $P/carrier && ln -s $P0/views $P/views" || exit 9
git -C $W archive $HS tools/hbm_die_v16 tools/hbm_die_v15 tools/die_port_bind.py tools/die_reach.py rtl/hbm_accel/die_glue rtl/lib results/arch/hbm_die_d4g/rstcarrier | ssh -o ControlPath=none $RH "mkdir -p $P/src && tar -x -C $P/src && cp -r $P/src/results/arch/hbm_die_d4g/rstcarrier/$LEFS $P/relay_views" || exit 9
scp -q -o ControlPath=none $JC/compressed_topology.json $JC/sinks.json $RH:$P/carrier/ || exit 9
XA=${XA//@CAR@/$P/carrier}
echo "VAR_START $T host=$RH src=$HS lefs=$LEFS args=$XA $(date -Is)" > $A/$T.otrun
/home/ubuntu/bin/ot-run --mem 32 --threads 1 --disk 10 --priority die --dir $P/loc -- bash -c "cd $P/src/tools/hbm_die_v16 && OT_FOREST_LOG=1 /usr/bin/time -v python3 reset_forest_layer.py --relay-rows --compact $XA --contract $P0/contract_pre.json --manifest $P0/manifest.json --views $P/views --relay-views $P/relay_views --out $P/layer.json --report $P/report.json && gzip -kf $P/layer.json" >> $A/$T.otrun 2>&1
echo "RC $? $(date -Is)" >> $A/$T.otrun
mkdir -p $A/$T; scp -q -o ControlPath=none $RH:$P/report.json $A/$T/ ; scp -q -o ControlPath=none $RH:$P/layer.json.gz $A/$T/ 2>/dev/null
echo "VAR_DONE $T $(python3 -c "import json;r=json.load(open('$A/$T/report.json'));print(r.get('geometry_gate'),r.get('reach_gate'),str(r.get('problems'))[:300])")" | tee -a $A/$T.otrun
