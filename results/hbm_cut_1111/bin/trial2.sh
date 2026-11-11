#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; C="python3 -I $W/bin/compose.py"; T=$W/trial; cd /
D=$W/deltas
echo "== conflicts"; $C conflicts $D/d1_channels.json $D/d1c_channels_ccd.json $D/d2_ftres_spu1.json $D/d4_adopt_vis_NW_io.json > $T/t2.conflicts.json; echo "conflict rc $?"; head -c 1500 $T/t2.conflicts.json; echo
rm -rf $T/t1c; $C apply $W/base $T/t1c $T/t1c.log.json $D/d1_channels.json $D/d1c_channels_ccd.json > /dev/null
echo "== channels-only reproduce"; sha256sum $T/t1c/die_plan.json $T/t1c/core_conns.json $T/t1c/clock_entries.json $T/t1c/compiler_core_delta.json
rm -rf $T/t2; $C apply $W/base $T/t2 $T/t2.log.json $D/d1_channels.json $D/d1c_channels_ccd.json $D/d2_ftres_spu1.json $D/d4_adopt_vis_NW_io.json
sha256sum $T/t2/die_plan.json
$C classify $W/base $T/t2 $T/t2.cls.json
$W/bin/g0.sh $T/t2 $T/t2.g0; tail -2 $T/t2.g0/g0.log
python3 -I $W/bin/g0cmp.py $W/g0_base/g0_report.json/g0_report.json $T/t2.g0/g0_report.json/g0_report.json | head -30
echo TRIAL2_DONE
