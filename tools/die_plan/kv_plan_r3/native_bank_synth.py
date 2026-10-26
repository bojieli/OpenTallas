#!/usr/bin/env python3
"""Map an exact emitted bank inventory and check every kept stage identity.

This is a bank-only identity/area coupon, not synthesis of the full partition.
Equal bank inputs deliberately exercise accidental prefix merging.
"""
import argparse,json
from pathlib import Path

def generate(m,out):
 lines=[];tops=[];expected=[]
 for tn,info in m['types'].items():
  banks=info['banks'];lines.append(f'module coupon_{tn}(input clk,d, output [{len(banks)-1}:0] q);')
  for i,(bank,b) in enumerate(banks.items()):
   lines.append(f'ot_dp_landing_bank #(.W(1),.D({b["depth"]})) {bank} (.clk(clk),.d(d),.q(q[{i}]));')
   for part in info['parts']:
    expected += [part+'/'+x for x in b['stage_ids']]
  lines.append('endmodule')
  for part in info['parts']:tops.append((tn,part,len(banks)))
 total=sum(x[2] for x in tops);lines.append(f'module native_bank_synth(input clk,d,output [{total-1}:0] q);');off=0
 for tn,part,n in tops:
  lines.append(f'coupon_{tn} {part} (.clk(clk),.d(d),.q(q[{off} +: {n}]));');off+=n
 lines.append('endmodule');out.mkdir(parents=True,exist_ok=True);(out/'synth.sv').write_text('\n'.join(lines)+'\n');(out/'expected.json').write_text(json.dumps(expected))
 assert len(expected)==m['total_ff']
 print(json.dumps(dict(expected_ff=len(expected),parts=len(tops))))

def check(mapped,expected,out):
 modules=mapped['modules'];actual=[];other=[]
 def walk(mod,path):
  for name,c in modules[mod].get('cells',{}).items():
   typ=c['type'];p=path+'/'+name if path else name
   if typ in modules and not modules[typ].get('attributes',{}).get('blackbox'):walk(typ,p)
   elif 'DFF' in typ:actual.append((p,typ))
   else:other.append((p,typ))
 walk('native_bank_synth','');found={x:[] for x in expected};unexpected=[]
 for p,t in actual:
  stage=p.rsplit('/',1)[0]
  if stage in found:found[stage].append((p,t))
  else:unexpected.append((p,t))
 bad={k:v for k,v in found.items() if len(v)!=1};r=dict(verdict='PASS' if not bad and not unexpected and len(actual)==len(expected) else 'FAIL',expected_ff=len(expected),actual_ff=len(actual),bad_stage_identities=bad,unexpected_ff=unexpected,nonff_cell_types={t:sum(z==t for _,z in other) for t in set(z for _,z in other)})
 out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['bad_stage_identities','unexpected_ff']}));assert r['verdict']=='PASS'
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True);g=s.add_parser('generate');g.add_argument('manifest');g.add_argument('out');c=s.add_parser('check');c.add_argument('mapped');c.add_argument('expected');c.add_argument('out');a=p.parse_args()
 if a.op=='generate':generate(json.load(open(a.manifest)),Path(a.out))
 else:check(json.load(open(a.mapped)),json.load(open(a.expected)),Path(a.out))
