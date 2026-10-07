#!/usr/bin/env python3
"""Inspect retained packet control/capture bits in an already-produced netlist."""
import argparse,hashlib,json,re
from pathlib import Path

def inspect(path):
    design=json.loads(path.read_text())
    mod=design['modules']['ot_hbm_collective_packet_fifo']
    qs={b for c in mod['cells'].values() if 'DFF' in c['type'].upper() for b in c['connections'].get('Q',[]) if isinstance(b,int)}
    result={}
    for key,pattern in {'control':r'g_on\.c$', 'seal':r'g_on\.seal$', 'capture':r'g_on\.captured$'}.items():
        ns={n:v['bits'] for n,v in mod['netnames'].items() if re.search(pattern,n)}
        bits={b for v in ns.values() for b in v if isinstance(b,int)}
        parity={v[word*72+bit] for v in ns.values() for word in range(len(v)//72) for bit in [0,1,3,7,15,31,63,71]} if key!='control' else set()
        result[key]={'nets':sorted(ns),'declared_bits':sum(map(len,ns.values())), 'dynamic_bits':len(bits),'sequential_bits':len(bits&qs),'parity_dynamic_bits':sum(isinstance(b,int) for b in parity),'parity_sequential_bits':len(parity&qs)}
    return {'netlist_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'retention':result,'scope':'Existing generic netlist postprocessing, no synthesis rerun. Literal constants separately excluded from dynamic and sequential counts.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);a=p.parse_args();print(json.dumps(inspect(a.netlist),indent=2))
