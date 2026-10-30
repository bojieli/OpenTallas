#!/bin/bash
# DIE-KV-39-SD-V1: KV-022 V1 (Codex 19-tap SD prep on the PHY-bearing sd36A plan). Form = DIE-KV-36 var.sh:
# (bind + kit-rtl with the bindroot tools, as DIE-KV-36) collector retap (mk_sd36.py, variant A rule) -> strict bind -> kit-rtl + PHY specialize -> gen.py phys -> kit_preflight.
set -uo pipefail
D=/srv/opentallas-scratch2/claude/die-kv-39-1029/sdv1; WT=/srv/opentallas-scratch2/claude/wt/die-kv-39-sdv1
R=$D/bind; BR=$D/bindroot; A=$D/recipe_kv27f_sd39v1.json; PL=$D/planV1
mkdir -p $R $D/kitrtl $D/kits $D/logs $BR/kv39sd
cd $D
python3 mk_sd36.py $WT/tools/die_plan planA/sidecar_sd36.json $BR/kv39sd/sidecar_sd39.json $PL/die_plan_sd39.json $PL/die_plan_sd39.json $PL/b/bind_plan_sd39.json $PL/b/bind_plan_sd39.json > logs/mk_sd36.json 2> logs/mk_sd36.err; echo "MK_RC $?"
cp $BR/kv39sd/sidecar_sd39.json $PL/sidecar_sd39.json
python3 - <<PY
import json; a=json.load(open("$D/recipe_kv27f_sd36A.json")); a["base"]="$BR"; a["clock_landing_table"]="kv39sd/sidecar_sd39.json"
a["note"]="DIE-KV-39-SD-V1: recipe_kv27f_sd36A with base/sidecar -> sd39 V1 (19-tap) | "+a.get("note","")
json.dump(a,open("$A","w"),indent=1)
PY
for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp /srv/opentallas-scratch2/claude/die-kv-33-1029/sd/bind/$f $R/ 2>/dev/null; done
cd $BR
/usr/bin/time -v python3 tools/die_plan/bind.py bind $PL/b/bind_plan_sd39.json --out $R --asbuilt $A --strict > $R/bind.log 2> $R/bind.time; echo "BIND_RC $? $(date)"; tail -n 1 $R/bind.log
for T in kv3_sys_SD kv3_sys_SD_v1; do
  python3 tools/die_plan/bind.py kit-rtl $PL/b/bind_plan_sd39.json --out $R --asbuilt $A --type $T --kit $D/kitrtl/$T > $D/logs/kitrtl_$T.log 2>&1; echo "$T KITRTL_RC $?"
  python3 $WT/tools/die_plan/specialize_serdes_phy.py $D/kitrtl/$T $WT/results/kv_serdes_pg_event33 > $D/logs/spec_$T.json 2>&1; echo "$T SPEC_RC $?"
done
cd $D
for T in kv3_sys_SD kv3_sys_SD_v1; do
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys $PL/die_plan_sd39.json --out kits --rtl-root $WT --types $T --kit-rtl $T=$D/kitrtl/$T/kit_rtl.f --hold-ff-margin 10 --clock-landing $PL/sidecar_sd39.json > logs/$T.gen.log 2>&1
  echo "$T GEN_RC $? $(tail -1 logs/$T.gen.log)"
  python3 -I kits/$T/kit_preflight.py kits/$T --plan-dir $PL --out kits/$T/kit_preflight_sd39.json > logs/$T.preflight.log 2>&1; echo "$T PREFLIGHT_RC $? $(tail -1 logs/$T.preflight.log)"
done
echo "DONE $(date)"
