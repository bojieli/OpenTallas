#!/usr/bin/env python3
"""Source-pinned unused fault pins for a Qwen die's observability tree.

Counts actual instance pins/bits, including new landing shapes and connected but
unconsumed nets. This is a planning inventory, never a physical qualification.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/qwen_layerbench')]
import netlist_relay_stages as E


def collect(die,mods,declared):
    nets,tin,tout,insts=E.P.parse_die(die)
    if any(mst=='__assign__' for mst,_,_,_ in insts):
        raise ValueError('fault inventory: top-level aliases require explicit resolution')
    loads=set()
    for mst,name,params,cm in insts:
        if mst not in mods:continue
        for p,expr in cm.items():
            if mods[mst].ports.get(p,(None,))[0]=='input':
                loads.update(E.P.expr_bits(expr,nets) or [])
    for n in tout:
        w,lo=nets[n];loads.update((n,bit) for bit in range(lo,lo+w))
    rows=[]
    for mst,name,params,cm in insts:
        if mst not in mods:continue
        mod=mods[mst];env=mod.env(params)
        for p,(direction,_) in mod.ports.items():
            if direction!='output':continue
            if (mst,p) in declared:cl='DECLARED_FAULT_OBS'
            elif mst.startswith('qfd_land') and p=='fault':cl='LANDING_FAULT_REAL_RTL'
            elif re.search('fault|abort|error',p):cl='REVIEW_UNCLASSIFIED'
            else:continue
            width=mod.width(p,env)
            bits=E.P.expr_bits(cm.get(p,''),nets) if cm.get(p) else None
            if bits is not None and len(bits)!=width:
                raise ValueError(f'{name}.{p}: fault port width mismatch')
            missing=[bit for bit in range(width) if bits is None or bits[-1-bit] not in loads]
            if not missing:continue
            ck=next((cm[q] for q in ['ck','clk','ckf'] if cm.get(q)),None)
            rs=next((cm[q] for q in ['rs','rst_n','rst','reset_n','rsi'] if cm.get(q)),None)
            rows.append(dict(instance=name,master=mst,port=p,port_width=width,unused_bits=missing,
                             bits=len(missing),classification=cl,clock=ck,reset=rs,
                             connection=cm.get(p),needs_source_native_capture=True))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['die-v','port-bind','classification','out']:p.add_argument('--'+arg,required=True,type=Path)
    p.add_argument('--commit',required=True);p.add_argument('--src-prefix',action='append',default=[])
    p.add_argument('--local-rtl',action='append',default=[])
    a=p.parse_args();pb=json.loads(a.port_bind.read_text());cl=json.loads(a.classification.read_text())
    declared={(x['master'],x['port']) for x in cl['owed'] if x['cls']=='FAULT_OBS'}
    mods,srcs=E.load_ports(pb,a.commit,a.src_prefix,a.local_rtl)
    rows=collect(a.die_v,mods,declared)
    out=dict(schema='opentallas.qw_fault_tree_inventory.v2',source_commit=a.commit,
             sources={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.die_v,a.port_bind,a.classification]},
             classified_historical_master_ports=len(declared),actual_unused_master_ports=len({(r['master'],r['port']) for r in rows}),
             actual_unused_instance_ports=len(rows),actual_unused_bits=sum(r['bits'] for r in rows),
             clock_groups=len({r['clock'] for r in rows}),unresolved_source_clock=sum(r['clock'] is None for r in rows),
             unresolved_source_reset=sum(r['reset'] is None for r in rows),
             unclassified_instance_ports=sum(r['classification']=='REVIEW_UNCLASSIFIED' for r in rows),
             physical_qualification_eligible=False,scope='Actual unused fault pins/bit inventory only; source capture, landed root crossings, bounded RTL, geometry and physical closure still owed.',rows=rows)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['rows','sources','scope']}))


if __name__=='__main__':main()
