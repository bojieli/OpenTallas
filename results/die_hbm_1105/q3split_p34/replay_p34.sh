#!/bin/bash
# HBM-GAPS-4-Q3SPLIT d44v part 34 replay: ot_hfd_coll_q3_edge_core -> ot_hfd_coll_q3_edge_arg + 3 x ot_hfd_coll_q3_edge_link
# in the same slot (276.48 x 1054.08, origin kept).  Run from the repo root of this branch.
#   replay_p34.sh BASE RR      BASE = unpacked d44v of the base commit PB (env, default the merge base with main), RR = new work dir
# Writes RR/new (plan), RR/g0, RR/geom, RR/views.json; PACK=1 also packages RR/new into the d44v dir (+ part34_event.json, SHA256SUMS).
set -e
BASE=$1; RR=$2; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1105/q3split_p34
[ "$(awk '$2=="die_plan.json"{print $1}' $D/SHA256SUMS)" = "$(sha256sum $BASE/die_plan.json | cut -d' ' -f1)" ] || [ -n "$PACKED" ] || { echo BASE plan is not this checkout; exit 3; }
rm -rf $RR; mkdir -p $RR/g0 $RR/geom; cp -r $BASE $RR/base; cp -r $BASE $RR/new
for N in base new; do python3 -I $F/fill_cores.py $RR/$N ${CORES_FILL:-/srv/opentallas-scratch2/claude/kit-wave/hbm/d44v11/cores}; done   # views_b2r2.py needs the 17 core files kept outside git
python3 -I results/die_hbm_1103/reform/mk_split.py $RR/new $F/split_p34.json $F --only ot_hfd_coll_q3_edge_core 2>&1 | tail -3 | cut -c1-300
python3 -I $F/mk_p34pins.py $RR/new
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do ( timeout 1800 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 1800 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -14 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -12 | tee $RR/geom.txt
R=$PWD; (cd $RR; python3 $R/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $RR/new/die_plan.json --out $RR/views.json 2>&1 | tail -1 | cut -c1-100)
grep -oE '"(ot_hfd_coll_q3_edge_link|ot_hfd_coll_q3_edge_arg)@[0-9a-f]{12}"' $RR/views.json | sort -u
if [ "${PACK:-0}" = 1 ]; then
  python3 -I results/die_hbm_1103/reform/package.py $RR/new $RR/base $D | tail -1
  # core_macros.json is tracked plain (> 200 kB already); keep it plain, no second .gz copy (HBM-GAPS-5-Q3SPLIT)
  if [ -f $D/core_macros.json.gz ] && git ls-files --error-unmatch $D/core_macros.json > /dev/null 2>&1; then zcat $D/core_macros.json.gz > $D/core_macros.json; rm $D/core_macros.json.gz; fi
  mv $D/split_event.json $D/part34_event.json; if git cat-file -e HEAD:$D/split_event.json 2>/dev/null; then git show HEAD:$D/split_event.json > $D/split_event.json; fi
  python3 -I - $D $RR/new <<'P'
import gzip, hashlib, sys
from pathlib import Path
D, N = Path(sys.argv[1]), Path(sys.argv[2])
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
new = [n for n in cur if n not in names and (n.startswith('cores/ot_hfd_coll_q3_edge_') and 'd44v_split' in n or n == 'part34_event.json')]
L += [[cur[n], n] for n in sorted(new)]
(D / 'SHA256SUMS').write_text(''.join(f'{a}  {n}\n' for a, n in L)); print('SHA256SUMS changed', ch, 'added', new)
P
  (cd $D; for n in die_plan.json core_conns.json clock_entries.json; do a=$(zcat $n.gz | sha256sum | cut -c1-64); grep -q "^$a  $n$" SHA256SUMS && echo ok $n || echo BAD $n; done)
fi
echo REPLAY DONE
