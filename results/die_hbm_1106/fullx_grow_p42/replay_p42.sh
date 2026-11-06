#!/bin/bash
# HBM-FORM-SPLIT-13-FULLX d44v part 42 replay: ot_hbm_su_pg_lane_full_x_core +34.56 local E (354.24 x 207.36), __s partner x +34.56.
# Run from the repo root.   replay_p42.sh RR   (RR = new work dir).  Unpacks d44v into RR/base, applies mk_p42.py (+ ft_nudge,
# ft_reach_fix as ev76) on RR/new, then G0 + plan-time GEOM base vs new, render.  PACK=1 packages RR/new into d44v.
set -e
RR=$1; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1106/fullx_grow_p42
rm -rf $RR; mkdir -p $RR/base/cores $RR/g0 $RR/geom
for f in $D/*.json $D/*.json.gz; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/$n;; *) cp $f $RR/base/$n;; esac; done
for f in $D/cores/*; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/cores/$n;; *) cp $f $RR/base/cores/$n;; esac; done
python3 -I results/die_hbm_1105/q3split_p34/fill_cores.py $RR/base ${CORES_FILL:-/srv/opentallas-scratch3/claude/die-hbm-60-plan/p/d44v11/cores}
cp -r $RR/base $RR/new
python3 -I $F/mk_p42.py $RR/new | tee $RR/mk.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/new/die_plan.json $RR/new/die_plan.nudged.json $RR/ft_nudge_ledger.json && mv $RR/new/die_plan.nudged.json $RR/new/die_plan.json
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_reach_fix.py $RR/new/die_plan.json $RR/new/die_plan.reach.json $RR/ft_reach_ledger.json || true; [ -f $RR/new/die_plan.reach.json ] && mv $RR/new/die_plan.reach.json $RR/new/die_plan.json
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do ( timeout 1800 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 1800 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -14 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -12 | tee $RR/geom.txt
python3 $F/render_p42.py $RR/base $RR/new $RR/p42_q_su.png
if [ "${PACK:-0}" = 1 ]; then
  python3 -I results/die_hbm_1103/reform/package.py $RR/new $RR/base $D | tail -1
  if [ -f $D/core_macros.json.gz ] && git ls-files --error-unmatch $D/core_macros.json > /dev/null 2>&1; then zcat $D/core_macros.json.gz > $D/core_macros.json; rm $D/core_macros.json.gz; fi
  python3 -I - $D <<'P'
import gzip, hashlib, sys
from pathlib import Path
D = Path(sys.argv[1])
L = [l.split(None, 1) for l in (D / 'SHA256SUMS').read_text().splitlines() if l.strip()]
names = [n for _, n in L]
cur = {}
for f in list(D.glob('*')) + list(D.glob('cores/*')):
    if f.is_file() and f.name not in ('SHA256SUMS', 'README.md'):
        n = str(f.relative_to(D)).removesuffix('.gz'); b = f.read_bytes()
        cur[n] = hashlib.sha256(gzip.decompress(b) if f.name.endswith('.gz') else b).hexdigest()
ch = 0
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a: L[i] = [cur[n], n]; ch += 1
new = [n for n in cur if n not in names and (n.endswith('__d44v_p42.json') or n == 'part42_event.json')]
L += [[cur[n], n] for n in sorted(new)]
(D / 'SHA256SUMS').write_text(''.join(f'{a}  {n}\n' for a, n in L)); print('SHA256SUMS changed', ch, 'added', new)
P
  (cd $D; for n in die_plan.json core_conns.json clock_entries.json; do a=$(zcat $n.gz | sha256sum | cut -c1-64); grep -q "^$a  $n$" SHA256SUMS && echo ok $n || echo BAD $n; done)
fi
echo REPLAY DONE
