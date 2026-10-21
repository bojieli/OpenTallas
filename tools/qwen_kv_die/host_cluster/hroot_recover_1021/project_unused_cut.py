#!/usr/bin/env python3
"""Project only undriven diagnostic cut bits, preserving the actual parent.

Every removed bit must have no child consumer and either no parent consumer or
an existing parent constant driver. No primitive or real top port is changed.
The context record is required for reconnection; this is not tile qualification.
"""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--json',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--record',type=Path,required=True);a=p.parse_args()
j=json.load(open(a.json));soft=j['modules']['native_soft'];parent=j['modules']['qkd_hr_ingest_qm']
def cell_bits(mod,direction):
 return {b for cell in mod['cells'].values() for pn,bs in cell['connections'].items() if cell['port_directions'][pn]==direction for b in bs if isinstance(b,int)}
drivers=cell_bits(soft,'output')|{b for q in soft['ports'].values() if q['direction']=='input' for b in q['bits'] if isinstance(b,int)}
internal_loads=cell_bits(soft,'input')
def candidates(parent):
 insts=[x for x in parent['cells'].values() if x['type']=='native_soft'];assert len(insts)==1;inst=insts[0]
 outer_loads=cell_bits(parent,'input')|{b for q in parent['ports'].values() if q['direction']=='output' for b in q['bits'] if isinstance(b,int)}
 changes=[]
 for name,q in soft['ports'].items():
  if q['direction']!='output':continue
  assert q.get('offset',0)==0 and not q.get('upto',0),('unsupported cut indexing',name)
  bad=[i for i,b in enumerate(q['bits']) if isinstance(b,int) and b not in drivers]
  if not bad:continue
  reasons=[]
  for i in bad:
   assert q['bits'][i] not in internal_loads,('undriven bit feeds child logic',name,i)
   ob=inst['connections'][name][i]
   if isinstance(ob,str):assert ob in ('0','1'),('undefined parent cut value',name,i,ob);why='existing_parent_constant'
   else:assert ob not in outer_loads,('cut bit is not globally unused',name,i,ob);why='no_parent_or_child_consumer'
   reasons.append(dict(index=i,parent_bit=ob,reason=why))
  kept=[i for i in range(len(q['bits'])) if i not in bad]
  changes.append(dict(port=name,old_width=len(q['bits']),kept_indices=kept,removed=reasons,new_port='qkc_context_cut_'+str(len(changes)) if kept else None))
 return changes
changes=candidates(parent);assert changes,'no contextual projection'
s=a.source.read_text();hend=s.index(');');head=s[:hend];tail=s[hend:]
ports=head[head.index('(')+1:].split(',');ports=[x.strip() for x in ports]
new_decls=[];assigns=[]
for c in changes:
 name=c['port'];ident=name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',name) else '\\'+name
 assert ports.count(ident)==1,(name,ports.count(ident));ports.remove(ident)
 pattern=r'^\s*output\s+(?:\[[^\]]+\]\s+)?'+re.escape(ident)+r'\s*;\s*\n'
 tail,n=re.subn(pattern,'\n',tail,count=1,flags=re.M);assert n==1,(name,n)
 if c['kept_indices']:
  new=c['new_port'];assert new not in s;ports.append(new);k=len(c['kept_indices']);width='' if k==1 else f'[{k-1}:0] '
  new_decls.append(f'  output {width}{new};\n  wire {width}{new};')
  # Original public wire and its actual bit numbers remain unchanged internally.
  terms=[ident+' '+f'[{i}]' if c['old_width']>1 else ident+' ' for i in reversed(c['kept_indices'])]
  assigns.append('  assign '+new+' = {'+', '.join(terms)+'};')
head='module native_soft('+', '.join(x+' ' if x.startswith('\\') else x for x in ports)
s=head+tail;s=s.replace(');',');\n'+'\n'.join(new_decls),1);pos=s.index('\nendmodule');s=s[:pos]+'\n'+'\n'.join(assigns)+'\n'+s[pos:]
# Refuse a causal change that exposes a previously discarded integer cut bit.
candidate=next((x for c in changes for x in c['removed'] if isinstance(x['parent_bit'],int)),None);assert candidate
negative=dict(parent);negative['ports']=dict(parent['ports']);negative['ports']['negative_observe_cut']=dict(direction='output',bits=[candidate['parent_bit']])
try:candidates(negative)
except AssertionError as exc:assert 'not globally unused' in str(exc);negative_result=str(exc)
else:raise AssertionError('negative exposed cut bit survived')
a.out.write_text(s)
a.record.write_text(json.dumps(dict(context_json_sha256=hashlib.sha256(a.json.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),projected_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),changes=changes,negative_control=negative_result,qualification=False),indent=1)+'\n')
print('PROJECT_ONLY_CONTEXTUALLY_REDUNDANT_CUT_BITS',sum(len(c['removed']) for c in changes),'NEGATIVE_OBSERVABILITY_REJECTED')
