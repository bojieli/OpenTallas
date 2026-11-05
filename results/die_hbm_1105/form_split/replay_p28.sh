#!/bin/bash
# HBM part 28 replay: q3_body -> CTL + 4 x QCOL4 on the plan of this checkout. Inputs: S base plan dir with the cores/ tree (BASE), base commit (PB). Run from the worktree root.
set -e
S=${S:-/srv/opentallas-scratch3/claude/hfs2}; W=$S/wtw; BASE=${BASE:-/srv/opentallas-scratch2/claude/hfs/rp/new}; PB=${PB:-4a9c74c7d4}; cd $W; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; RR=$S/rp28; F=results/die_hbm_1105/form_split; rm -rf $RR; mkdir -p $RR/g0 $RR/geom $RR/ov
[ "$(git show $PB:$D/SHA256SUMS | awk '$2=="die_plan.json"{print $1}')" = "$(sha256sum $BASE/die_plan.json | cut -d' ' -f1)" ] && echo base = PB plan || { echo BASE not PB; exit 4; }
cp -r $BASE $RR/base; git archive HEAD $D | tar -x -C $RR/ov --strip-components=5; (cd $RR/ov; find . -name '*.gz' -exec gunzip {} +)
git diff --name-only --no-renames $PB HEAD -- $D | sed "s#^$D/##;s#\.gz\$##" > $RR/ov.list; wc -l < $RR/ov.list
while read f; do mkdir -p $(dirname $RR/base/$f); rm -f $RR/base/$f; [ -f $RR/ov/$f ] && cp $RR/ov/$f $RR/base/$f; done < $RR/ov.list
[ "$(awk '$2=="die_plan.json"{print $1}' $RR/ov/SHA256SUMS)" = "$(sha256sum $RR/base/die_plan.json | cut -d' ' -f1)" ] && echo base plan = main || { echo MISMATCH; exit 3; }
rm -rf $RR/ov; cp -al $RR/base $RR/new
python3 -I -c "
import os,sys
p=sys.argv[1]; d=open(p).read(); os.unlink(p); open(p,'w').write(d)" $RR/new/die_plan.json
python3 -I results/die_hbm_1103/reform/mk_split.py $RR/new $F/p28/split_p28.json $F/p28 --only ot_hfd_coll_q3_body_core 2>&1 | tail -2 | cut -c1-300
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do [ -f $RR/$N/core_conns.json ] || zcat $RR/$N/core_conns.json.gz > $RR/$N/core_conns.json; ( timeout 900 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 900 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -12 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -10 | tee $RR/geom.txt
cd $RR; python3 $W/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $RR/new/die_plan.json --out $RR/views.json 2>&1 | tail -1 | cut -c1-100
grep -oE '"(ot_hfd_coll_q3_body_ctl|ot_hfd_coll_q3_qcol4)@[0-9a-f]{12}"' $RR/views.json | sort -u
echo DONE
