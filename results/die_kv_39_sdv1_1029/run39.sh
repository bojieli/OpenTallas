#!/bin/bash
# DIE-KV-39-SD-V1: kit place -> declared FDI CDC (DIE-KV-38 kv38_cdc_fdi.sdc, same form as the C/A baseline) appended to
# 3_place.sdc -> CTS + FF structural hold gate (+ route if it passes).  usage: run39.sh KIT
set -uo pipefail
K=$1; D=/srv/opentallas-scratch2/claude/die-kv-39-1029/sdv1; R=$D/kits/run_kit.sh
[ -x $R ] || R=$(dirname $K)/run_kit.sh
echo "PLACE start $(date)"; bash $R $K place 32 8; rc=$?; echo "PLACE_RC $rc $(date)"; [ $rc = 0 ] || exit $rc
S=$(ls $K/run/results/asap7/*/base/3_place.sdc | head -1); cp -p $S $S.pre39; cat $D/kv38_cdc_fdi.sdc >> $S; echo "CDC appended to $S"
bash $R $K route 32 8; rc=$?; echo "ROUTE_RC $rc $(date)"; grep -h "OT_HOLD\|worst\|WNS\|slack" $K/hold_gate.log | tail -5; exit $rc
