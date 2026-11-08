#!/bin/bash
# DIE-HBM-90-PEV expx328_1107 replay. Run from the repo root.  [BASE_REV=origin/main] replay.sh RR
# base = d35a, d35b, d35c, d44v laid in order (as release_tree_plan materialize_plan), gunzipped; new = base + mk_expx328.py + ft_nudge + ft_reach_fix.
set -e
RR=$1; export PYTHONDONTWRITEBYTECODE=1
POR=physical/die_plan/hbm/plan_of_record; F=results/die_hbm_1107/expx328
REV=${BASE_REV:-origin/main}   # the plan of record the event applies to (never the working tree)
rm -rf $RR; mkdir -p $RR/base $RR/g0 $RR/src
git archive $REV $POR/d35a $POR/d35b $POR/d35c $POR/d44v | tar -x -C $RR/src; git rev-parse $REV > $RR/base_rev
for d in d35a d35b d35c d44v; do S=$RR/src/$POR/$d; (cd $S; find . -type f ! -name SHA256SUMS ! -name README.md) | while read f; do f=${f#./}; o=$RR/base/${f%.gz}; mkdir -p $(dirname $o); case $f in *.gz) zcat $S/$f > $o;; *) cp $S/$f $o;; esac; done; done
rm -rf $RR/src
cp -r $RR/base $RR/new
python3 $F/mk_expx328.py $RR/new | tee $RR/mk.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/new/die_plan.json $RR/new/die_plan.nudged.json $RR/ft_nudge_ledger.json > $RR/ft_nudge.log 2>&1 && mv $RR/new/die_plan.nudged.json $RR/new/die_plan.json; tail -3 $RR/ft_nudge.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_reach_fix.py $RR/new/die_plan.json $RR/new/die_plan.reach.json $RR/ft_reach_ledger.json > $RR/ft_reach.log 2>&1 || true; tail -3 $RR/ft_reach.log; [ -f $RR/new/die_plan.reach.json ] && mv $RR/new/die_plan.reach.json $RR/new/die_plan.json
# ft_nudge re-sites the bit cells of bit_sites slots but keeps regs_um (the per-stage middle-bit site the die lane
# geometry uses): re-derive regs_um[1:] from the moved bits (ft_s0_resite --medoid-fix), else G0C street_die_leg sees
# stations inside the moved __s cores.
SL=$(python3 -I -c "import json,sys; print(','.join(sorted({r['type']+'/'+r['slot'] for r in json.load(open(sys.argv[1])) if r.get('mode')=='bit_sites' and r.get('bits_moved')})))" $RR/ft_nudge_ledger.json)
echo "medoid-fix: $SL"
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_s0_resite.py --medoid-fix $RR/new/die_plan.json $RR/new/die_plan.medoid.json "$SL" && mv $RR/new/die_plan.medoid.json $RR/new/die_plan.json
python3 -I -c "import json,sys; f=sys.argv[1]; d=json.load(open(f)); open(f,'w').write(json.dumps(d))" $RR/new/die_plan.json   # compact, as d44v on main
echo PLAN_READY
