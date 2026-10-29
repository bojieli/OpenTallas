#!/bin/bash
# DIE-KV-36: kit-rtl of the hg types not re-tied (ECTL RESPONSE_LAT 17->18 reaches every hg frame) - control vs bindB2
cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
S=/srv/opentallas-scratch2/claude/die-kv-36-1029
for T in kv3_hg kv3_hg_v1p2 kv3_hg_v1p4 kv3_hg_v1p5 kv3_hg_v3; do
 python3 tools/die_plan/bind.py kit-rtl results/die_kv_29_1029/event27f/plan.json --out $S/bindCtl --asbuilt physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv27f.json --type $T --kit $S/bindCtl/kit_rtl/$T > $S/bindCtl/kit_rtl_$T.log 2>&1; echo "ctl $T $?"
 python3 tools/die_plan/bind.py kit-rtl kv36/event28b/plan.json --out $S/bindB2 --asbuilt $S/recipe_kv27f_eB2.json --type $T --kit $S/bindB2/kit_rtl/$T > $S/bindB2/kit_rtl_$T.log 2>&1; echo "B2 $T $?"
done
cd $S; for f in $(cd bindB2/kit_rtl && find . -name "*.sv" | sort); do n=$(diff <(sed "s#//.*##;s#bindCtl#BIND#g" bindCtl/kit_rtl/$f) <(sed "s#//.*##;s#bindB2#BIND#g" bindB2/kit_rtl/$f) | grep -c "^[<>]"); echo "FUNCDIFF $f $n"; done
grep -h "RESPONSE_LAT" bindB2/kit_rtl/*/*_bound.sv | grep -o "RESPONSE_LAT([0-9]*)" | sort | uniq -c
echo HGREST_DONE
