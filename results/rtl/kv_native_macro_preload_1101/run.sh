#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
DK=docker
$DK ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --cpus=1 --memory=1g --memory-swap=1g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -V > tool.txt; yosys -ql preloaded.log preloaded.ys; rc=$?; test $rc = 0 || exit $rc; for c in native_only wrong_master; do yosys -ql $c.log $c.ys; rc=$?; echo "$c RC=$rc"; test $rc != 0 || exit 1; done; chown -R '"$(id -u):$(id -g)"' /work'
python3 - <<'CHECK'
import json
j=json.load(open('preloaded.json')); m=j['modules']['qkd_astk_ex_s']
assert int(m['attributes']['blackbox'],2)==1 and not m.get('cells')
assert [(n,p['direction'],len(p['bits'])) for n,p in m['ports'].items()]==[('ck','input',1),('rst_n','input',1),('xa','input',66),('xe','output',34)]
assert len(j['modules']['top']['cells'])==1
assert next(iter(j['modules']['top']['cells'].values()))['type']=='qkd_astk_ex_s'
for c in ['native_only','wrong_master']:
 assert 'is not part of the design' in open(c+'.log').read()
print('LIBERTY_PRELOAD_NATIVE_EX_MECHANISM PASS:102 pins,1 hard cell,0 native logic; absent/wrong Liberty controls descend native body')
print('Synthetic Liberty is a frontend fixture only; not a signed child or equivalence proof.')
CHECK
