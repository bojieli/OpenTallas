#!/bin/bash
# FTRES measured-need (ftres_mneed_1111, FT2_MODE=C) applied on base+channels+spu1, as path delta d2b
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; P=/srv/opentallas-scratch2/claude/die-hbm-97/ftres_mneed_1111; cd /
mkdir -p $W/inputs/mneed; cp $P/ft2_delta.py $P/SHA256SUMS $P/README.txt $W/inputs/mneed/; sha256sum $W/inputs/mneed/ft2_delta.py; grep ft2_delta.py $P/SHA256SUMS
rm -rf $W/trial/tcs; python3 -I $W/bin/compose.py apply $W/base $W/trial/tcs $W/trial/tcs.log.json $W/deltas/d1_channels.json $W/deltas/d1c_channels_ccd.json $W/deltas/d2_ftres_spu1.json > /dev/null
rm -rf $W/inputs/mneed/out; FT2_MODE=C python3 -I $W/inputs/mneed/ft2_delta.py $W/trial/tcs/die_plan.json $W/inputs/mneed/out > $W/inputs/mneed/ft2_on_tcs.log 2>&1; echo "ft2 rc $?"; tail -5 $W/inputs/mneed/ft2_on_tcs.log; ls $W/inputs/mneed/out
python3 -I $W/bin/compose.py diff $W/trial/tcs $W/inputs/mneed/out ftres_mneed $W/deltas/d2b_ftres_mneed.json --only die_plan.json
# idempotency + base equivalence: ft2 on base alone should give d33c018b
FT2_MODE=C python3 -I $W/inputs/mneed/ft2_delta.py $W/base/die_plan.json $W/inputs/mneed/out_base > /dev/null 2>&1; sha256sum $W/inputs/mneed/out_base/die_plan.json
echo MNEED_DONE
