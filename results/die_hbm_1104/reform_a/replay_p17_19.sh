#!/bin/bash
# HBM-REFORM-A3: merge TARGET (default hub/main) into this branch; d44v plan parts 17-19 are replayed on TARGET's plan because the plan files are binary.
#   replay_p17_19.sh TREE WORK [TARGET]. TREE: repo with this branch checked out. WORK: new dir. BASE_PLAN (env): unpacked d44v at PLAN_MB (cb98b2e232), default epyc4 hbm-reform-a/p17/base.
# Recipes and reset contract merge by key. lane1p tile tables stay as committed, so live forms and the wrapper stay valid. Nothing is committed until the checks print.
R=$1; W=$2; TGT=${3:-hub/main}; T=/srv/opentallas-scratch3/claude/hbm-reform-a; BP=${BASE_PLAN:-$T/p17/base}; PLAN_MB=cb98b2e232
cd $R; D=physical/die_plan/hbm/plan_of_record/d44v; A=results/die_hbm_1104/reform_a; TMP=$W.tmp; mkdir -p $TMP
OURS=$(git rev-parse HEAD); THEIRS=$(git rev-parse $TGT); MB=$(git merge-base HEAD $TGT); echo ours $OURS theirs $THEIRS base $MB
for s in "" __oneclk; do f=cores/ot_hbm_su_pg_lane1p_core__440.64x112.32__d44v_split$s.json; git show $OURS:$D/$f > $TMP/lane1p$s.json; done
git merge --no-commit --no-ff $TGT > $TMP/merge.log 2>&1; echo merge rc=$?; git diff --name-only --diff-filter=U | cut -c1-100
python3 -I - $OURS $THEIRS $MB $TMP <<'E'
import json,os,subprocess,sys
o,t,b,tmp=sys.argv[1:5]
sh=lambda r,f:subprocess.check_output(['git','show',f'{r}:{f}']).decode()
def wr(f,s):
    open(f+'.tmp','w').write(s); os.replace(f+'.tmp',f)
f='physical/die_plan/hbm_arch_cores/recipes_b2.json'; O,T_,B=[json.loads(sh(r,f)) for r in (o,t,b)]; X=dict(T_); c=[]
for k in set(O)|set(B):
    if O.get(k)!=B.get(k):
        if T_.get(k)!=B.get(k) and T_.get(k)!=O.get(k): c.append(k)
        if k in O: X[k]=O[k]
        else: X.pop(k,None)
print('recipes both changed',c); wr(f,json.dumps(X,indent=1)+"\n"); open(tmp+'/rec.json','w').write(json.dumps(X,indent=1)+"\n")
f='physical/die_plan/hbm/reset_contract.json'; O,T_,B=[json.loads(sh(r,f)) for r in (o,t,b)]; X=dict(T_)
X['modules']=sorted(set(T_['modules'])|set(O['modules'])); assert O['modules_basis'].startswith(B['modules_basis'].rstrip()); X['modules_basis']=T_['modules_basis'].rstrip()+O['modules_basis'][len(B['modules_basis'].rstrip()):]
wr(f,json.dumps(X,indent=1)+"\n"); open(tmp+'/con.json','w').write(json.dumps(X,indent=1)+"\n")
f='physical/die_plan/hbm/plan_of_record/d44v/README.md'; O,T_,B=[sh(r,f) for r in (o,t,b)]; assert O.startswith(B.rstrip()); wr(f,T_.rstrip()+"\n"+O[len(B.rstrip()):].rstrip()+"\n")
E
# plan files: TARGET's; every other d44v path keeps git's merge
git diff --name-only --diff-filter=U -- $D | grep -v README.md | while read f; do git checkout $TGT -- "$f"; done
rm -rf $W; mkdir -p $W/g0 $W/geom; cp -al $BP $W/base; mkdir $W/ov; git archive $TGT $D | tar -x -C $W/ov --strip-components=5
( cd $W/ov; find . -name '*.gz' -exec gunzip {} + )
git diff --name-only --no-renames $PLAN_MB $TGT -- $D | sed "s#^$D/##;s#\.gz\$##" > $W/ov.list
while read f; do mkdir -p $(dirname $W/base/$f); rm -f $W/base/$f; [ -f $W/ov/$f ] && cp $W/ov/$f $W/base/$f; done < $W/ov.list
rm -rf $W/ov; sha256sum $W/base/die_plan.json > $W/base.sha
[ "$(git show $TGT:$D/SHA256SUMS | awk '$2=="die_plan.json"{print $1}')" = "$(cut -d' ' -f1 $W/base.sha)" ] && echo base plan = target || { echo BASE PLAN MISMATCH; exit 3; }
cp -al $W/base $W/new
python3 $A/part17/mk_p17.py $W/new $A/part17 $R --wrapper-out $TMP/lane1p.sv 2>&1 | cut -c1-200 | tail -1
python3 $A/part18/mk_p18.py $W/new $A/part18 $R 2>&1 | cut -c1-200 | tail -1
python3 $A/part19/mk_p19.py $W/new $A/part19 $R 2>&1 | cut -c1-200 | tail -1
python3 -I $A/part19/rootmac.py $W/new | cut -c1-90
for s in "" __oneclk; do f=cores/ot_hbm_su_pg_lane1p_core__440.64x112.32__d44v_split$s.json; rm -f $W/new/$f; cp $TMP/lane1p$s.json $W/new/$f; done
for p in "rec physical/die_plan/hbm_arch_cores/recipes_b2.json" "con physical/die_plan/hbm/reset_contract.json"; do set -- $p; cp $TMP/$1.json $2.tmp; mv $2.tmp $2; done
sha256sum -c $W/base.sha
bash $T/p17/chk2.sh $W $R base > $W/chk_base.log 2>&1; bash $T/p17/chk2.sh $W $R new > $W/chk_new.log 2>&1; grep -E "by check|gone|FAIL count|^NEW 0|GONE" $W/chk_new.log | cut -c1-120
python3 -I $T/pkgpart.py $W/new $W/base $R | head -1
python3 -I results/die_hbm_1103/reform/g0cmp.py $W/g0/base/g0_report.json $W/g0/new/g0_report.json 2>&1 | cut -c1-300 > $D/g0/g0_diff_d44v_p14_p19.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $W/geom/plan_geom_base.json $W/geom/plan_geom_new.json 2>&1 | cut -c1-300 > $D/geom/geom_diff_d44v_p14_p19.txt
cd $W; PYTHONDONTWRITEBYTECODE=1 python3 $R/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $W/new/die_plan.json --out views.json 2>&1 | tail -1 | cut -c1-120
grep -oE '"(ot_hbm_su_pg_lane1p_core|ot_hbm_su_pg_lane_exp_x_core|ot_hbm_su_pg_lane_full_x_core|ot_hbm_su_pg_sfu_s_core|ot_hgi_coll_tkm_tp192_htile_core|ot_hgi_coll_tkm_m_tp192__root)@[0-9a-f]{12}"' views.json | sort -u
echo REPLAY DONE
