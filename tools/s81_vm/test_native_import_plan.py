#!/usr/bin/env python3
"""Counterexamples against the real frozen import inputs, run after extraction."""
import json
from pathlib import Path
import sys
import native_import_plan as P


inputs=Path(sys.argv[1])
leaves=json.loads((inputs/'inventory.json').read_text())['leaves']
old={r['path']:r for r in json.loads((inputs/'old_leaves.json').read_text())['leaves']}
by={r['path']:r for r in leaves}
def rejects(f):
    try:
        f()
    except ValueError:
        return
    raise AssertionError('invalid actual binding survived')

leaf=by['dut.u_wfc.split_return.u_ret.lo']
assert P.select_binding(leaf,old)=='dsfd_vm_wfc_return256_native_1016_r2'
rejects(lambda:P.select_binding({**leaf,'parameters':{'RESPONSE_PAD':3}},old))
seq=by['dut.u_core.u_seq']
rejects(lambda:P.select_binding({**seq,'parameters':{}},old))
physical=P.model(inputs/'closed_lefs/dsfd_vm_wfc_return256_native_1016_r2/dsfd_vm_wfc_return256.lef')
P.require_pins(leaf,physical)
lost=dict(physical)
lost['pins']=dict(physical['pins'])
del lost['pins']['s_d[255]']
rejects(lambda:P.require_pins(leaf,lost))
print('VM_IMPORT_COUNTEREXAMPLES PASS: wrong calendar parameter, stale seq parameter, dropped actual terminal all rejected')
