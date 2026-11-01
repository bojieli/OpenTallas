#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
DK=docker; $DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus=1 --memory=1g --memory-swap=1g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -V > tool.txt; for m in qfd_dv_s8x_vmr qfd_dv_s8_crh_rp1; do cd /work/$m; yosys -ql lib_only.log lib_only.ys; rc=$?; test $rc != 0 || exit 1; grep -q "does not have a parameter named" lib_only.log || exit 1; yosys -ql eager_bb.log eager_bb.ys || exit $?; done; chown -R '"$(id -u):$(id -g)"' /work'
python3 - <<'PY'
import json
man=json.load(open('manifest.json'))
for n,r in man.items():
 j=json.load(open(n+'/eager_bb.json'));m=j['modules'][n];c=j['modules']['top']['cells']['u_child']
 assert int(m['attributes']['blackbox'],2)==1 and not m.get('cells')
 assert c['type']==n and int(c['parameters']['MIF'],2)==0
 assert sum(len(p['bits'])for p in m['ports'].values())==r['signed_functional_bits']
 assert all(int(v,2)==0 for v in m['parameter_default_values'].values())
 print(n,'PARAMETER_HEADER PASS MIF0 defaultparams',m['parameter_default_values'],'pins',r['signed_functional_bits'])
print('Mechanism/ABI only; physical FT wiring and independent signed-child source proof remain required.')
PY
