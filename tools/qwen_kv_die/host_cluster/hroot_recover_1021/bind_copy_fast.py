#!/usr/bin/env python3
"""Proof-only exact-input binding; unchanged strict checker validates the result.
Single scans avoid O(copy-ports * netlist-size) adapter construction. This source
is NEVER used as the physical candidate and does not establish cold convergence.
"""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=json.load(open(a.record));s=a.source.read_text();assert hashlib.sha256(a.source.read_bytes()).hexdigest()==r['generated_sha256']
aliases={}
for direction,key in [('input','port_copies'),('output','output_copies')]:
 for name,n in r.get(key,{}).items():
  assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name)
  for k in range(1,n):aliases[f'{name}__c{k}']=(direction,name)
head,tail=s.split(');',1);start=head.index('(',head.index('module '+r['top']));ports=[v.strip() for v in head[start+1:].split(',')];assert set(aliases)<=set(ports);assert len(ports)==len(set(ports))
head=head[:start+1]+'\n  '+',\n  '.join(p for p in ports if p not in aliases)+'\n'
seen=set()
def decl(m):
 direction,name=m[1],m[2]
 if name not in aliases:return m.group()
 assert name not in seen and aliases[name][0]==direction;seen.add(name)
 return '  wire '+name+';'+('\n  assign '+name+' = '+aliases[name][1]+';' if direction=='input' else '')
tail=re.sub(r'^  (input|output) wire ([A-Za-z_][A-Za-z0-9_]*);',decl,tail,flags=re.M);assert seen==set(aliases)
s=re.sub(r'^`timescale[^\n]*\n','',head+');'+tail);a.out.write_text(s);print('PROOF_ONLY_EXACT_INPUT_BINDING',len(aliases))
