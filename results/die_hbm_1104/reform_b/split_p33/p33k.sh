set -e
# p33k.sh: commit part 33 RTL + bench, recipes, plan, kits.  Run after run_core PASS, on top of the tree that holds part 26.
A=/srv/opentallas-scratch2/claude/hbm-reform-b5; W=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt; cd $W; export PYTHONDONTWRITEBYTECODE=1
Q=results/die_hbm_1104/reform_b/split_p33; C=ot_hfd_coll_q2n2_body_core; R=rtl/hbm_accel/cores_split/reform_1105b
cp $A/q2n/mk_p33.py $A/q2n/mkseam.py $A/q2n/q2n_seam.json $A/q2n/p33p.sh $A/q2n/p33k.sh $A/q2n/gen/tb_q2n.sv $Q/ ; cp $A/q2n/eq.log $A/q2n/core.log $Q/
git add $R/ot_q2nf_split.sv $R/ot_q2nf_rest.sv $Q
printf "HBM q2n2_body: rest + g_qout tile, 0 added data cycles, lockstep benches, for part 33\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n" | git commit -q -F -
SC=$(git rev-parse HEAD); echo src $SC
python3 -I - $SC <<'E'
import json,sys
sc=sys.argv[1]; f='physical/die_plan/hbm_arch_cores/recipes_b2.json'; d=json.load(open(f))
base=dict(defines=[],params={},source='HBM-REFORM-B5 d44v part 33 tile of ot_hfd_coll_q2n2_body_core; bench results/die_hbm_1104/reform_b/split_p33/',source_commit=sc,read_at_commit=True,util=0.45)
R='rtl/hbm_accel/cores_split/reform_1105b/'
d['ot_q2nf_qout']=dict(top='ot_q2nf_qout',files=[R+'ot_q2nf_split.sv'],macros=[],**base)
d['ot_q2nf_rest']=dict(top='ot_q2nf_rest',files=[R+'ot_q2nf_rest.sv'],macros=['ot_sram_1r1w_256x256_m2_r2c2','ot_sram_1r1w_64x512_m1_r2c2','ot_sram_1rw_256x64_m4_r2c2'],**base)
json.dump(d,open(f,'w'),indent=1); open(f,'a').write('\n')
f='physical/die_plan/hbm/reset_contract.json'; x=json.load(open(f)); x['modules']=sorted(set(x['modules'])|{'ot_q2nf_qout','ot_q2nf_rest'}); json.dump(x,open(f,'w'),indent=1); open(f,'a').write('\n')
E
git add physical/die_plan/hbm_arch_cores/recipes_b2.json physical/die_plan/hbm/reset_contract.json
printf "HBM q2n2_body part 33: recipes for rest and tile\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n" | git commit -q -F -
git status --short | head -3
P=$A/plan33
python3 physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $P/die_plan.json --out $A/f33views.json 2>&1 | tail -1 | cut -c1-70
python3 -I - <<E > $A/f33v.txt
import json
for v in json.load(open('$A/f33views.json'))['view_list']:
  if v['module'] in ('ot_q2nf_qout','ot_q2nf_rest'): print(v['view'])
E
cat $A/f33v.txt; rm -rf $A/f33k
for V in $(cat $A/f33v.txt); do python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --views $A/f33views.json --view $V --out $A/f33k --clock-pin-entry on --core-macros auto --clock-taps density 2>&1 | tail -1 | cut -c1-160; done
ls $A/f33k; for k in $A/f33k/*; do ls $k | grep -c PROVENANCE; grep -cE 'core_multi_density|core_density_taps' $k/config.mk; grep -E 'DIE_AREA|CORE_UTIL|PLACE_DENSITY' $k/config.mk|cut -c1-70; done
