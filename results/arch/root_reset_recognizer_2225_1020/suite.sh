#!/bin/bash
set -u
R=$(pwd)
mkdir -p pylib base cand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C base
tar xf fixtures.tar -C base
tar xf base.tar -C cand
tar xf fixtures.tar -C cand
(cd cand && git apply --binary ../cand.patch) || exit 3
export PYTHONPATH="$R/pylib"
for side in base cand; do
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
 for side in ('base','cand'):
  p=Path(f'{side}_{cohort}.log');text=p.read_text()
  ids[side]={re.sub(r' - .*','',ln) for ln in text.splitlines() if ln.startswith(('FAILED ','ERROR '))}
  Path(f'{side}_{cohort}.fail').write_text('\n'.join(sorted(ids[side]))+'\n')
  print(side,cohort,'rc='+Path(f'{side}_{cohort}.rc').read_text().strip(),text.splitlines()[-1])
 print('NEW',cohort,sorted(ids['cand']-ids['base']))
 print('FIXED',cohort,sorted(ids['base']-ids['cand']))
ENDPY

for side in base cand; do
 (cd "$side" && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" tools/test_textbook*.py > "$R/${side}_textbook.log" 2>&1; echo $? > "$R/${side}_textbook.rc") &
done
wait
(cd cand && python3 results/arch/qdq_async_reset_relay_1020/check_actual.py > "$R/actual_replay.log" 2>&1); echo $? > "$R/actual_replay.rc"
tail -5 base_textbook.log
tail -5 cand_textbook.log
cat actual_replay.rc
tar czf result_logs.tar.gz *.log *.rc *.fail
base64 -w0 result_logs.tar.gz > result_logs.b64
echo RESULT_BEGIN
cat result_logs.b64
echo
echo RESULT_END
