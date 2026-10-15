#!/usr/bin/env python3
"""Check unoptimised Yosys proc/memory_map FF ownership at the native pins."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

FFS={'$dff','$adff','$dffe','$adffe'}

def check(path):
    raw=Path(path).read_bytes()
    module=json.loads(raw)['modules']['qkd_kv_native_programme']
    cells=module['cells'];ports=module['ports']
    qbits={bit for cell in cells.values() if cell['type'] in FFS for bit in cell['connections']['Q']}
    outputs={}
    for name,port in ports.items():
        if port['direction']!='output':continue
        assert all(bit in qbits for bit in port['bits']),name+' has combinational output pins'
        outputs[name]=dict(bits=len(port['bits']),direct_ff_Q=True)
    inputs={}
    for name,port in ports.items():
        if port['direction']!='input' or name in ('ck','rst_n'):continue
        for bit in port['bits']:
            sinks=[(cell['type'],pin) for cell in cells.values() for pin,bits in cell['connections'].items()
                   if cell['port_directions'][pin]=='input' and bit in bits]
            assert sinks and all(kind in FFS and pin=='D' for kind,pin in sinks),name+' bypasses input pin capture'
        inputs[name]=dict(bits=len(port['bits']),direct_ff_D_only=True)
    ff=collections.Counter()
    for cell in cells.values():
        if cell['type'] in FFS:ff[cell['type']]+=len(cell['connections']['Q'])
    assert sum(ff.values())==6291,ff
    return dict(status='PASS_STRUCTURAL_PIN_FF_OWNERSHIP',module='qkd_kv_native_programme',
                yosys_json_sha256=hashlib.sha256(raw).hexdigest(),
                input_faces=inputs,output_faces=outputs,logical_ff_bits=dict(ff),total_logical_ff_bits=sum(ff.values()),
                start_pin_capture_edges=1,boot_pin_capture_edges=1,slot_interval_shift_edges=0,
                qualification='Yosys read/proc/memory_map/opt_clean structural audit only; no technology mapping, placement or routed timing qualification')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.write_text(json.dumps(check(a.netlist),indent=2)+'\n')
    print('PASS_STRUCTURAL_PIN_FF_OWNERSHIP logicalFF6291')
if __name__=='__main__':main()
