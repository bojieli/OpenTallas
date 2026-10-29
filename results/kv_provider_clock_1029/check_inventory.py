import copy,importlib.util,json,sys
from pathlib import Path
b=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('inv',b/'inventory.py');I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
m=json.loads((b/'provider_mapped.json').read_text());s=json.loads((b/'start_stages.json').read_text());lef=Path(sys.argv[2]).read_text()
p=I.inventory(m,s,lef)
(b/'provider_cells_aliases.json').write_text(json.dumps(p,indent=1)+'\n')
controls={}
for kind in ['wrong_stage','unknown_cell','missing_declared_ff']:
 mm=copy.deepcopy(m);ss=copy.deepcopy(s)
 if kind=='wrong_stage':
  old=ss['die_outputs'][0]['stage'];ss['die_outputs'][0]['stage']=next(x['id'] for x in ss['stages'] if x['id']!=old)
 elif kind=='unknown_cell':
  cm=mm['modules']['ot_die_start_stages']['cells'];key=next(k for k,c in cm.items() if c['type']!='$scopeinfo');cm['unowned.'+key]=cm.pop(key)
 else:
  cm=mm['modules']['ot_die_start_stages']['cells']
  launched={x['launch_inst'] for x in p['outputs']}
  key=next(k for k,c in cm.items() if c['type'].startswith('DFF') and k not in launched)
  del cm[key]
 try:I.inventory(mm,ss,lef)
 except ValueError as e:controls[kind]={'caught':True,'reason':str(e)}
 else:raise RuntimeError('missed '+kind)
r={'positive_counts':p['counts'],'controls':controls,'output_inv_counts':{str(n):sum(len(x['output_inverters'])==n for x in p['outputs']) for n in {len(x['output_inverters']) for x in p['outputs']}}}
(b/'inventory_controls_aliases.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
