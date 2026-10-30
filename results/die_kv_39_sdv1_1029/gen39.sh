#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/die-kv-39-1029/sdv1; WT=/srv/opentallas-scratch2/claude/wt/die-kv-39-sdv1; PL=$D/planV1
cd $D
for T in kv3_sys_SD kv3_sys_SD_v1; do
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys $PL/die_plan_sd39.json --out kits --rtl-root $WT --types $T --kit-rtl $T=$D/kitrtl/$T/kit_rtl.f --hold-ff-margin 10 --clock-landing $PL/sidecar_sd39.json > logs/$T.gen.log 2>&1
  echo "$T GEN_RC $? $(tail -1 logs/$T.gen.log)"
  python3 -I kits/$T/kit_preflight.py kits/$T --plan-dir $PL --out kits/$T/kit_preflight_sd39.json > logs/$T.preflight.log 2>&1; echo "$T PREFLIGHT_RC $? $(tail -1 logs/$T.preflight.log)"
done
echo "DONE $(date)"
