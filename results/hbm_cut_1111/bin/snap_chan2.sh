#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; C=/srv/opentallas-scratch2/claude/die-hbm-97-channels/plan_p11t_chan; D=$W/deltas
cd /; rm -rf $W/inputs/chan2.tmp; cp -a $C $W/inputs/chan2.tmp
(cd $W/inputs/chan2.tmp && sha256sum -c --quiet SHA256SUMS && echo CHAN2_SUMS_OK && sha256sum die_plan.json SHA256SUMS compiler_core_delta.json core_conns.json)
mv $W/inputs/chan2.tmp $W/inputs/chan2
mv $D/d1_channels.json $D/withdrawn/d1_channels_rev1_fd512301.json; mv $D/d1c_channels_ccd.json $D/withdrawn/d1c_channels_ccd_rev1.json
python3 -I $W/bin/compose.py diff $W/base $W/inputs/chan2 channels_rev2 $D/d1_channels.json --skip compiler_core_delta.json | grep -v " raw set$"
python3 -I $W/bin/compose.py diff $W/base $W/inputs/chan2 channels_rev2_ccd $D/d1c_channels_ccd.json --only compiler_core_delta.json
python3 -I -c "
import json; d=json.load(open('$D/d1c_channels_ccd.json'))
for p,o,v in d['files']['compiler_core_delta.json']['ops']: print(p,o,str(v)[:200])"
echo CHAN2_DONE
