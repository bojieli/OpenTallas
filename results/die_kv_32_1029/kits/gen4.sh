#!/bin/bash
R=/srv/opentallas-scratch2/claude
WT=$R/wt/codex-kv-kits-0822
D=/srv/opentallas-scratch2/claude/die-kv-32-kits-1029
O=/srv/opentallas-scratch2/claude/die-kv-31-kits-1029
B=$D/bind_fix/kit_rtl
SC=$R/wt/codex-kv-0822/results/kv_start_25_1029/event26/sidecar.json
cd $D; mkdir -p kits_gen4 logs
for tn in ${TYPES:-kv3_io_cor kv3_io_cor_v1 kv3_io_ft kv3_io_ft_v1 kv3_hub_Ei}; do
  x=; [ $tn = kv3_hub_Ei ] && x="--gpl-plain kv3_hub_Ei"
  /usr/bin/time -f "%e s %M KB" python3 $D/gen_root2/tools/die_plan/gen.py phys $O/plan_straps/die_plan.json --out $D/kits_gen4 --rtl-root $WT --types $tn --kit-rtl $tn=$B/$tn/kit_rtl.f --hold-ff-margin 10 --clock-landing $SC $x > logs/$tn.gen4.log 2>&1
  echo "$tn rc=$? $(tail -1 logs/$tn.gen4.log)"
done
