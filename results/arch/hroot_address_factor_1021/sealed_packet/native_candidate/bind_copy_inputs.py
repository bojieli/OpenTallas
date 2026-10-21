#!/usr/bin/env python3
"""Construct a proof-only exact-input binding; never use as a physical tile.

Every extra port is enumerated by the source-pinned generator record. Input
copies are physically assigned the original input, and output copies become
internal wires. The unchanged strict certificate then compares identical top
interfaces without interpreting an alias map. A changed alias fails the usual
pin relation check. Reset/input fanout intentionally recombines in this proof
vehicle; the independent shipping-shell census is still required.
"""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=Path,required=True)
p.add_argument('--record',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args(); r=json.loads(a.record.read_text()); s=a.source.read_text()
assert hashlib.sha256(a.source.read_bytes()).hexdigest()==r['generated_sha256']
for direction,key in [('input','port_copies'),('output','output_copies')]:
 for name,n in r.get(key,{}).items():
  assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name),name
  for k in range(1,n):
   alias=f'{name}__c{k}'
   # Generated scalar copy ports are the only interface additions accepted.
   pattern=rf',\n  {alias}(?=,|\n\);)'
   s,count=re.subn(pattern,'',s,count=1); assert count==1,alias
   decl=f'  {direction} wire {alias};'
   assert s.count(decl)==1,alias
   replacement=f'  wire {alias};'
   if direction=='input': replacement+=f'\n  assign {alias} = {name};'
   s=s.replace(decl,replacement)
s=re.sub(r'^`timescale[^\n]*\n','',s)  # structural parser requires a module-first statement
a.out.write_text(s)
print('EXACT_INPUT_BINDING_WRITTEN',a.out)
