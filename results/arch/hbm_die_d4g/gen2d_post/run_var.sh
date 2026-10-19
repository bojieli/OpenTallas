#!/bin/bash
# LH-GEN2CD 10-19: forest re-plan variants after forest_codex9d5a2c350 FAIL (hbm CN no root home in 40 sites). Reach budget unchanged.
#  $1 tag  $2.. extra reset_forest_layer args.  Source 7b3f6f89f (= 9d5a2c350 + --max-root-tries CLI).
set -o pipefail
T=$1; shift; HS=15e069307; XA=$(printf "%q " "$@")
A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d/forest_var; B=/srv/opentallas-scratch/claude/hd4g/gen2d; P0=$B/forest_codex9d5a2c350; P=$B/forest_$HS/$T
W=/home/ubuntu/wt/hd4g-gen2d-post
ssh ot-epyc4 "rm -rf $P && mkdir -p $P/loc && ln -s $P0/views $P/views && ln -s $P0/relay_views $P/relay_views" || exit 9
git -C $W archive $HS tools/hbm_die_v16 tools/hbm_die_v15 tools/die_port_bind.py tools/die_reach.py rtl/hbm_accel/die_glue rtl/lib | ssh ot-epyc4 "mkdir -p $P/src && tar -x -C $P/src" || exit 9
/home/ubuntu/bin/ot-run --mem 32 --threads 1 --disk 10 --priority die --dir $P/loc -- bash -c "cd $P/src/tools/hbm_die_v16 && OT_FOREST_LOG=1 /usr/bin/time -v python3 reset_forest_layer.py --relay-rows $XA --contract $P0/contract_pre.json --manifest $P0/manifest.json --views $P/views --relay-views $P/relay_views --out $P/layer.json --report $P/report.json && gzip -kf $P/layer.json" > $A/$T.otrun 2>&1
echo "RC $? $(date -Is)" >> $A/$T.otrun
mkdir -p $A/$T; scp -q ot-epyc4:$P/report.json $A/$T/ ; scp -q ot-epyc4:$P/layer.json.gz $A/$T/ 2>/dev/null
echo "VAR_DONE $T $(python3 -c "import json;r=json.load(open('$A/$T/report.json'));print(r.get('geometry_gate'),r.get('reach_gate'),str(r.get('problems'))[:300])")"
