#!/bin/bash
# DIE-KV-36 KV-022 variant $1: gen.py phys + kit_preflight (second half of var.sh)
set -uo pipefail
V=$1; D=/srv/opentallas-scratch2/claude/die-kv-36-1029/sd; WT=/srv/opentallas-scratch2/claude/wt/die-kv-36-sd; PL=$D/plan$V; cd $D
for T in kv3_sys_SD kv3_sys_SD_v1; do
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys $PL/die_plan_sd36.json --out kits$V --rtl-root $WT --types $T --kit-rtl $T=$D/kitrtl$V/$T/kit_rtl.f --hold-ff-margin 10 --clock-landing $PL/sidecar_sd36.json > logs$V/$T.gen.log 2>&1
  echo "sd36$V $T GEN_RC $? $(tail -1 logs$V/$T.gen.log)"
  python3 -I kits$V/$T/kit_preflight.py kits$V/$T --plan-dir $PL --out kits$V/$T/kit_preflight_sd36.json > logs$V/$T.preflight.log 2>&1; echo "sd36$V $T PREFLIGHT_RC $? $(tail -1 logs$V/$T.preflight.log)"
  head -12 kits$V/$T/landing_placement.tcl | grep collect
done
