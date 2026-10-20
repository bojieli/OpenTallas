import sys,pathlib,json,collections
sys.path[:0]=['/src/tools','/src/tools/ref_tile'];import textbook_lint as T;import native_census as N
D=pathlib.Path('/work');d=json.load(open(D/'native_census_r6.json'));s=pathlib.Path(d['netlist']['path']).read_text();roles,_=N.liberty_roles([x['path'] for x in d['liberty']]);mods=T.parse_verilog(s);mods={k:v for k,v in mods.items() if k==d['top'] or k not in roles};g,_=T.flatten(mods,d['top']);out=[]
drivers={}
for i,(master,name,pins) in enumerate(g.cells):
 role=roles[master]
 for pn,nets in pins.items():
  if role['pins'].get(pn,{}).get('direction')=='output':
   for net in nets:drivers[g.find(net)]=(i,pn)
for v in d['violations'][:3]:
 seen=set();todo=[g.find(g.net(v['net']))];ends=[];cone=[]
 while todo:
  net=todo.pop()
  if net in seen:continue
  seen.add(net);dp=drivers.get(net)
  if dp is None:ends.append({'net':g.net_name[net],'kind':'literal_or_input'});continue
  i,pn=dp;master,name,pins=g.cells[i];role=roles[master]
  if role['sequential']:ends.append({'driver':name+'/'+pn,'master':master});continue
  cone.append({'master':master,'inst':name,'out':pn,'function':role['pins'][pn].get('function')})
  for pnn,ns in pins.items():
   if role['pins'].get(pnn,{}).get('direction')=='input' and not role['pins'][pnn].get('clock'):
    todo.extend(g.find(n) for n in ns)
 out.append({'driver':v['driver'],'loads':v['loads'],'sequential_origins':ends,'combinational_cone':cone})
pathlib.Path('/audit/ancestors_r6.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out)[:12000])
