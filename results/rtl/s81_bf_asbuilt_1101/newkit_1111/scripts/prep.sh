#!/bin/bash
# prepare the three as-built BF benches on the new-kit root
D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; R=$D/root; C=$D/code
mkdir -p $D/runs; cd /
for sv in col_h9:asb_x col_h9:asb_nx col_h10:asb_x; do
  M=${sv%%:*}; Vr=${sv#*:}; O=$D/runs/${M}_${Vr}
  [ -d $O ] && { echo "exists $O"; continue; }
  python3 -I $C/tools/s81_dv/bf_asbuilt_1101/prepare.py --source $R --schedule $D/sched/${M}_l4_lp_${Vr}_schedule.json \
    --out $O --master $M --variant $Vr --native-bf-family --defines-manifest physical/die_plan/s81/bind/frame_asbuilt.json
  echo "PREP $M $Vr rc=$?"
  python3 -I -c "import json;m=json.load(open('$O/manifest.json'));print({k:m[k] for k in ('overlay_instances','cfg_image_instances','plan_kit','plan_kit_sha256','quiescent_q_modules','xo_forwarding_qualification')})"
done
