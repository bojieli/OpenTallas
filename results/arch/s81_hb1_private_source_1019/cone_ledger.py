#!/usr/bin/env python3
"""Read-only evidence extraction; no simulation, SAT or mapping."""
import json,gzip,pathlib
P=pathlib.Path(__file__).resolve().parent
load=lambda p:json.load(gzip.open(p) if str(p).endswith('.gz') else open(p))
m=load(P.parent/'s81_hb1_diagnostic_census_1019/receipt/mapped.json.gz')['modules']['ot_s81sl_xr3'];cells=m['cells'];c=load(P.parent/'s81_hb1_diagnostic_census_1019/receipt/native_census.json.gz');model=load(P.parent/'s81_hb1_fixedpoint_model_1019/correspondence.json.gz');fn=load(P.parent/'s81_hb1_cell_semantics_1019/projection_manifest.json')['masters']
norm=lambda s:s.replace('\\','');native={norm(r['instance']):r['instance'] for r in c['pin_inventory']};directions={(norm(r['instance']),r['pin']):r['direction'] for r in c['pin_inventory'] if r['signal'] not in ('POWER','GROUND')};owner={b[0]:(n,p) for n,cell in cells.items() for p,b in cell['connections'].items() if directions[n,p]=='OUTPUT'};roots={r['driver']:r for r in c['records'] if r['driver']!='PORT'};assign={(norm(d),dc,p):(norm(s),sc,iv) for s,sc,d,dc,p,iv in model['endpoint_assignments'] if d!='PORT'};inputs={b:f'{n}[{j}]' for n,p in m['ports'].items() if p['direction']=='input' for j,b in enumerate(p['bits'])};records={};states=set()
def wire(mode,b,nxt=False):
 if b in inputs:return {'input':inputs[b]}
 if isinstance(b,str):return {'constant':b}
 n,p=owner[b];return visit(mode,n,0,p,nxt)
def pin(mode,n,ci,p,nxt=False):
 a=assign.get((n,ci,p)) if mode=='candidate' else None
 if a:
  s,sc,iv=a;r=roots[native[s]];return {'assigned_native_root':native[s],'copy':sc,'inverted':iv,'edge':visit(mode,s,sc,r['pin'],False)}
 return {'original_bit':cells[n]['connections'][p][0],'edge':wire(mode,cells[n]['connections'][p][0],nxt)}
def visit(mode,n,ci,p,nxt):
 k=json.dumps([mode,n,ci,p,nxt]);ref={'node':k}
 if k in records:return ref
 cell=cells[n];ty=cell['type'];r={'mode':mode,'native_instance':native[n],'copy':ci,'master':ty,'output':p,'phase':'NEXT' if nxt else 'PRESENT'};records[k]=r
 if ty.startswith('DFF'):
  if not nxt:
   states.add((mode,n,ci));r['state']='canonical-shared' if ci==0 else 'extra-independent';return ref
  pins=['D']+(['RESETN','SETN'] if ty.startswith('DFFASR') else []);r['boolean_next']='QN=~D with original asynchronous SETN/RESETN action';r['inputs']={q:pin(mode,n,ci,q) for q in pins}
 else:r['Liberty_function']=fn[ty]['functions'][p];r['inputs']={q:pin(mode,n,ci,q,nxt) for q in cell['connections'] if directions[n,q]=='INPUT'}
 return ref
targets={mode:{p:wire(mode,m['ports'][p]['bits'][0],True) for p in ('sw_d','sw_v')} for mode in ('native','candidate')};seen=set();asr=[]
while states-seen:
 for mode,n,ci in list(states-seen):
  seen.add((mode,n,ci))
  if cells[n]['type'].startswith('DFFASR'):asr.append({'mode':mode,'instance':native[n],'copy':ci,'actual_async_inputs':{p:pin(mode,n,ci,p) for p in ('RESETN','SETN')}})
result={'scope':'Full static exact cone and ASR ancestor ownership; arbitrary present-state NEXT diagnostic only','targets':targets,'nodes':records,'async_owners':asr,'sequential_boundaries':len(states),'Boolean_function_authority':'frozen canonical TT Liberty; binary-only semantics; official4state caveats separately retained'}
(P/'nextstate_receipt/full_cone_ledger.json').write_text(json.dumps(result,indent=2)+'\n');print({'nodes':len(records),'state_boundaries':len(states),'async_owners':len(asr)})
