from pathlib import Path
import json,sys
sys.path.insert(0,'/audit')
import native_census as N
r=Path('/audit');d=json.loads((r/'native_census_final.json').read_text());raw=Path(d['netlist']['path']).read_text()
roles,_=N.liberty_roles([str(p) for p in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('asap7sc7p5t_*_RVT_TT_nldm_*.lib*')])
mods=N.TL.parse_verilog(raw);mods={k:v for k,v in mods.items() if k==d['top'] or k not in roles};g,_=N.TL.flatten(mods,d['top'])
rows=[]
for v in d['violations']:
 row={k:z for k,z in v.items() if k!='endpoints'};row['contacts']=[]
 for e in v['endpoints']:
  ci,pin,bit=e;master,inst,_=g.cells[ci]
  row['contacts'].append(dict(master=master,instance=inst,pin=pin,bit=bit,actual_liberty_role=str(roles.get(master))))
 rows.append(row)
(r/'decoded_clock_contacts.json').write_text(json.dumps(rows,indent=2)+'\n')
print([(x['driver'],x['loads'],[(e['master'],e['pin'],e['instance']) for e in x['contacts'][:5]]) for x in rows])
