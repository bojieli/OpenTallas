#!/usr/bin/env python3
"""Parameter-exact, name-only aliases for the colliding VM CDC view cells.

Uses the shared rename_view helper; verifies every LEF/Liberty byte by applying
the inverse rename and requires insertion clock records to remain identical.
The aliases do not add registers, area, clock entries, or calendar edges.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_params(leaf, spec):
    if spec['top']!=leaf['master']:
        raise ValueError('alias kit source master differs')
    declared=spec.get('params',{})
    if any(leaf['parameters'].get(k)!=v for k,v in declared.items()):
        raise ValueError('alias kit elaborated parameter mismatch: '+leaf['path'])
    # Each width must be explicitly selected by the source physical kit.
    if 'W' in leaf['parameters'] and declared.get('W')!=leaf['parameters']['W']:
        raise ValueError('alias width not explicitly bound by actual kit')


def build(plan, inputs, out, rename_helper):
    bykit={}
    for leaf in plan['leaves']:
        prior=bykit.get(leaf['kit'])
        if prior and (prior['master'],prior['parameters'],prior['ports'])!=(leaf['master'],leaf['parameters'],leaf['ports']):
            raise ValueError('one kit aliases incompatible source instances')
        bykit[leaf['kit']]=leaf
    bycell=collections.defaultdict(list)
    for kit,leaf in bykit.items():bycell[leaf['physical_cell']].append(kit)
    records={}
    for cell,kits in bycell.items():
        if len(kits)<2:continue
        for kit in kits:
            leaf=bykit[kit]
            source=inputs/kit/'views'/cell
            spec=json.loads((inputs/kit/'spec.json').read_text())
            exact_params(leaf,spec)
            alias=cell+'__vm_'+hashlib.sha256(kit.encode()).hexdigest()[:12]
            required=[cell+'.lef']+[cell+'_'+c+'.lib' for c in ('ss','ff','tt')]+['insertion.json']
            if any(not(source/n).is_file() for n in required):raise ValueError('incomplete actual alias source '+kit)
            subprocess.run([sys.executable,str(rename_helper),str(source),alias],check=True,capture_output=True)
            target=source.parent/alias
            proof={}
            for name in required:
                renamed=name.replace(cell,alias)
                old=(source/name).read_text();new=(target/renamed).read_text()
                if name.endswith('.lef'):
                    restored=re.sub(r'^(MACRO|\s*FOREIGN|END) '+re.escape(alias)+r'\b',lambda m:m[1]+' '+cell,new,flags=re.M)
                    if restored!=old:raise ValueError('alias altered actual LEF geometry/pins')
                elif name.endswith('.lib'):
                    restored=new.replace('library ('+alias+'_','library ('+cell+'_').replace('cell ("'+alias+'")','cell ("'+cell+'")')
                    if restored!=old:raise ValueError('alias altered Liberty timing/clock annotations')
                elif json.loads(new)!=json.loads(old):
                    raise ValueError('alias altered literal insertion clock keys/values')
                proof[name]={'source_sha256':sha(source/name),'alias_sha256':sha(target/renamed)}
            records[kit]=dict(source_master=leaf['master'],parameters=leaf['parameters'],
                              physical_cell=cell,alias=alias,outline_um=leaf['outline_um'],
                              source_spec_sha256=sha(inputs/kit/'spec.json'),files=proof,
                              scope='NAME_ONLY_FROM_THIS_ACTUAL_KIT; native/source qualification inherited only from its own receipts')
            out.mkdir(parents=True,exist_ok=True)
            # Fixed-parameter simulation/synthesis wrapper; no storage or logic.
            declarations=[];connections=[]
            for port,v in leaf['ports'].items():
                declarations.append(v['direction']+' wire '+('['+str(v['bits']-1)+':0] ' if v['bits']>1 else '')+port)
                connections.append('.'+port+'('+port+')')
            params=', '.join('.'+p+'('+str(v)+')' for p,v in sorted(leaf['parameters'].items()))
            text='module '+alias+'(\n '+',\n '.join(declarations)+'\n);\n '+leaf['master']+' #('+params+') u_exact('+', '.join(connections)+');\nendmodule\n'
            (out/(alias+'.sv')).write_text(text)
    (out/'aliases.json').write_text(json.dumps(dict(schema='opentallas.s81.vm-name-only-aliases.v1',aliases=records,normal_cycle_delta=0,added_registers=0),indent=1)+'\n')
    return records


def main():
    import gzip
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=json.loads(gzip.decompress(a.plan.read_bytes())if a.plan.suffix=='.gz'else a.plan.read_bytes())
    r=build(plan,a.inputs,a.out,Path(__file__).resolve().parents[1]/'ref_tile/rename_view.py')
    print('VM_VIEW_ALIASES PASS actual_kits='+str(len(r))+' added_registers=0 normal_cycle_delta=0')


if __name__=='__main__':main()
