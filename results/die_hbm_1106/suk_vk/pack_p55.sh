#!/bin/bash
# HBM-CONS-2/SUK: package RR/new into d44v after replay_p55.sh (run from the repo root).   pack_p55.sh RR
set -e
RR=$1; D=physical/die_plan/hbm/plan_of_record/d44v
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
new = [n for n in cur if n not in names and (n.endswith('__d44v_p55.json') or n == 'part55_event.json')]
L += [[cur[n], n] for n in sorted(new)]
(D / 'SHA256SUMS').write_text(''.join(f'{a}  {n}\n' for a, n in L)); print('SHA256SUMS changed', ch, 'added', new)
P
(cd $D; for n in die_plan.json core_conns.json clock_entries.json; do a=$(zcat $n.gz | sha256sum | cut -c1-64); grep -q "^$a  $n$" SHA256SUMS && echo ok $n || echo BAD $n; done)
