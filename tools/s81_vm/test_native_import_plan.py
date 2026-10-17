#!/usr/bin/env python3
"""Counterexamples against the real frozen import inputs, run after extraction."""
import json
from pathlib import Path
import sys
import tempfile
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
rejects(lambda:P.verify_flat_sources({'files':[{'path':'a/shared.sv','sha256':'x'},
                                               {'path':'b/shared.sv','sha256':'x'}]},inputs))
directory=inputs/'closed_lefs/dsfd_vm_wfc_return256_native_1016_r2'
clocks,_=P.clock_contract(directory,physical)
assert clocks=={'ck'}
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    lib=next(directory.glob('*_tt.lib')).read_text().replace('"ck"','"clk"')
    ins=(directory/'insertion.json').read_text().replace('"ck"','"clk"')
    (tmp/'renamed_tt.lib').write_text(lib)
    (tmp/'insertion.json').write_text(ins)
    renamed={**physical,'pins':{('clk' if k=='ck' else k):v for k,v in physical['pins'].items()}}
    assert P.clock_contract(tmp,renamed)[0]=={'clk'}
    # A real extra Liberty clock with no physical port must refuse, not vanish.
    (tmp/'renamed_tt.lib').write_text(lib.replace('pin("clk") {','pin("not_in_abi") {'))
    rejects(lambda:P.clock_contract(tmp,renamed))
    (tmp/'renamed_tt.lib').write_text(lib)
    (tmp/'insertion.json').write_text(ins.replace('"clk"','"ck"'))
    rejects(lambda:P.clock_contract(tmp,renamed))
print('VM_IMPORT_CLOCK_PROOF PASS: renamed clk discovered, absent clock/mismatched measured keys/duplicate source basenames rejected')
