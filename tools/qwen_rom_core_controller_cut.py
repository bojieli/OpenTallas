#!/usr/bin/env python3
"""Remove passive interface ports from an exposed controller; keep cell graph exact."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def cut(design, top, drop_feedthrough=False):
    result=copy.deepcopy(design)
    module=result['modules'][top]
    before=design['modules'][top]
    connected={bit for cell in module['cells'].values()
               for connection in cell['connections'].values()
               for bit in connection if isinstance(bit,int)}
    removed={name:port for name,port in module['ports'].items()
             if not any(bit in connected for bit in port['bits'])}
    if drop_feedthrough:
        # DEC_LA_PINREG cut: an output that is only a wire from input pins (or a constant) is not the block's logic
        # (the die routes it past the block: unit -> memory port), so it leaves the block with the inputs it carries
        inbits={b for p in module['ports'].values() if p['direction']=='input' for b in p['bits'] if isinstance(b,int)}
        for n,p in module['ports'].items():
            if n not in removed and p['direction']=='output' and all((not isinstance(b,int)) or b in inbits for b in p['bits']):
                removed[n]=p
        outbits={b for n,p in module['ports'].items() if n not in removed and p['direction']=='output'
                 for b in p['bits'] if isinstance(b,int)}
        for n,p in module['ports'].items():
            if n not in removed and p['direction']=='input' and \
               not any(isinstance(b,int) and (b in connected or b in outbits) for b in p['bits']):
                removed[n]=p
    for name in removed:
        del module['ports'][name]
    assert module['cells']==before['cells'], 'cell graph changed'
    assert module['netnames']==before['netnames'], 'net identities changed'
    def counts(ports):
        return {direction:sum(len(p['bits']) for p in ports.values()
                             if p['direction']==direction)
                for direction in ('input','output','inout')}
    report={'schema':'qwen.rom.controller_cut_result.v1',
            'before_port_bits':counts(before['ports']),
            'after_port_bits':counts(module['ports']),
            'retained_cells':len(module['cells']),
            'cell_graph_identical':True,'netnames_identical':True,
            'removed':{n:{'direction':p['direction'],'bits':len(p['bits'])}
                       for n,p in removed.items()},
            'clock_qualified':False,'real_parent_loads_qualified':False}
    return result,report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--top',default='ot_qwen_rom_core');p.add_argument('--drop-feedthrough',action='store_true');a=p.parse_args()
    raw=a.input.read_bytes();design=json.loads(raw)
    result,report=cut(design,a.top,a.drop_feedthrough)
    report['input_sha256']=hashlib.sha256(raw).hexdigest()
    a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    report['output_sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest()
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
