#!/bin/bash
# FABLE-FIX-KV-HUB-R3: views of the 5 re-frozen hub_Eo/hub_Wo ring masters (KV-PLAN-R2 1d hub_C recipe: ck_contract census tt+ff ->
# export_view (closed view) -> clock_contract.json).  usage: export_all.sh  (through ot-run, epyc8)
set -uo pipefail
W=/srv/opentallas-scratch2/claude/fable-fix-kv-hub; R=$W/r3/rk; V=$W/r3/views; C=$W/r3/ck; L=$W/launch_h
CK=/srv/opentallas-scratch2/claude/kv-plan-r2/d27b/hubc_tools/ck_contract.py
mkdir -p $V $C; bad=0
for m in $(ls $R); do
  K=$R/$m/kits/${m}_synth0; O=$C/$m; mkdir -p $O
  v=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('verdict'))" $K/signoff/signoff.json 2>/dev/null)
  [ "$v" = SIGNED ] || { echo "$m NOT_SIGNED ($v)"; bad=1; continue; }
  [ -e $V/$m ] && { echo "$m view exists, skip"; continue; }
  ( python3 -I $CK run $K $O tt > $O/run_tt.log 2>&1 ) & ( python3 -I $CK run $K $O ff > $O/run_ff.log 2>&1 ) & wait
  ( cd $L && python3 -I tools/autopilot/export_view.py --kit $K --signoff $K/signoff/signoff.json --out $V --die qwen_kvsys \
      --note "FABLE-FIX-KV-HUB-R3 11-21: CLAND-MACRO-1 re-freeze from D27d source (tree_h) for the kv3_hub_Eo/kv3_hub_Wo hard ring rows" ) > $O/export.json 2> $O/export.err
  echo "$m export rc $? $(cut -c1-200 $O/export.json)"
  python3 -I $CK write $K $O $V/$m/${m}_tt.lib > $O/write.log 2>&1; rc=$?; echo "$m contract rc $rc $(tail -1 $O/write.log | cut -c1-200)"
  [ $rc = 0 ] || { bad=1; continue; }
  chmod u+w $V/$m && cp -p $O/clock_contract.json $V/$m/clock_contract.json && chmod a-w $V/$m/clock_contract.json $V/$m
done
( cd $V && sha256sum */* 2>/dev/null > SHA256SUMS.tmp && mv SHA256SUMS.tmp SHA256SUMS )
echo EXPORT_ALL_DONE bad=$bad; exit $bad
