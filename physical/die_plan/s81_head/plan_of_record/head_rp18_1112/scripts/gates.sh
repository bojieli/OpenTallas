#!/bin/bash
# gates.sh TAG : HEAD-96 rp18 gates on epyc4 for pd/TAG.json (and rp17 baseline once): G0, G0C, reset summary, street, reach, gen x26, render
set -u; H=/srv/opentallas-scratch2/claude/head-96; W=/srv/opentallas-scratch2/claude/wt/head-96; R=/srv/opentallas-scratch3/claude/head-94/wtM8
G=$1; O=$H/g_$G; mkdir -p $O; PL=$H/pd/$G.json; cd $W
( python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "g0 rc=$?" >> $O/g0.log ) &
( python3 -I tools/die_plan/check.py $PL --completeness --out $O/g0c --quiet > $O/g0c.log 2>&1; echo "g0c rc=$?" >> $O/g0c.log ) &
( python3 -I $H/resetsum.py $W $PL $O/reset.json > $O/reset.log 2>&1; echo "reset rc=$?" >> $O/reset.log ) &
( python3 -I tools/die_plan/street_rule.py check $PL --die s81_head --repo $R --out $O/street.json > $O/street.log 2>&1; echo "street rc=$?" >> $O/street.log ) &
( python3 -I tools/die_plan/reach_fix.py check $PL --repo $R --json $O/reach.json --tsv $O/reach.tsv -j 8 > $O/reach.log 2>&1; echo "reach rc=$?" >> $O/reach.log ) &
( python3 -I $H/render_die.py $W $PL $O/render > $O/render.log 2>&1; echo "render rc=$?" >> $O/render.log ) &
if [ "${GEN:-1}" = 1 ]; then
  mkdir -p $O/gen
  one() { t=$1; K=$(mktemp -d -p $H); (cd $W && python3 -I tools/die_plan/gen.py phys $PL --clock-landing $H/pd/sidecar.json --types $t --out $K --rtl-root $W > $O/gen/$t.log 2>&1); echo "rc=$?" >> $O/gen/$t.log; rm -rf $K; }
  export -f one; export H W O PL
  python3 -I -c "import json,sys;print('\n'.join(sorted(json.load(open(sys.argv[1]))['partition_types'])))" $PL | xargs -P 6 -I{} bash -c 'one {}'
fi
wait
echo GATES_DONE $G
