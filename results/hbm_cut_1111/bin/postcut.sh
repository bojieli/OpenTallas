#!/bin/bash
# FTRES postcut (ft3_delta.py) on base+channels+spu1+mneed -> path delta d2c
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; P=/srv/opentallas-scratch2/claude/die-hbm-97/ftres_postcut_1111; D=$W/deltas; cd /
mkdir -p $W/inputs/postcut; cp $P/ft3_delta.py $P/SHA256SUMS $P/README.txt $P/ft3_event.json $W/inputs/postcut/
rm -rf $W/trial/tcsm; python3 -I $W/bin/compose.py apply $W/base $W/trial/tcsm $W/trial/tcsm.log.json $D/d1_channels.json $D/d1c_channels_ccd.json $D/d2_ftres_spu1.json $D/d2b_ftres_mneed.json > /dev/null || echo APPLY_FAIL
rm -rf $W/inputs/postcut/out; python3 -I $W/inputs/postcut/ft3_delta.py $W/trial/tcsm/die_plan.json $W/inputs/postcut/out > $W/inputs/postcut/ft3_on_tcsm.log 2>&1; echo "ft3 rc $?"; tail -3 $W/inputs/postcut/ft3_on_tcsm.log
python3 -I $W/bin/compose.py diff $W/trial/tcsm $W/inputs/postcut/out ftres_postcut $D/d2c_ftres_postcut.json --only die_plan.json
echo POSTCUT_DONE
