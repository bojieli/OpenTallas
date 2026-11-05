set -e
S=/srv/opentallas-scratch2/claude/hfs; W=$S/wt; cd $W; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; RR=$S/rp; rm -rf $RR; mkdir -p $RR/g0 $RR/geom $RR/ov
PB=e99e7043f4; [ "$(git show $PB:$D/SHA256SUMS | awk '$2=="die_plan.json"{print $1}')" = "$(sha256sum $S/base/die_plan.json | cut -d' ' -f1)" ] && echo base = e99e plan || { echo S/base not e99e; exit 4; }
cp -al $S/base $RR/base; git archive HEAD $D | tar -x -C $RR/ov --strip-components=5; (cd $RR/ov; find . -name '*.gz' -exec gunzip {} +)
git diff --name-only --no-renames $PB HEAD -- $D | sed "s#^$D/##;s#\.gz\$##" > $RR/ov.list; wc -l < $RR/ov.list
while read f; do mkdir -p $(dirname $RR/base/$f); rm -f $RR/base/$f; [ -f $RR/ov/$f ] && cp $RR/ov/$f $RR/base/$f; done < $RR/ov.list
[ "$(awk '$2=="die_plan.json"{print $1}' $RR/ov/SHA256SUMS)" = "$(sha256sum $RR/base/die_plan.json | cut -d' ' -f1)" ] && echo base plan = main || { echo MISMATCH; exit 3; }
rm -rf $RR/ov; cp -al $RR/base $RR/new
python3 -I - <<E
import json,os
f="$RR/new/die_plan.json"; D=json.load(open(f)); n={}
for k,T in D["partition_types"].items():
  for h in T.get("hard_cores",[]):
    m=h["module"]
    if m=="ot_hgi_sfu_core_split3__opstore_a": h["outline_um"]=[760.32,552.96]; n[m]=n.get(m,0)+1
    if m=="ot_hgi_coll_gq_issue": h["outline_um"]=[328.32,233.28]; n[m]=n.get(m,0)+1
os.unlink(f); json.dump(D,open(f,"w"),indent=1); open(f,"a").write("\n"); print(n)
E
F=results/die_hbm_1105/form_split
python3 -I results/die_hbm_1103/reform/mk_split.py $RR/new $F/p27/split_p27.json $F/p27 --only ot_hgi_sfu_core_split3__opstore_a,ot_hgi_sfu_core_split3__opstore_b 2>&1 | tail -2 | cut -c1-300
python3 -I results/die_hbm_1103/reform/mk_split.py $RR/new $F/p29/split_p29.json $F/p29 --only ot_hgi_coll_gq_issue 2>&1 | tail -2 | cut -c1-300
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do [ -f $RR/$N/core_conns.json ] || zcat $RR/$N/core_conns.json.gz > $RR/$N/core_conns.json; ( timeout 900 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 900 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -12 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -10 | tee $RR/geom.txt
cd $RR; python3 $W/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $RR/new/die_plan.json --out $RR/views.json 2>&1 | tail -1 | cut -c1-100
grep -oE '"(ot_hgi_sfu_ops[ab]_[a-z0-9]+|ot_hgi_coll_gqi_issue|ot_hgi_gq_aq_tile)@[0-9a-f]{12}"' $RR/views.json | sort -u
echo DONE
