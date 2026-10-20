import json,sys,inspect
from pathlib import Path
sys.path.insert(0,'/src/tools/ref_tile');sys.path.insert(0,'/src/tools')
import native_census as NC
import textbook_lint as TL
old=json.loads(Path('/work/native_census.json').read_text())
roles,_=NC.liberty_roles([p['path'] for p in old['liberty']])
g,top=TL.flatten(TL.parse_verilog(Path(old['netlist']['path']).read_text()),old['top'])
# Diagnostic reporting only: same census logic/Liberty, remove output-list truncation.
code=inspect.getsource(NC.census).replace('[:40]', '[:]')
ns=dict(NC.__dict__);exec(code,ns);x=ns['census'](g,roles)
assert (x['max_dynamic_loads'],len(x['violations']),len(x['role_errors']))==(49,9,0)
out=[]
for v in x['violations']:
 row={k:v[k] for k in ['driver','net','loads','driver_role']};row['load_pins']=[]
 for ci,pn,bit in v['endpoints']:
  if ci=='port': row['load_pins'].append({'port':pn,'bit':bit})
  else:
   master,name,pins=g.cells[ci];row['load_pins'].append({'instance':name,'master':master,'pin':pn,'bit':bit})
 assert len(row['load_pins'])==row['loads'];out.append(row)
print(json.dumps(out,indent=2))
