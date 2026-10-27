#!/bin/bash
# HBM-CORES-R7 kit wave launcher: for every new *_k2 kit (SU-first order from wave_order.json): clock-port track snap,
# FF-binding check (config.mk OT_VCLK_FF == sdc_lint.json insertion_ff_ps), then ot-run (staged kit, any of
# intel1/intel2/epyc2) run_kit_hbm.sh GOAL=place (outline <= 0.45 mm2) or GOAL=synth (larger: cell count first, 400k cap).
set -u
D=/srv/opentallas-scratch2/claude/hbm-cores-r7; W=/srv/opentallas-scratch2/claude/wt/hbm-cores-r7-1027
mkdir -p $D/logs
for m in $(python3 -c "import json;print(' '.join(json.load(open('$D/wave_order.json'))['order']))"); do
  K=$(ls -d $D/kits/${m}_*-_k2 2>/dev/null | head -1); [ -n "$K" ] || continue
  [ -e $K/.r7_launched ] && continue
  python3 $W/results/hbm_cores_r7/scripts/clkpin_snap.py $K > $K/clkpin_snap.log 2>&1 || { echo "SKIP $m clkpin: $(tail -1 $K/clkpin_snap.log)"; echo clkpin > $K/.r7_launched; continue; }
  ff=$(sed -n 's/^export OT_VCLK_FF *= *//p' $K/config.mk); fj=$(python3 -c "import json;print(json.load(open('$K/sdc_lint.json')).get('insertion_ff_ps'))")
  python3 -c "import sys;sys.exit(0 if abs(float('$ff')-float('$fj'))<=0.5 else 1)" 2>/dev/null || { echo "SKIP $m FF binding cfg=$ff json=$fj"; echo ffbind > $K/.r7_launched; continue; }
  a=$(python3 -c "import re;t=open('$K/config.mk').read();x=re.search(r'DIE_AREA = 0 0 ([\d.]+) ([\d.]+)',t);print(float(x.group(1))*float(x.group(2))/1e6)")
  read G M T < <(python3 -c "a=$a;print(*(('place',16,8) if a<0.1 else ('place',24,8) if a<0.25 else ('place',32,16) if a<0.45 else ('synth',48,16)))")
  echo "$G $M $T area=$a" > $K/.r7_launched
  nohup ~/.local/bin/ot-run --mem $M --threads $T --dir $K --stage $K -- bash $K/run_kit_hbm.sh $K $G $M $T > $D/logs/$(basename $K).$G.log 2>&1 < /dev/null &
  echo "LAUNCH $m $G mem=$M thr=$T area=$a"; sleep 2
done
