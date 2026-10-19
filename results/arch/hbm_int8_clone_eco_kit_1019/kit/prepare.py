"""Deterministic source-only topology/typed allowlist generator. Does not load OpenDB."""
import json,gzip,pathlib,hashlib
P=pathlib.Path(__file__).parent
load=lambda n:json.load(gzip.open(P/'inputs'/(n+'.json.gz'),'rt'))
raw=load('raw'); pos=load('positions'); scope=load('scope'); packing=load('packing'); retained=load('retained')
m=next(iter(raw['modules'].values()));cells=m['cells'];mods={};adds={};rewires=[];nets={};branches=[]
def endpoint(n,p):return dict(cell=n,pin=p)
def add(n,master):
 assert n not in cells and n not in adds,n
 adds[n]=dict(name=n,master=master)
def net(n):
 assert n not in [z['name'] for z in m['net_metadata'].values()]
 nets[n]=n;return n
def pin_net(n,p):
 z=cells[n]['connections'][p];assert len(z)==1;return m['net_metadata'][str(z[0])]['name']
def move(n,p,to):
 rewires.append(dict(**endpoint(n,p),original_net=pin_net(n,p) if n in cells else None,new_net=to))
def chain(names,source,finish=None):
 for i,n in enumerate(names):
  out=net(n+'_Y') if i<len(names)-1 or finish is None else finish
  move(n,'A',source);move(n,'Y',out);source=out
 return source
for r in retained['boundary']:
 d=r['driver'];assert cells[d['cell']]['type']==d['master'];mods[d['cell']]=dict(old_master=d['master'],new_master='INVx6_ASAP7_75t_R',role='boundary')
for key,c in retained['typed_cones'].items():
 d=next(p for p in c['native_pins'] if p['direction']=='output');name=d['cell'];master=d['master']
 if master.startswith('NAND'):
  mods[name]=dict(old_master=master,new_master='NAND2x2_ASAP7_75t_R',role='internal_nand');continue
 mods[name]=dict(old_master=master,new_master='INVx6_ASAP7_75t_R',role='reset_split')
 original=pin_net(name,'Y');source=pin_net(name,'A');groups=packing['reset_branch_exact_native_sinks'][key]
 for b,group in enumerate(groups):
  names=[f'int8_reset_{key}_b{b}_hb{k}' for k in range(4)]
  for n in names:add(n,'HB4xp67_ASAP7_75t_R')
  final=chain(names,source)
  inv=name if b==0 else f'int8_reset_{key}_b1_inv'
  if b:add(inv,'INVx6_ASAP7_75t_R')
  move(inv,'A',final)
  if b:
   out=net(inv+'_Y');move(inv,'Y',out)
   for p in group:move(p['cell'],p['pin'],out)
  branches.append(dict(role='reset_split',source_net=source,buffers=names,inverter=inv,sinks=[endpoint(p['cell'],p['pin']) for p in group]))
for r in scope['plans']:
 n,p=r['endpoint'].rsplit('/',1);assert cells[n]['type'].startswith('DFF');assert p==('D' if r['role']=='data' else 'RESETN')
 source=pin_net(n,p);names=[c['name'] for c in r['added_cells']]
 for name in names:add(name,'HB4xp67_ASAP7_75t_R')
 out=chain(names,source);move(n,p,out);branches.append(dict(role=r['role'],source_net=source,buffers=names,sinks=[endpoint(n,p)]))
assert len(mods)==1078 and len(adds)==1866
assert len({(r['cell'],r['pin']) for r in rewires})==len(rewires)
placed={r['name']:r for r in packing['placed']};assert set(placed)==set(mods)|set(adds)
a=dict(schema='int8.exact_clone_allowlist.v1',model_commit='feb988a7a',checkpoint_sha256=raw['source_odb_sha256'],replacement_cells=mods,added_cells=adds,added_nets=sorted(nets),rewired_pins=rewires,branches=branches,placement=placed,counts=dict(replacements=len(mods),additions=len(adds),extra_pg=3732,ordinary_branches=594,reset_hold_branches=10,reset_split_branches=12),immutable=dict(all_ff=2782,clock_cells=253,open_clock_load_cells=110),area_um2=1667.54376)
assert a['checkpoint_sha256']=='fc6b007164e4e5c2a934052922d40114cc4fc60602423d023aa53fa2a67d2081'
(P/'allowlist.json').write_text(json.dumps(a,indent=2)+'\n')
def q(s):
 assert '{' not in str(s) and '}' not in str(s);return '{'+str(s)+'}'
t=[]
for n,r in mods.items():t.append('eco_replace '+q(n)+' '+q(r['old_master'])+' '+q(r['new_master']))
for n,r in adds.items():t.append('eco_add '+q(n)+' '+q(r['master']))
for n in sorted(nets):t.append('eco_net '+q(n))
for r in rewires:t.append('eco_connect '+' '.join(q(r[k]) for k in ['cell','pin'])+' '+q(r['original_net'] or '')+' '+q(r['new_net']))
for n,r in placed.items():t.append('eco_place '+q(n)+' '+' '.join(str(x) for x in r['bbox'][:2]))
(P/'exact_changes.tcl').write_text('# GENERATED; source only after exact grant. No engine was invoked by generator.\n'+'\n'.join(t)+'\n')
print('SOURCE_ONLY_ALLOWLIST',a['counts'],'rewired_pins',len(rewires),'new_nets',len(nets))
