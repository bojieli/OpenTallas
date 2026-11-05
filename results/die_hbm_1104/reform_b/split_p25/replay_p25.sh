#!/bin/bash
# HBM-REFORM-B4: merge TARGET into this branch; d44v part 25 is replayed on TARGET's plan because the plan files are binary.
#   replay_p25.sh TREE WORK TARGET. WORK: new dir. BASE_PLAN (env): unpacked d44v at PLAN_MB. Nothing is committed.
set -u
R=$1; W=$2; TGT=$3; BP=${BASE_PLAN:-/srv/opentallas-scratch3/claude/hbm-reform-b3/plan24}; PLAN_MB=${PLAN_MB:-5ebd22920c}
export PYTHONDONTWRITEBYTECODE=1
cd $R; D=physical/die_plan/hbm/plan_of_record/d44v; Q=results/die_hbm_1104/reform_b/split_p25; TMP=$W.tmp; rm -rf $TMP; mkdir -p $TMP
OURS=$(git rev-parse HEAD); THEIRS=$(git rev-parse $TGT); MB=$(git merge-base HEAD $TGT); echo ours $OURS theirs $THEIRS base $MB
git merge --no-commit --no-ff $TGT > $TMP/merge.log 2>&1; echo merge rc=$?; git diff --name-only --diff-filter=U | cut -c1-100
python3 -I - $OURS $THEIRS $MB <<'E'
import json,os,subprocess,sys
o,t,b=sys.argv[1:4]
sh=lambda r,f:subprocess.check_output(['git','show',f'{r}:{f}']).decode()
def wr(f,s):
    open(f+'.tmp','w').write(s); os.replace(f+'.tmp',f)
f='physical/die_plan/hbm_arch_cores/recipes_b2.json'; O,T,B=[json.loads(sh(r,f)) for r in (o,t,b)]; X=dict(T); c=[]
for k in set(O)|set(B):
    if O.get(k)!=B.get(k):
        if T.get(k)!=B.get(k) and T.get(k)!=O.get(k): c.append(k)
        if k in O: X[k]=O[k]
        else: X.pop(k,None)
print('recipes both changed',c); wr(f,json.dumps(X,indent=1)+"\n")
f='physical/die_plan/hbm/reset_contract.json'; O,T,B=[json.loads(sh(r,f)) for r in (o,t,b)]; X=dict(T)
X['modules']=sorted(set(T['modules'])|set(O['modules'])); wr(f,json.dumps(X,indent=1)+"\n")
f='physical/die_plan/hbm/plan_of_record/d44v/README.md'; O,T,B=[sh(r,f) for r in (o,t,b)]; assert O.startswith(B.rstrip()); wr(f,T.rstrip()+"\n"+O[len(B.rstrip()):].rstrip()+"\n")
E
git diff --name-only --diff-filter=U -- $D | grep -v README.md | while read f; do git checkout $TGT -- "$f"; done
git add physical/die_plan/hbm_arch_cores/recipes_b2.json physical/die_plan/hbm/reset_contract.json $D/README.md
rm -rf $W; mkdir -p $W/g0 $W/geom; cp -a $BP $W/base; mkdir $W/ov; git archive $TGT $D | tar -x -C $W/ov --strip-components=5
( cd $W/ov; find . -name '*.gz' -exec gunzip {} + )
git diff --name-only --no-renames $PLAN_MB $TGT -- $D | sed "s#^$D/##;s#\.gz\$##" > $W/ov.list
while read f; do mkdir -p $(dirname $W/base/$f); rm -f $W/base/$f; [ -f $W/ov/$f ] && cp $W/ov/$f $W/base/$f; done < $W/ov.list
rm -rf $W/ov
[ "$(git show $TGT:$D/SHA256SUMS | awk '$2=="die_plan.json"{print $1}')" = "$(sha256sum $W/base/die_plan.json | cut -d' ' -f1)" ] && echo base plan = target || { echo BASE PLAN MISMATCH; exit 3; }
cp -a $W/base $W/new
python3 -I $Q/mk_p25.py $W/new
python3 -I results/die_hbm_1103/reform/mk_split.py $W/new $Q/split_p25.json $Q 2>&1 | tail -2 | cut -c1-240
sed -i '/ot_wbq_root__\|ot_wbq_sw__/d' $D/SHA256SUMS
python3 -I /srv/opentallas-scratch3/claude/hbm-reform-b3/pk.py $W/new $W/base $D | cut -c1-300
python3 -I results/die_hbm_1103/reform/package.py $W/new $W/base $D | tail -1 | cut -c1-80
cp $D/split_event.json $D/part25_event.json; git show $TGT:$D/split_event.json > $D/split_event.json
python3 -I - <<'E'
import hashlib
D='physical/die_plan/hbm/plan_of_record/d44v/'
h=lambda n:hashlib.sha256(open(D+n,'rb').read()).hexdigest()
L=[l.split(None,1) for l in open(D+'SHA256SUMS').read().splitlines() if l.strip()]
N=[n for a,n in L]
if 'part25_event.json' not in N: L.append(('', 'part25_event.json'))
open(D+'SHA256SUMS','w').write(''.join(f'{h(n) if n in("split_event.json","part25_event.json") else a}  {n}\n' for a,n in L))
E
(cd $D; for n in die_plan.json core_conns.json clock_entries.json; do a=$(zcat $n.gz | sha256sum | cut -c1-64); grep -q "^$a  $n$" SHA256SUMS && echo ok $n || echo BAD $n; done)
python3 physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $W/new/die_plan.json --out $W/views.json 2>&1 | tail -1 | cut -c1-60
grep -oE '"(ot_wbq_root|ot_wbq_sw)@[0-9a-f]{12}"' $W/views.json | sort -u
git status --short | grep -E '^(UU|AA|DU|UD)' | cut -c1-100
echo REPLAY DONE
