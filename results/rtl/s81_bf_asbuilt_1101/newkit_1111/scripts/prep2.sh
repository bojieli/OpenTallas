#!/bin/bash
# prepare the three as-built BF benches WITH the bound-plan seam stages (runs2), then the leaf-latency check plain vs fixed
D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; R=$D/root; C=$D/code
PLAN=$R/physical/die_plan/s81/plan_h2_2249.json
mkdir -p $D/runs2 $D/leaflat; cd /
for sv in col_h9:asb_x col_h9:asb_nx col_h10:asb_x; do
  M=${sv%%:*}; Vr=${sv#*:}; O=$D/runs2/${M}_${Vr}; W=$D/fsaw/${M}_${Vr#asb_}
  if [ ! -f $O/manifest.json ]; then
  python3 -I $C/tools/s81_dv/bf_asbuilt_1101/prepare.py --source $R --schedule $D/sched/${M}_l4_lp_${Vr}_schedule.json \
    --out $O --master $M --variant $Vr --native-bf-family --defines-manifest physical/die_plan/s81/bind/frame_asbuilt.json --bound-plan $PLAN
  echo "PREP $M $Vr rc=$?"
  fi
  python3 -I -c "import json;m=json.load(open('$O/manifest.json'));print(m['bound_plan'])"
  for k in runs runs2; do
    ME=""; [ -f $D/$k/${M}_${Vr}/measure.json ] && ME="--measure $D/$k/${M}_${Vr}/measure.json"
    BFASB_ROOT=$R python3 -I $D/pyrun.py $C/tools/s81_dv/bf_asbuilt_1101/bench_leaf_latency.py --bench $D/$k/${M}_${Vr} \
      --schedule $D/sched/${M}_l4_lp_${Vr}_schedule.json --work $W --source-root $R $ME --out $D/leaflat/${k}_${M}_${Vr}.json
    echo "LEAFLAT $k $M $Vr rc=$?"
  done
done
