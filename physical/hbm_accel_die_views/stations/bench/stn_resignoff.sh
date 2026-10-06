#!/bin/bash
# stn_resignoff.sh <src> <route dir> <master> <ckins_ss> <ckins_ff_min>: re-run the margin sign-off (corner STA + SS/FF
# ETM) of a routed view against stn_margin_sdc.py signoff with the corner-true vclk latency (no re-route).
S=$1; W=$2; m=$3; L=$4; LF=$5
cd $S; V=physical/hbm_accel_die_views/stations/$m/$m.sdc
B=$(ls -d $W/work/orfs/results/asap7/*/base); rel=${B#$W/work/orfs/}
python3 physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py $V $L signoff $LF > $W/signoff.sdc
cp $W/signoff.sdc $W/signoff/$rel/6_final.sdc
[ -f $W/corner_sta.json ] && mv $W/corner_sta.json $W/corner_sta_prev.json
python3 tools/w18/corner_sta.py --orfs-dir $W/signoff --output $W/corner_sta.json > $W/corner_signoff.log 2>&1; echo "resignoff_corner_rc=$?" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $m --out $W/view --interface-sdc $W/signoff.sdc --tmp-dir $W/abs_tmp3 > $W/export_resignoff.log 2>&1; echo "resignoff_export_rc=$?" >> $W/exit
python3 -c "import json;j=json.load(open('$W/margin.json'));j['ckins_ff_min_ps']=$LF;j['resignoff']=True;json.dump(j,open('$W/margin.json','w'))"
