#!/usr/bin/env python3
"""Repair only illegal empty vector connections at the copied-source rendering boundary."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def normalize(stage):
    p=stage/'selected_preprocessed.sv'; original=p.read_text()
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:' '*len(m[0]),original,flags=re.S)
    modules={m[1]:m for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',clean,re.S)}
    repairs=[]; changes=[]
    for parent, module in modules.items():
        for line in re.finditer(r'[^\n]*\n?',module[0]):
            text=line[0]
            ports=list(re.finditer(r'\.(\w+)\(\{\}\)',text))
            if not ports:continue
            inst=re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s*)?(\w+)\s*\(',text)
            if not inst:raise ValueError('Cannot resolve empty connection instance in '+parent)
            master,name=inst.groups(); definition=modules[master][0]
            header=definition[:definition.index(';')+1]
            directions={}
            for d in re.finditer(r'\b(input|output|inout)\b(.*?)(?=\binput\b|\boutput\b|\binout\b|$)',header,re.S):
                for port in ports:
                    if re.search(r'\b'+port[1]+r'\b',d[2]):directions[port[1]]=d[1]
            for port in ports:
                direction=directions.get(port[1]);proof='Open output; no receiving net exists'
                if direction!='output':
                    if (master,port[1],direction)!=('ot_su12_sfu_sp2','side_y','input'):
                        raise ValueError('Unproven empty input/inout: '+master+'.'+port[1])
                    body=definition[definition.index(';')+1:]
                    # A named child port label is not a reference to the wrapper input.
                    body=re.sub(r'\.side_y\s*\(','.child_side_y(',body)
                    if re.search(r'\bside_y\b',body):raise ValueError('side_y is used; cannot open')
                    proof='Selected wrapper side_y input has no references; internal child side_y is explicitly32d0'
                begin=module.start()+line.start()+port.start();end=module.start()+line.start()+port.end()
                replacement='.'+port[1]+'()';changes.append((begin,end,replacement))
                repairs.append(dict(parent=parent,master=master,instance=name,port=port[1],direction=direction,
                                    before=port[0],after=replacement,proof=proof))
    if not repairs:raise ValueError('No empty connections found; require a fresh unnormalized source stage')
    result=original
    for begin,end,replacement in sorted(changes,reverse=True):result=result[:begin]+replacement+result[end:]
    assert not re.search(r'\.\w+\(\{\}\)',result)
    receipt=dict(status='SYNTAX_ONLY_OPEN_CONNECTION_RENDERING',connections=len(repairs),
        source_sha256=hashlib.sha256(original.encode()).hexdigest(),rendered_sha256=hashlib.sha256(result.encode()).hexdigest(),
        production_source_changes=0,new_nets=0,new_drivers=0,assertion_guards_changed=0,repairs=repairs)
    p.write_text(result);(stage/'sim.f').write_text(str(p.resolve())+'\n')
    meta=stage/'module_closure.json';j=json.loads(meta.read_text())
    j['pre_normalization_preprocessed_module_bodies']=j.pop('unchanged_preprocessed_module_bodies')
    j['rendering_boundary_normalization']=receipt
    meta.write_text(json.dumps(j,indent=1)+'\n')
    (stage/'open_connection_repairs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='repairs'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',type=Path,required=True)
    normalize(p.parse_args().stage)
