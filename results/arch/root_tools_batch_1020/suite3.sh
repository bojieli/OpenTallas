#!/bin/bash
set -u
R=$(pwd)
mkdir -p pylib base3 cand3
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base3.tar -C base3
tar xf base3.tar -C cand3
(cd cand3 && git apply --binary ../cand3.patch) || exit 3
for side in base3 cand3; do
 (cd "$side" && git init -q && git unpack-objects < ../baseline_objects.pack >/dev/null)
done
export PYTHONPATH="$R/pylib"
for side in base3 cand3; do
 for cohort in closure_loop ref_tile fleet landed_parent; do
  (cd "$side/tools/$cohort" && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors --deselect test_ot_run_load_hold.py::Rebalance::test_single_host_waits_unbounded_and_max_wait_is_kept . > "$R/${side}_${cohort}.log" 2>&1; echo $? > "$R/${side}_${cohort}.rc") &
 done
done
wait
python3 - <<'ENDPY'
from pathlib import Path
import re
for cohort in ('closure_loop','ref_tile','fleet','landed_parent'):
 ids={}
 for side in ('base3','cand3'):
  p=Path(f'{side}_{cohort}.log');text=p.read_text()
  ids[side]={re.sub(r' - .*','',ln) for ln in text.splitlines() if ln.startswith(('FAILED ','ERROR '))}
  Path(f'{side}_{cohort}.fail').write_text('\n'.join(sorted(ids[side]))+'\n')
  print(side,cohort,'rc='+Path(f'{side}_{cohort}.rc').read_text().strip(),text.splitlines()[-1])
 print('NEW',cohort,sorted(ids['cand3']-ids['base3']))
 print('FIXED',cohort,sorted(ids['base3']-ids['cand3']))
ENDPY
