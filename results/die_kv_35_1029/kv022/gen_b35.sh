#!/bin/bash
# DIE-KV-35 KV-022: same recipe as die-kv-33-1029/sd/gen_b.sh, plan = die_plan_sd35.json (clk_clk_phy type pad), out = kits
S=/srv/opentallas-scratch2/claude/die-kv-33-1029/sd; N=/srv/opentallas-scratch2/claude/die-kv-35-1029/sd; WT=/srv/opentallas-scratch2/claude/wt/die-kv-33-sd; SC=/srv/opentallas-scratch2/claude/wt/codex-kv-0822/results/kv_start_25_1029/event26/sidecar.json; cd $N
for tn in kv3_sys_SD kv3_sys_SD_v1; do
  /usr/bin/time -f "%e s %M KB" python3 $WT/tools/die_plan/gen.py phys plan/die_plan_sd35.json --out kits --rtl-root $WT --types $tn --kit-rtl $tn=$S/kit_rtl/$tn/kit_rtl.f --hold-ff-margin 10 --clock-landing $SC > logs/$tn.gen.log 2>&1
  echo "$tn gen rc=$? $(tail -1 logs/$tn.gen.log)"
  python3 -I kits/$tn/kit_preflight.py kits/$tn --plan-dir plan --out kits/$tn/kit_preflight_sd35.json > logs/$tn.preflight.log 2>&1; echo "$tn preflight rc=$? $(tail -2 logs/$tn.preflight.log)"
done
