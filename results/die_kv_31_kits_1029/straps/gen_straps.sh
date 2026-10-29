#!/bin/bash
R=/srv/opentallas-scratch2/claude
WT=$R/wt/codex-kv-kits-0822
D=$R/die-kv-31-kits-1029
B=$R/codex-kv-0822/bind_fast/kit_rtl
cd $D; mkdir -p kits_gen2 logs
for tn in kv3_hroot kv3_io_cor kv3_io_cor_v1 kv3_io_ft kv3_io_ft_v1 kv3_hub_Ei kv3_sys_c; do
  f=$B/$tn/kit_rtl.f; [ $tn = kv3_sys_c ] && f=$D/rtlsrc/kv3_sys_c/kit_rtl.f
  x=; [ $tn = kv3_hub_Ei ] && x="--gpl-plain kv3_hub_Ei"
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys $D/plan_straps/die_plan.json --out $D/kits_gen2 --rtl-root $WT --types $tn --kit-rtl $tn=$f --hold-ff-margin 10 $x > logs/$tn.gen2.log 2>&1
  echo "$tn rc=$? $(tail -1 logs/$tn.gen2.log)"
done
