#!/usr/bin/env python3
"""Check unoptimised Yosys proc/memory_map FF ownership at the native pins."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

FFS={'$dff','$adff','$dffe','$adffe'}
ASYNC_FFS={'$adff','$adffe'}
# Logical FF bits per accepted reset form (exact, never a range).
#  async: f74794fa4 -- rst_n is the ARST of one 1-bit $adff (the pin reset flop).
#  sync:  b985e4faf (Q-COMPUTE-ELEM p2) -- rst_n is the D of one kept 1-bit $dff (reset_pin_n); that flop's Q
#         is the ARST of every internal $adff and drives nothing else, so assertion is one edge after rst_n falls
#         and release stays one edge.
LOGICAL_FF_BITS={'async':6292,'sync':6629}

def _input_sinks(cells,bits):
    return [(name,cell['type'],pin,len(cell['connections']['Q']) if 'Q' in cell['connections'] else 0)
            for name,cell in cells.items() for pin,pbits in cell['connections'].items()
            if cell['port_directions'][pin]=='input' and any(bit in pbits for bit in bits)]

def reset_form(cells,reset_bits):
    sinks=_input_sinks(cells,reset_bits)
    assert len(sinks)==1 and sinks[0][3]==1,sinks
    name,kind,pin,_=sinks[0]
    if kind=='$adff' and pin=='ARST':return 'async',sinks[0],0
    assert kind=='$dff' and pin=='D',sinks
    q=cells[name]['connections']['Q']
    fan=_input_sinks(cells,q)
    assert fan and all(kind in ASYNC_FFS and pin=='ARST' for _,kind,pin,_ in fan),('reset pin FF Q must drive only internal ARST pins',fan)
    arst=[(n,c['connections']['ARST']) for n,c in cells.items() if c['type'] in ASYNC_FFS]
    assert all(bits==q for _,bits in arst),('every internal ARST must be the reset pin FF Q',[n for n,b in arst if b!=q])
    return 'sync',sinks[0],len(fan)

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
    assert len(ports['rst_n']['bits'])==1
    form,reset_sink,internal_arst=reset_form(cells,ports['rst_n']['bits'])
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
    assert sum(ff.values())==LOGICAL_FF_BITS[form],(form,ff)
    return dict(status='PASS_STRUCTURAL_PIN_FF_OWNERSHIP',module='qkd_kv_native_programme',
                yosys_json_sha256=hashlib.sha256(raw).hexdigest(),
                input_faces=inputs,output_faces=outputs,external_reset_form=form,external_reset_sink_count=1,external_reset_sink=reset_sink,
                internal_arst_sinks_of_reset_pin_ff=internal_arst,reset_pin_assert_edges=1 if form=='sync' else 0,reset_pin_release_edges=1,
                logical_ff_bits=dict(ff),total_logical_ff_bits=sum(ff.values()),
                start_pin_capture_edges=1,boot_pin_capture_edges=1,slot_interval_shift_edges=0,
                qualification='Yosys read/proc/memory_map/opt_clean structural audit only; no technology mapping, placement or routed timing qualification')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=check(a.netlist)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(f"PASS_STRUCTURAL_PIN_FF_OWNERSHIP reset={r['external_reset_form']} logicalFF{r['total_logical_ff_bits']}")
if __name__=='__main__':main()
