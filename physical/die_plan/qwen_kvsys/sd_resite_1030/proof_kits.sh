#!/bin/bash
# DIE-KV-47-SD: kit-wave equivalent per type: kit_rtl.sh (bind kit-rtl + specialize_serdes_phy) -> gen.py phys -> kit_preflight
set -u; O=/srv/opentallas-scratch2/claude/die-kv-47-sd; W=/srv/opentallas-scratch2/claude/wt/die-kv-47-sd; BIND=${BIND:-$O/bind_b1}; PLAN=$W/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json
cd $W
for T in kv3_sys_SD kv3_sys_SD_v1; do
  rm -rf $O/kits/$T $O/kitrtl/$T; mkdir -p $O/kits $O/kitrtl $O/logs
  (cd $O/bbase && TYPE=$T OUT=$O/kitrtl/$T PLAN=$PLAN KV_BIND_OUT=$BIND KV_ASBUILT=$O/recipe_b1.json bash $W/physical/die_plan/qwen_kvsys/kit_wave/kit_rtl.sh) > $O/logs/kitrtl_$T.log 2>&1; echo "$T KITRTL_RC $? $(tail -1 $O/logs/kitrtl_$T.log)"
  (cd $O/bbase2 && python3 tools/die_plan/gen.py phys $PLAN --out $O/kits --types $T --rtl-root $O/bbase --kit-rtl $T=$O/kitrtl/$T/kit_rtl.f --hold-ff-margin 10 --clock-landing $W/physical/die_plan/qwen_kvsys/plan_of_record/eW_sidecar.json) > $O/logs/gen_$T.log 2>&1; echo "$T GEN_RC $? $(tail -1 $O/logs/gen_$T.log)"
  rm -f $O/kits/preflight_$T.json; (cd $O/bbase2 && python3 tools/die_plan/kit_preflight.py $O/kits/$T --plan-dir $W/physical/die_plan/qwen_kvsys/plan_of_record --contract --out $O/kits/preflight_$T.json) > $O/logs/pf_$T.log 2>&1; echo "$T PREFLIGHT_RC $? $(tail -1 $O/logs/pf_$T.log)"
done
