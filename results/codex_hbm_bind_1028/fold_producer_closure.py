"""Diagnose recursive source obligations before emitting the physically placed S-role service copies.
A physicalclone is not a source. Preserveunknown dependencies as OPEN rather than tying/aliasing them.
"""
from pathlib import Path
import json,re,sys,collections
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'tools'),str(root/'tools/die_plan')]
import die_port_bind as D,bind_elab as E
native=Path(sys.argv[1]);manifest=Path(sys.argv[2]);out=Path(sys.argv[3]);ab=json.loads(manifest.read_text());base=Path(ab.get('base',root));idx=E.module_index(ab['rtl_roots'],ab['files'],base);prefer=[str(base/f) if not Path(f).is_absolute() else f for f in ab['prefer']]
nets,tin,tout,insts=D.parse_die(native,'hbm_current_native_top');I={i:(m,p,c) for m,i,p,c in insts};req=json.loads((Path(__file__).with_name('core_requirements.json')).read_text())['hub_candidates'];rows=[]
for r in req:
 src=r['template'];dst=r['asbuilt_required'];mod,params,conns=I[src];f,_=E.pick(idx,ab.get('alias',{}).get(mod,mod),prefer);mm=next(x for x in D.parse_modules(Path(f).read_text(),f) if x.name==ab.get('alias',{}).get(mod,mod));role=r['role'];nrole='NW' if role=='SW' else 'NE'
 missing=collections.defaultdict(list);provided=[];inputs=[]
 for pn,expr in conns.items():
  new=expr.replace('_'+nrole,'_'+role);names=set(re.findall(r'\b[A-Za-z_]\w*\b',re.sub(r"\d+'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ]+",'',new)))
  if mm.ports[pn][0]=='input':
   for n in sorted(names):
    if n not in nets:missing[n].append(pn)
   inputs.append(dict(port=pn,expression=new))
  else:
   for n in sorted(names):provided.append(dict(net=n,port=pn,existing_top_input=n in tin,declared=n in nets))
 rows.append(dict(instance=dst,template=src,module=mod,params=params,source_inputs=inputs,produced=provided,undefined_input_nets=dict(missing)))
provided={p['net']:r['instance'] for r in rows for p in r['produced']}
for r in rows:
 r['undefined_after_all28']={n:ps for n,ps in r['undefined_input_nets'].items() if n not in provided}
rec=dict(schema='opentallas.hbm.fold_producer_closure.v1',candidate_instances=len(rows),undefined_after_all28=sorted({n for r in rows for n in r['undefined_after_all28']}),rows=rows)
out.write_text(json.dumps(rec,indent=2)+'\n');print('candidates',len(rows),'missingupstreamnets',len(rec['undefined_after_all28']));print('\n'.join(rec['undefined_after_all28']))
