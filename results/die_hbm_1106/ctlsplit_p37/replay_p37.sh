#!/bin/bash
# HBM-FORM-TIMING-11 d44v part 38 replay (was part 37 before BM3 took that number): split3__ctl -> ot_hgi_sfu_split3_ctl_rest_1c (same slot) + ot_hgi_sfu_split3_ctl_pipe_1c
# (new 172.8 x 151.2 slot W of it).  Run from the repo root.   replay_p37.sh RR   (RR = new work dir)
# Unpacks the checked-in d44v into RR/base, applies mk_p37.py on RR/new, then G0 + plan-time GEOM base vs new, render, views.
# PACK=1 also packages RR/new into the d44v dir (+ part38_event.json, SHA256SUMS).
set -e
RR=$1; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1106/ctlsplit_p37
rm -rf $RR; mkdir -p $RR/base/cores $RR/g0 $RR/geom
for f in $D/*.json $D/*.json.gz; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/$n;; *) cp $f $RR/base/$n;; esac; done
for f in $D/cores/*; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/cores/$n;; *) cp $f $RR/base/cores/$n;; esac; done
python3 -I results/die_hbm_1105/q3split_p34/fill_cores.py $RR/base ${CORES_FILL:-/srv/opentallas-scratch2/claude/kit-wave/hbm/d44v11/cores}
cp -r $RR/base $RR/new
python3 -I $F/mk_p37.py $RR/new
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do ( timeout 1800 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 1800 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -14 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -12 | tee $RR/geom.txt
python3 $F/render_p37.py $RR/new $RR/p37_q_b113.png
R=$PWD; (cd $RR; python3 $R/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $RR/new/die_plan.json --out $RR/views.json 2>&1 | tail -1 | cut -c1-100)
grep -oE '"(ot_hgi_sfu_split3_ctl_rest_1c|ot_hgi_sfu_split3_ctl_pipe_1c)@[0-9a-f]{12}"' $RR/views.json | sort -u
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
new = [n for n in cur if n not in names and ('ot_hgi_sfu_split3_ctl_' in n and 'd44v_split' in n or n == 'part38_event.json')]
L += [[cur[n], n] for n in sorted(new)]
(D / 'SHA256SUMS').write_text(''.join(f'{a}  {n}\n' for a, n in L)); print('SHA256SUMS changed', ch, 'added', new)
P
  (cd $D; for n in die_plan.json core_conns.json clock_entries.json; do a=$(zcat $n.gz | sha256sum | cut -c1-64); grep -q "^$a  $n$" SHA256SUMS && echo ok $n || echo BAD $n; done)
fi
echo REPLAY DONE
