import sys,pathlib,json,collections
sys.path[:0]=['/src/tools','/src/tools/ref_tile'];import textbook_lint as T;import native_census as N
D=pathlib.Path('/work');d=json.load(open(D/'native_census_r5.json'));s=pathlib.Path(d['netlist']['path']).read_text();roles,_=N.liberty_roles([x['path'] for x in d['liberty']]);mods=T.parse_verilog(s);mods={k:v for k,v in mods.items() if k==d['top'] or k not in roles};g,_=T.flatten(mods,d['top']);out=[]
for v in d['violations']:
 z={k:v[k] for k in ['driver','net','loads']};z['sink_names']=[g.cells[i][1]+'/'+pin for i,pin,_ in v['endpoints']];nid=g.find(g.net(v['net']));z['alias_names']=[name for i,name in enumerate(g.net_name) if g.find(i)==nid];out.append(z)
pathlib.Path('/audit/six_roots_named.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out)[:18000])
