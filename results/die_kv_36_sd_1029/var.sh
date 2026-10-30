#!/bin/bash
# DIE-KV-36 KV-022 variant $1 (A = nearest reset tap per collector source, B = both sources on rst_n_t5):
# strict bind of bind_plan_sd36 with the sd36 sidecar -> kit-rtl + PHY specialize (DIE-KV-33-SD kitrtl.sh form) ->
# gen.py phys on die_plan_sd36 (DIE-KV-35 gen_b35.sh form; tools = main via sparse wt die-kv-36-sd) -> kit_preflight.
set -uo pipefail
V=$1; D=/srv/opentallas-scratch2/claude/die-kv-36-1029/sd; WT=/srv/opentallas-scratch2/claude/wt/die-kv-36-sd
R=$D/bind$V; BR=$D/bindroot$V; A=$D/recipe_kv27f_sd36$V.json; PL=$D/plan$V
mkdir -p $R $D/kitrtl$V $D/kits$V $D/logs$V
for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp /srv/opentallas-scratch2/claude/die-kv-33-1029/sd/bind/$f $R/ 2>/dev/null; done
cd $BR
/usr/bin/time -v python3 tools/die_plan/bind.py bind $PL/b/bind_plan_sd36.json --out $R --asbuilt $A --strict > $R/bind.log 2> $R/bind.time; echo "sd36$V BIND_RC $? $(date)"; tail -n 1 $R/bind.log
for T in kv3_sys_SD kv3_sys_SD_v1; do
  python3 tools/die_plan/bind.py kit-rtl $PL/b/bind_plan_sd36.json --out $R --asbuilt $A --type $T --kit $D/kitrtl$V/$T > $D/logs$V/kitrtl_$T.log 2>&1; echo "sd36$V $T KITRTL_RC $?"
  python3 $WT/tools/die_plan/specialize_serdes_phy.py $D/kitrtl$V/$T $WT/results/kv_serdes_pg_event33 > $D/logs$V/spec_$T.json 2>&1; echo "sd36$V $T SPEC_RC $?"
  grep -n -A3 "u_cland_collect" $D/kitrtl$V/$T/*_bound.sv | grep -o "u_cland_collect_[a-z0-9_]*\|rst_n([a-z0-9_]*)" | paste - - | sort -u | tr '\n' ' '; echo
done
cd $D
for T in kv3_sys_SD kv3_sys_SD_v1; do
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys $PL/die_plan_sd36.json --out kits$V --rtl-root $WT --types $T --kit-rtl $T=$D/kitrtl$V/$T/kit_rtl.f --hold-ff-margin 10 --clock-landing $PL/sidecar_sd36.json > logs$V/$T.gen.log 2>&1
  echo "sd36$V $T GEN_RC $? $(tail -1 logs$V/$T.gen.log)"
  python3 -I kits$V/$T/kit_preflight.py kits$V/$T --plan-dir $PL --out kits$V/$T/kit_preflight_sd36.json > logs$V/$T.preflight.log 2>&1; echo "sd36$V $T PREFLIGHT_RC $? $(tail -1 logs$V/$T.preflight.log)"
  head -12 kits$V/$T/landing_placement.tcl | grep collect
done
echo "sd36$V DONE $(date)"
