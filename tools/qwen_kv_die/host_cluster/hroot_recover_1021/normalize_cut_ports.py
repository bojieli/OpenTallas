#!/usr/bin/env python3
"""Invertible scalar ABI adapter for the private soft diagnostic cut.

No primitive changes. Each new legal scalar pin has an exact old port/bit map.
This avoids a native generator limitation on copy aliases of escaped bus bits.
"""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--record',type=Path,required=True);a=p.parse_args()
sp=importlib.util.spec_from_file_location('cut_parser',a.parser);m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
s=a.source.read_text();mods=m.parse_verilog(s);old=mods['native_soft'];hend=s.index(');');tail=s[hend:];names=[];decls=[];assigns=[];mapping=[]
for port in old.ports:
 assert old.dirs[port] in ('input','output')
 ident=port if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',port) else '\\'+port
 pat=r'^\s*'+old.dirs[port]+r'\s+(?:wire\s+)?(?:\[[^\]]+\]\s+)?'+re.escape(ident)+r'\s*;\s*\n'
 tail,n=re.subn(pat,'\n',tail,count=1,flags=re.M);assert n==1,(port,n)
 indices=[None]
 if port in old.widths:
  hi,lo=old.widths[port];assert hi>=lo;(indices:=list(range(lo,hi+1)))
 for bit in indices:
  new='soft_pin_'+str(len(mapping));assert new not in s;names.append(new);decls.append(f'  {old.dirs[port]} wire {new};')
  expr=ident+' '+('' if bit is None else f'[{bit}]')
  assigns.append(f'  assign {expr} = {new};' if old.dirs[port]=='input' else f'  assign {new} = {expr};')
  mapping.append(dict(pin=new,direction=old.dirs[port],port=port,bit=bit))
s='module native_soft('+', '.join(names)+tail;s=s.replace(');',');\n'+'\n'.join(decls),1);e=s.index('\nendmodule');s=s[:e]+'\n'+'\n'.join(assigns)+'\n'+s[e:]
a.out.write_text(s);a.record.write_text(json.dumps(dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),normalized_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),pin_map=mapping,qualification=False),indent=1)+'\n');print('INVERTIBLE_SCALAR_CUT_PINS',len(mapping))
