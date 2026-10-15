#!/usr/bin/env python3
"""Source-derived typed join and physical pin inventory, not a q3 numeric proof."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/hbm_accel/generic/collective/p2p'

def header(source,name):
 source=re.sub(r"//[^\n]*", "", source)
 start=re.search(r'\bmodule\s+'+name+r'\b',source).start()
 text=source[start:source.index(');',start)]
 result={}
 for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*(.*?)(?=\b(?:input|output)\s+(?:wire|reg)|$)',text,re.S):
  width=1
  if m[2]:
   a,b=m[2][1:-1].split(':')
   assert re.fullmatch(r'[0-9+*\- ()]+',a+b)
   width=int(eval(a,{'__builtins__':{}}))-int(eval(b,{'__builtins__':{}}))+1
  for name in m[3].strip().rstrip(',').split(','):
   name=name.strip()
   assert re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*',name),name
   result[name]={'direction':m[1],'width':width}
 return result

def check():
 source=(P/'ot_hfd_coll_q_static_v3.sv').read_text()
 result={}
 for npt in (3,2):
  name=f'ot_hfd_coll_q{npt}_static_host_v3'
  wrapper=(P/f'{name}.sv').read_text()
  ports=header(wrapper,name)
  child=header(source,f'ot_hfd_coll_q{npt}_static_v3')
  connections=dict(re.findall(r'\.(\w+)\((\w+)\)',wrapper.split(f'ot_hfd_coll_q{npt}_static_v3 u_q(',1)[1].split(');',1)[0]))
  assert set(connections)==set(child),(set(connections)^set(child))
  for port,net in connections.items():
   if net in ports:assert child[port]['width']==ports[net]['width'],(port,net)
  for pin,width in [('issuer_busy',1),('issuer_fault',1),('issuer_uop_v',1),('issuer_uop_pc',6)]:
   assert child[pin]=={'direction':'output','width':width}
   assert connections[pin]==pin
  assert '.qid(QID)' in wrapper and '.TARGET(8\'d52+8\'(QID))' in wrapper
  assert '.program_active(hgi_busy)' in wrapper
  assert not re.search(r'\bu_q\.[a-zA-Z_]',wrapper),'hierarchical feedback reference'
  clocks={p:d['width'] for p,d in ports.items() if p.startswith('clk_')}
  result[name]={'ports':ports,'input_bits_excluding_clock_reset':sum(d['width'] for p,d in ports.items() if d['direction']=='input' and p not in clocks and p!='rst_n'),
   'output_bits':sum(d['width'] for d in ports.values() if d['direction']=='output'),
   'clock_pins':clocks,'logical_clock_roots':sum(clocks.values()),
   'actual_native_child':f'ot_hfd_coll_q{npt}_static_v3','physical_QID':'0' if npt==3 else '1..3','host_target':'52+QID',
   'feedback':'all9bits direct nativeissuer ports, typed bound; no hierarchical reference',
   'mechanism_scope':'q2 native functional bench; q3 binding/header only, no q3 numerical or fullparent physical qualification'}
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args()
 text=json.dumps(check(),indent=2)+'\n'
 if a.out:a.out.write_text(text)
 else:print(text,end='')
