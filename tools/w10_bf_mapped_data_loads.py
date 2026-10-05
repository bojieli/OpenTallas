#!/usr/bin/env python3
"""Actual mapped BF source fanout reachability, retaining ungated-front data cost."""
import argparse
import collections
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re

def build(raw,coeff):
    sha=hashlib.sha256(raw).hexdigest()
    if sha!='d6b8f7848db0fdfb1f1142deaa298154c4a6366447ee5d1906df8055ed4ba2ea':raise ValueError('wrong actual BF source')
    text=raw.decode(); roots=set();cells=[];consumer=collections.defaultdict(list);fixed=[]
    for width,name in re.findall(r'^\s*input\s+(\[[^]]+\]\s*)?(\\?\S+)\s*;',text,re.M):
        name=name.strip()
        if name in ('clk','rst_n'):continue
        if width:
            a,b=map(int,re.findall(r'\d+',width));roots.update(f'{name}[{i}]' for i in range(min(a,b),max(a,b)+1))
        else:roots.add(name)
    for m in re.finditer(r'^\s+(\w+_ASAP7_75t_\w+|ot_rom_4096x274_m8)\s+(\\?\S+)\s+\((.*?)\n\s*\);',text,re.M|re.S):
        t,name,body=m.groups();ports={p:v.strip() for p,v in re.findall(r'\.(\w+)\(([^)]+)\)',body)}
        if t in ('wire','input','output','reg','module'):continue
        if t=='ot_rom_4096x274_m8':continue
        if t not in coeff['coefficients']:raise ValueError('unpriced '+t)
        if t.startswith('DFF'):
            role='root' if ports['CLK']=='clk' else 'leaf'
            if role=='root':roots.add(ports.get('QN',ports.get('Q')))
            fixed.append((t,role,ports['D']));continue
        if t.startswith('ICG'):
            fixed.append((t,'root',None));continue
        output=ports.get('Y',ports.get('Z',ports.get('H',ports.get('L'))))
        if output is None:raise ValueError('unknown output '+t)
        ins=[v for p,v in ports.items() if p not in ('Y','Z','H','L','VDD','VSS')]
        idx=len(cells);cells.append((t,output))
        for net in ins:consumer[net].append(idx)
    queue=collections.deque(roots);seen=set()
    while queue:
        n=queue.popleft()
        for i in consumer.get(n,[]):
            if i in seen:continue
            seen.add(i);out=cells[i][1]
            if out not in roots:roots.add(out);queue.append(out)
    hist={'root':collections.Counter(),'leaf':collections.Counter()}
    for i,(t,out) in enumerate(cells):hist['root' if i in seen else 'leaf'][t]+=1
    wire_hist={'root':hist['root'].copy(),'leaf':hist['leaf'].copy()}
    sensitive_leaf_D=0
    for t,role,data in fixed:
        wire_hist[role][t]+=1
        data_role='root' if role=='leaf' and data in roots else role
        if role=='leaf' and data_role=='root':sensitive_leaf_D+=1
        hist[data_role][t]+=1
    if sum(sum(h.values()) for h in hist.values())!=527187:raise ValueError('mapped cell census mismatch')
    terms={};v=D('.77');hz=D('1.2e9');cv=hz*v*v*D('1e-15')
    for role,counts in hist.items():
        energy=sum(n*D(coeff['coefficients'][t]['data_cycle_energy_fJ']) for t,n in counts.items())
        pins=sum(n*D(coeff['coefficients'][t]['nonclock_pin_cap_fF']) for t,n in counts.items())
        output=sum(n*D(coeff['coefficients'][t]['output_load_ceiling_fF']) for t,n in wire_hist[role].items())
        terms[role]={'cell_histogram':dict(sorted(counts.items())),
          'output_wire_histogram':dict(sorted(wire_hist[role].items())),
          'internal_data_upper_W':str(energy*hz*D('1e-15')),'input_pin_upper_W':str(pins*cv),
          'unresolved_output_wire_upper_W':str(output*cv),
          'conditional_total_data_upper_W':str(energy*hz*D('1e-15')+(pins+output)*cv)}
    return {'schema':'w10_bf_actual_mapped_data_cones_v1','source_sha256':sha,'terms':terms,'root_sensitive_leaf_D_bits':sensitive_leaf_D,
      'source_scope':'Actual raw fullmap, includes dead cells; root-reachable data cones conservatively include all CFG/STREAM inputs and ungated front. Pure leaf cones have no root data driver.',
      'rule':'Charge root data upper during incoming CFG/STREAM; charge leaf data upper only in existing wake union. Data-wire ceiling is unresolved, not measured RC.',
      'reset_scope':'Warm reset-deasserted only; startup reset energy separately overbounded',
      'physical_admission':False,'actual_power_qualified':False,'root_stop_credit':0}
def main():
    p=argparse.ArgumentParser()
    for n in ('netlist','coefficients','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();raw=Path(a.netlist).read_bytes();x=build(raw,json.loads(Path(a.coefficients).read_text()));x['coefficients_sha256']=hashlib.sha256(Path(a.coefficients).read_bytes()).hexdigest();Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
