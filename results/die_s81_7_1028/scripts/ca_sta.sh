#!/bin/bash
# DIE-S81-7: CA plan on the ONE interval model (count_align_plan --sta-proof: hull of the landed_phase_ocv derated
# interval and die_sta_related.count_align_d_intervals, spice clock, CPPR at LCA) -> count_align_bind -> gate die STA
# --count-align --count-align-key region --clock-cal spice --cppr-lca.  usage: ca_sta.sh V SCALE
set -u
V=$1; S=$2; WT=/srv/opentallas-scratch2/claude/wt/die-s81-7; MT=$WT/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-7
PL=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json; PR=$O/proof_$V; R=$O/CAS_${V}_$S; mkdir -p $R
python3 $MT/count_align_plan.py $O/lpo_$V.json --scale $S --mc-chips 2000 --sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --out $R/plan.json > $R/plan.log 2>&1; echo PLAN_RC $?
python3 -c "import json;d=json.load(open('$R/plan.json'))['summary'];print({k:d.get(k) for k in ('fail','worst_margin_lo_ps','worst_margin_lo_port','depth4','depth8','below_100ps','max_path_ambiguous_cycles','sta_hull')})"
python3 $WT/results/die_s81_7_1028/scripts/bind_parts_plan.py $R/plan.json $O/lpo_$V.json --scale $S --samples 2000 --out $R/bind.json > $R/bind.log 2>&1; echo BIND_RC $?
grep -E "sim_window_violations|sim_min_margin" $R/bind.log | head -3
for KEY in region part; do
python3 -I $MT/die_sta_related.py $PR --plan $PL --out $R/sta_$KEY --cppr-lca --clock-ocv table --clock-droop shared --clock-cal spice \
  --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers HB4 --landing-window-ps 416.5 \
  --count-align $R/bind.json --count-align-key $KEY > $R/sta_$KEY.log 2>&1; echo STA_RC $KEY $?
python3 -c "
import json;d=json.load(open('$R/sta_$KEY/die_sta_related.json'))
for C in ('TT','FF'):
  x=d['count_aligned'][C]; print('$KEY',C,{k:x[k] for k in ('key','landed_tags','unbound','crossings','sta_timed','tree_plan','no_taps','fail','verdict')}, 'worst_lo', x['worst_lo'] if not isinstance(x['worst_lo'],dict) else {k:x['worst_lo'].get(k) for k in ('port','margin_lo_ps')})
print('SUMMARY', json.dumps(d['summary'])[:700])"
done
echo CAS_DONE $(date)
