#!/bin/bash
# DIE-S81-8 packed-G freeze-gate CA + die STA (S81 gate form: MESO-START-2 --start-skew-clean + STA hull, spice, --cppr-lca,
# key region; COORD 03:22/03:36) on Codex clock_G_body (fresh GRT0 TT/FF), + NUMBER-CHECK nc_ca_ocv.py.  usage: gate_pg.sh SPICE (per-corner TT x1.0485 / FF x1.0552 via ca_spice.py, DIE-S81-7 recipe)
set -u
S=${1:?}; MAP=/srv/opentallas-scratch2/claude/die-s81-5/feed/map_part.json; WT=/srv/opentallas-scratch2/claude/wt/die-s81-8; MT=$WT/tools/die_plan; SC=$WT/results/die_s81_8_1028/scripts
CB=/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body; PR=$CB/proof_body; X=$CB/routed/lpo.json
PL=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json; O=/srv/opentallas-scratch2/claude/die-s81-8/gate_s$S; mkdir -p $O
F="--start-skew 46.9,79.4 --start-skew-clean --sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca"
(cd $O && python3 $SC/ca_spice.py $X $MAP $O/sp 1.0485 1.0552 --mc 0 > $O/ca.log 2>&1); echo "ca_spice rc $?"; X=$O/sp_xing_lpo.json
python3 $MT/count_align_plan.py $X $F --out $O/plan.json > $O/plan.log 2>&1; echo "plan rc $?"
python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --out $O/bind.json > $O/bind.log 2>&1; echo "bind rc $?"
for K in region part; do
python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_$K --corner TT --corner FF --clock-ocv table --clock-droop shared \
  --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice \
  --count-align $O/bind.json --count-align-key $K > $O/sta_$K.log 2>&1; echo "sta $K rc $?"; grep -E "COUNT-ALIGN|intra " $O/sta_$K.log
done
python3 -I -c "
import json;d=json.load(open('$O/sta_region/die_sta_related.json'))
for c in ('TT','FF'): json.dump(d['corners'][c]['register'],open('$O/reg_'+c+'.json','w'))"
python3 -I $SC/nc_ca_ocv.py $MT $PR $PL $O/bind.json $O/nc_ca_ocv.json; echo "nc rc $?"
echo DONE $(date)
