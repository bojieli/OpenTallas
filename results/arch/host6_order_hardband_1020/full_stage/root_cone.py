from pathlib import Path
import json,re,sys,collections
sys.path.insert(0,'/helpers');import textbook_lint as T;import native_census as N
raw=Path('/work/final.v');g,top=T.flatten(T.parse_verilog(raw.read_text()),'qkd_hr_core_order_n32');a=T.build(g,None);root=g.ports['host_rst_n'][1];ck=g.ports['ck_core'][1]
libs=sorted(set(re.findall(r'^read_liberty (\S+)',Path('/gate/cts.log').read_text(),re.M)));roles,receipts=N.liberty_roles(libs)
rows=[]
for ci,pin,unused in a['loads'].get(root,[]):
 typ,name,pins=g.cells[ci];clock=pins.get('CLK',[]);path=[];net=clock[0] if clock else None;seen=set();pol=0
 while net is not None and net!=ck and net not in seen:
  seen.add(net)
  if net not in a['driver']:break
  driver,pn=a['driver'][net]
  if driver<0:break
  dt,dn,dp=g.cells[driver];role=roles.get(dt);fn=(role or {}).get('pins',{}).get(pn,{}).get('function');inputs=[(p,x) for p,bs in dp.items() if (role or {}).get('pins',{}).get(p,{}).get('direction')=='input' for x in bs]
  path.append(dict(cell=dn,master=dt,output_pin=pn,function=fn,inputs=[dict(pin=p,net=g.net_name[x]) for p,x in inputs]))
  if len(inputs)!=1 or fn is None:break
  f=re.sub(r'[\s()]','',fn);ip,ix=inputs[0]
  if f not in [ip,'!'+ip,'~'+ip,ip+"'"]:break
  pol^=(f!=ip);net=ix
 rows.append(dict(cell=name,master=typ,pin=pin,D=[g.net_name[x] for x in pins.get('D',[])],CLK=[g.net_name[x] for x in clock],literal_clock_equal=clock==[ck],clock_resolves_to_declared=net==ck,clock_inversion=pol,clock_path=path))
n=json.loads(Path('/work/final_native.json').read_text());clockloads=[]
for v in n.get('violations',[]):
 if v['driver']=='ck_core':
  for ci,pn,bit in v['endpoints']:
   typ,name,pins=g.cells[ci];role=roles.get(typ,{})
   clockloads.append(dict(cell=name,master=typ,pin=pn,pins={p:[g.net_name[x] for x in xs] for p,xs in pins.items()},functions={p:r.get('function') for p,r in role.get('pins',{}).items() if r.get('direction')=='output'}))
result=dict(final_v_sha256=__import__('hashlib').sha256(raw.read_bytes()).hexdigest(),root_firstD=rows,raw_native_clock_offenders=clockloads,liberty=receipts)
Path('/work/root_clock_cone.json').write_text(json.dumps(result,indent=2));print('ROOT_CLOCK',len(rows),collections.Counter((r['master'],r['literal_clock_equal'],r['clock_resolves_to_declared'],r['clock_inversion']) for r in rows));print('CLOCK_OFFENDER_CLASSES',collections.Counter((r['master'],r['pin']) for r in clockloads))
