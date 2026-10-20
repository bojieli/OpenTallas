import sys,json
from pathlib import Path
sys.path.insert(0,'/src/tools');sys.path.insert(0,'/src/tools/ref_tile')
import native_census as NC
j=json.load(open('/work/native_census.json'));roles,_=NC.liberty_roles([x['path'] for x in j['liberty']]);mods=NC.TL.parse_verilog(Path(j['netlist']['path']).read_text());mods={k:v for k,v in mods.items() if k==j['top'] or k not in roles};g,_=NC.TL.flatten(mods,j['top']);v=next(v for v in j['violations'] if 'ib_i[125]' in v['driver']);out={'violation':v,'terminals':[{'cell':g.cells[i][1],'master':g.cells[i][0],'pin':p,'bit':b} for i,p,b in v['endpoints']]};Path('/work/ib125_terminals.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['terminals'],indent=2))
