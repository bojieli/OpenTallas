#!/bin/bash
# stn_resignoff.sh <src> <route dir> <master> <ckins_ss> <ckins_ff_min> <ckins_ff_max>: margin sign-off of a routed view with a
# corner-true vclk latency (no re-route): SS setup against stn_margin_sdc.py signoff at the SS insertion, FF hold
# against the same file at the FF minimum insertion; corner_sta.json = SS setup of the first + FF hold of the second.
S=$1; W=$2; m=$3; L=$4; LF=$5; LX=$6
cd $S; V=physical/hbm_accel_die_views/stations/$m/$m.sdc
B=$(ls -d $W/work/orfs/results/asap7/*/base); rel=${B#$W/work/orfs/}
python3 physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py $V $L signoff $LF $LX > $W/signoff.sdc
python3 physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py $V $L signoff $LF $LX > $W/signoff_ff.sdc
mkdir -p $W/signoff_ff/$rel
for f in 6_final.odb 6_final.spef; do ln -f $W/signoff/$rel/$f $W/signoff_ff/$rel/$f 2>/dev/null || cp $W/signoff/$rel/$f $W/signoff_ff/$rel/$f; done
cp $W/signoff.sdc $W/signoff/$rel/6_final.sdc; cp $W/signoff_ff.sdc $W/signoff_ff/$rel/6_final.sdc
python3 tools/w18/corner_sta.py --orfs-dir $W/signoff --output $W/corner_sta_ss.json > $W/corner_signoff.log 2>&1; r1=$?
python3 tools/w18/corner_sta.py --orfs-dir $W/signoff_ff --output $W/corner_sta_ff.json > $W/corner_signoff_ff.log 2>&1; r2=$?
python3 - $W <<'PY'
import json, sys
w = sys.argv[1]
ss = json.load(open(f'{w}/corner_sta_ss.json')); ff = json.load(open(f'{w}/corner_sta_ff.json'))
out = dict(ss); out['hold_ff'] = ff['hold_ff']
out['closes_signoff'] = bool(ss['setup_ss']['worst_slack_ps'] >= 0 and ff['hold_ff']['worst_slack_ps'] >= 0)
out['corner_true_vclk'] = dict(setup_from='corner_sta_ss.json', hold_from='corner_sta_ff.json')
json.dump(out, open(f'{w}/corner_sta.json', 'w'), indent=1)
PY
echo "resignoff_corner_rc=$((r1+r2))" >> $W/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $m --out $W/view --interface-sdc $W/signoff.sdc --tmp-dir $W/abs_tmp3 > $W/export_resignoff.log 2>&1; echo "resignoff_export_rc=$?" >> $W/exit
python3 -c "import json;j=json.load(open('$W/margin.json'));j['ckins_ff_min_ps']=$LF;j['ckins_ff_max_ps']=$LX;j['resignoff']='corner-true vclk (stn_resignoff.sh)';json.dump(j,open('$W/margin.json','w'))"
