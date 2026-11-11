#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; C=/srv/opentallas-scratch2/claude/die-hbm-97-channels/plan_p11t_chan
cd /; rm -rf $W/inputs/chan.tmp; mkdir -p $W/inputs
cp -a $C $W/inputs/chan.tmp
(cd $W/inputs/chan.tmp && sha256sum -c --quiet SHA256SUMS && echo CHAN_SUMS_OK && sha256sum die_plan.json SHA256SUMS compiler_core_delta.json core_conns.json)
mv $W/inputs/chan.tmp $W/inputs/chan
python3 -I $W/bin/compose.py diff $W/base $W/inputs/chan channels $W/deltas/d1_channels.json --skip compiler_core_delta.json
python3 -I $W/bin/compose.py diff $W/base $W/inputs/chan channels_ccd $W/deltas/d1c_channels_ccd.json --only compiler_core_delta.json --file-base compiler_core_delta.json=$W/base/../inputs/spu1_ccd_3f7a.json
