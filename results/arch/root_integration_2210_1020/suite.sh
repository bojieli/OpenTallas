#!/bin/bash
set -u
R=$(pwd)
mkdir -p pylib fixturebase fixturecand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C fixturebase
tar xf fixtures.tar -C fixturebase
tar xf base.tar -C fixturecand
tar xf fixtures.tar -C fixturecand
(cd fixturecand && git apply --binary ../final.patch) || exit 3
export PYTHONPATH="$R/pylib"
for side in fixturebase fixturecand; do
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
 for side in ('fixturebase','fixturecand'):
  p=Path(f'{side}_{cohort}.log');text=p.read_text()
  ids[side]={re.sub(r' - .*','',ln) for ln in text.splitlines() if ln.startswith(('FAILED ','ERROR '))}
  Path(f'{side}_{cohort}.fail').write_text('\n'.join(sorted(ids[side]))+'\n')
  print(side,cohort,'rc='+Path(f'{side}_{cohort}.rc').read_text().strip(),text.splitlines()[-1])
 print('NEW',cohort,sorted(ids['fixturecand']-ids['fixturebase']))
 print('FIXED',cohort,sorted(ids['fixturebase']-ids['fixturecand']))
ENDPY

(cd fixturecand && python3 -m pytest -q -o addopts="" tools/die_safety/test_hbm_ir_required.py tools/ref_tile/tests/test_clock_rule_waiver.py tools/ref_tile/tests/test_mc3c7_native_scope.py tools/ref_tile/tests/test_landed_root_spread.py tools/ref_tile/tests/test_child_pair_spread.py tools/closure_loop/test_gate_rule_guard.py tools/closure_loop/test_helper_overlay.py > "$R/focused.log" 2>&1); echo $? > "$R/focused.rc"
tail -5 "$R/focused.log"
tar czf fixture_logs.tar.gz *.log *.rc *.fail
base64 -w0 fixture_logs.tar.gz > fixture_logs.b64
echo RESULT_BEGIN
cat fixture_logs.b64
echo
echo RESULT_END
