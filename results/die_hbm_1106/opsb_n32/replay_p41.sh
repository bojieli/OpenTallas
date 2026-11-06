#!/bin/bash
# HBM-FORM-SPLIT-13-OPSB d44v part 41 replay: ot_hgi_sfu_opsb_output core_macros -> 16 x ot_sram_1r1w_2048x32_m8_r0c0_g32 (4 x 4).
# Run from the repo root.   replay_p41.sh RR BASE_PLAN_DIR   (BASE = unpacked d44v incl. filled cores/; RR = new work dir)
# G0 (check.py with core_conns + core_macros) and plan-time GEOM base vs new, render, views.  PACK=1 copies core_macros.json +
# part41_event.json into the d44v dir and refreshes SHA256SUMS.
set -e
RR=$1; B=$2; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1106/opsb_n32
rm -rf $RR; mkdir -p $RR/g0 $RR/geom; cp -r $B $RR/base; cp -r $B $RR/new
python3 -I $F/mk_p41.py $RR/new
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do ( timeout 2400 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 2400 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -14 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -12 | tee $RR/geom.txt
python3 $F/render_p41.py $RR/new $RR/p41_opsb_output.png
R=$PWD; (cd $RR; python3 $R/physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $RR/new/die_plan.json --out $RR/views.json 2>&1 | tail -1 | cut -c1-100)
grep -oE '"ot_hgi_sfu_opsb_output@[0-9a-f]{12}"' $RR/views.json | sort -u
if [ "${PACK:-0}" = 1 ]; then
  cp $RR/new/core_macros.json $D/core_macros.json; cp $RR/new/part41_event.json $D/part41_event.json
  python3 -I - $D <<'P'
import hashlib, sys
from pathlib import Path
D = Path(sys.argv[1]); L = [l.split(None, 1) for l in (D / 'SHA256SUMS').read_text().splitlines() if l.strip()]
cur = {n: hashlib.sha256((D / n).read_bytes()).hexdigest() for n in ('core_macros.json', 'part41_event.json')}
ch = 0
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a: L[i] = [cur[n], n]; ch += 1
add = [n for n in cur if n not in [n_ for _, n_ in L]]; L += [[cur[n], n] for n in add]
(D / 'SHA256SUMS').write_text(''.join(f'{a}  {n}\n' for a, n in L)); print('SHA256SUMS changed', ch, 'added', add)
P
fi
echo REPLAY DONE
