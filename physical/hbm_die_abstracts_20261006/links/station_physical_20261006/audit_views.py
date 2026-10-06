#!/usr/bin/env python3
"""Read real timing models; report actual units, root caps and routed clockQ."""
import argparse,json,re,hashlib,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--views',required=True,type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(root/'tools'))
from chip_assembly.etm import _groups,_NUM
v=a.views;manifest=json.loads((v/'export.json').read_text());result={'name':manifest['name'],'status':'ACTUAL_ETM_AUDIT_PARENT_OPEN','parent_closed':False,'corners':{}}
for corner in ('ss','ff'):
 f=v/f'{manifest["name"]}_{corner}.lib';s=f.read_text()
 tm=re.search(r'time_unit\s*:\s*"([0-9.]+)(ps|ns)"',s);assert tm
 scale=float(tm[1])*(1 if tm[2]=='ps' else 1000)
 cp=re.search(r'capacitive_load_unit\s*\(\s*([0-9.]+)\s*,\s*(ff|pf)\s*\)',s,re.I);assert cp
 capscale=float(cp[1])*(1 if cp[2].lower()=='ff' else 1000)
 caps={};cq={};comb={};setup={};hold={}
 lib=next((s[b:e] for k,n,b,e in _groups(s) if k=='library'))
 for k,n,b,e in _groups(lib):
  if k!='cell':continue
  cell=lib[b:e]
  groups=list(_groups(cell))
  for pk,pn,pb,pe in groups:
   if pk!='pin':continue
   pin=cell[pb:pe]
   if re.search(r'direction\s*:\s*input',pin):
    cm=re.search(r'(?<!_)\bcapacitance\s*:\s*([0-9.eE+-]+)',pin);assert cm and float(cm[1])>0,pn
    caps[pn]=float(cm[1])*capscale
   for tk,tn,tb,te in _groups(pin):
    if tk!='timing':continue
    timing=pin[tb:te];typ=re.search(r'timing_type\s*:\s*"?([a-z_]+)',timing);typ=typ[1] if typ else 'combinational'
    related=re.search(r'related_pin\s*:\s*"?([^";\s]+)',timing);related=related[1] if related else '?'
    values=[]
    for kind,_,vb,ve in _groups(timing):
     if kind not in ('cell_rise','cell_fall','rise_constraint','fall_constraint'):continue
     vm=re.search(r'values\s*\((.*?)\)\s*;',timing[vb:ve],re.S)
     if vm:values.extend(float(x)*scale for x in _NUM.findall(vm[1]))
    if not values:continue
    dest=cq if typ in ('rising_edge','falling_edge') else setup if typ.startswith('setup_') else hold if typ.startswith('hold_') else comb
    dest[pn+' <- '+related]={'min_ps':min(values),'max_ps':max(values),'type':typ}
 assert caps.get('clk_sm',0)>0 and cq,'actual root cap and clockQ required'
 c={'liberty_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'time_scale_to_ps':scale,'cap_scale_to_fF':capscale,'clock_input_cap_fF':caps['clk_sm'],'input_cap_fF':caps,'routed_clockQ':cq,'routed_through':comb,'setup_constraints':setup,'hold_constraints':hold,'clockQ_max_ps':max(d['max_ps'] for d in cq.values()),'clockQ_min_ps':min(d['min_ps'] for d in cq.values())}
 result['corners'][corner]=c
(v/'timing_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({c:{k:d[k] for k in ('clock_input_cap_fF','clockQ_max_ps','clockQ_min_ps')} for c,d in result['corners'].items()}))
