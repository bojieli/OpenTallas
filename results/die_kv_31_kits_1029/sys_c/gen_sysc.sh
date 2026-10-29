#!/bin/bash
set -o pipefail
R=/srv/opentallas-scratch2/claude
WT=$R/wt/codex-kv-kits-0822
D=$R/die-kv-31-kits-1029
cd $D
/usr/bin/time -v python3 $WT/tools/die_plan/gen.py phys $D/plan_snap/die_plan.json --out $D/kits_gen --rtl-root $WT --types kv3_sys_c --kit-rtl kv3_sys_c=$D/rtlsrc/kv3_sys_c/kit_rtl.f --hold-ff-margin 10 > $D/logs/kv3_sys_c.gen.log 2>&1
echo rc=$? >> $D/logs/kv3_sys_c.gen.log
