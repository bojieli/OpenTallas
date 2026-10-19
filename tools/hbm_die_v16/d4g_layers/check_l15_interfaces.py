#!/usr/bin/env python3
"""Source-bound CP/SVG/XC interface bind unit, not a release die or router fixture.

All non-internal ports are explicit unit inputs/outputs. Internal connections come
from the migrated contract, including every bit of the two tgt_active contributors.
The report qualifies interfaces only, not clock timing or unresolved router production.
"""
import argparse
import json
from pathlib import Path
import sys
import l15_smb_relative as L


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('contract'); ap.add_argument('--out', required=True)
    a = ap.parse_args(); c = L.load(a.contract)
    names = ['cp_svg_SW0','svg_SW0','xc_SW0']; I = c['instances']; nameset=set(names)
    internal = [e for e in c['edges'] if e['source'][0] in nameset and e['sink'][0] in nameset]
    source = {}
    for e in internal:
        s,t=e['source'],e['sink']
        for k in range(e['bits']):
            ep=(t[0],t[1],t[2]+k)
            if ep in source: raise ValueError(f'multiple contract drivers {ep}')
            source[ep]=f'w__{s[0]}__{s[1]}[{s[2]+k}]'
    ports=[]; wires=[]; inst=[]
    for n in names:
        v=I[n]; conn=[]
        for p,d in v['ports'].items():
            w=d['bits']; wn=f'w__{n}__{p}'
            if d['direction']=='output':
                ports.append(f'output wire [{w-1}:0] {wn}'); expr=wn
            else:
                missing=[k for k in range(w) if (n,p,k) not in source]
                ext={}
                if missing:
                    pn=f'i__{n}__{p}';ports.append(f'input wire [{len(missing)-1}:0] {pn}')
                    ext={k:f'{pn}[{i}]' for i,k in enumerate(missing)}
                bits=[source.get((n,p,k),ext.get(k)) for k in reversed(range(w))]
                expr='{'+','.join(bits)+'}'
            conn.append(f'.{p}({expr})')
        params=','.join(f'.{p}({value})' for p,value in v['params'].items())
        inst.append(f'{v["master"]} #({params}) {n} ('+',\n'.join(conn)+');')
    Path(a.out).write_text('// Interface-only unit; external ports are unit stimulus/observations, not production die IO.\n'
        +'module l15_interface_unit ('+','.join(p.split()[-1] for p in ports)+');\n'+';\n'.join(ports)+';\n'+'\n'.join(wires+inst)+'\nendmodule\n')
    print('L15_INTERFACE_UNIT',len(names),'real masters',len(internal),'contract internal links; unresolved router remains external UNIT input only')


if __name__=='__main__': main()
