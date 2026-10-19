import json,re,hashlib,math,collections,csv
from pathlib import Path
P=Path('/srv/opentallas-scratch/claude/hd4g/gen2d/forest_codex9d5a2c350'); C=P.parent.parent/'gen2c/case_a'; O=Path.cwd();m=json.load(open(P/'manifest.json'));c=json.load(open(P/'contract_pre.json'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lefs={}; inputs={str(p):sha(p) for p in [P/'manifest.json',P/'contract_pre.json',C/'run.tcl']}
def lef(master):
 if master not in lefs:
  p=P/'views'/f'{master}.lef';t=p.read_text(); inputs[str(p)]=sha(p);pins={}
  for z in re.finditer(r'^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1',t,re.M|re.S):
   rect=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',z[2]);use=re.search(r'USE\s+(\w+)',z[2]);dr=re.search(r'DIRECTION\s+(\w+)',z[2]);
   if rect:
    r=list(map(float,rect.groups()));pins[z[1]]={'xy':[(r[0]+r[2])/2,(r[1]+r[3])/2],'use':use[1] if use else None,'direction':dr[1] if dr else None}
  lefs[master]=pins
 return lefs[master]
def point(n,p,b=0,nb=1):
 v=m['placement'][n];master=v.get('m') or v.get('master');q=lef(master)[f'{p}[{b}]' if nb>1 else p]['xy'];x,y=q
 if v.get('o') in ['MY','R180']:x=v['w']-x
 if v.get('o') in ['MX','R180']:y=v['h']-y
 return [v['x']+x,v['y']+y]
import reset_rows_frozen
rows=reset_rows_frozen.plan_rows(c)
sinks=[]
for z in c['clock_resets']:
 if z['kind']!='reset' or z['domain']!='hbm' or z['source'][0]!='hb_ckgen':continue
 if z['port']=='rs' and z['instance'] in rows['parent']:continue
 for b in range(z['bits']):
  try:xy=point(z['instance'],z['port'],b,z['bits']);err=None
  except Exception as e:xy=None;err=str(e)
  sinks.append(dict(instance=z['instance'],port=z['port'],bit=b,bits=z['bits'],domain='hbm',source=z['source'],xy_um=xy,pin_error=err))
assert len(sinks)==810,len(sinks)
placements=[dict(name=n,**v) for n,v in m['placement'].items()];clock=[]
for line in open(C/'run.tcl'):
 a=re.search(r'place_inst -name (dk[hrs]_\S+) -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)',line)
 if a:clock.append(dict(name=a[1],x=float(a[2]),y=float(a[3]),orientation=a[4],envelope_um=[1.62,.27],envelope_basis='frozen allocator conservative; native master indexed separately'))
clock_byname={x['name']:x for x in clock}
for line in open(C/'die.v'):
 a=re.match(r'\s*(\w+)\s+(dk[hrs]_\S+)\s*\((.*?)\);',line)
 if a and a[2] in clock_byname:clock_byname[a[2]].update(master=a[1],connections=dict(re.findall(r'\.(\w+)\(([^()]*)\)',a[3])))
inputs[str(C/'die.v')]=sha(C/'die.v')
# Deterministic new skeleton, never a recovered failed reservation. Every grid step is 302.4um.
source=point('hb_ckgen','por_hbm');step=302.4;origin=[math.floor(source[0]/43.2)*43.2,math.floor(source[1]/43.2)*43.2];nodes={(0,0):{'parent':None,'sinks':[]}};edges=set()
for k,s in enumerate(sinks):
 if s['xy_um'] is None:continue
 gx,gy=[round((s['xy_um'][i]-origin[i])/step) for i in [0,1]];prev=(0,0)
 for axis,end in [(0,gx),(1,gy)]:
  while prev[axis]!=end:
   nxt=list(prev);nxt[axis]+=1 if end>prev[axis] else -1;nxt=tuple(nxt)
   if nxt not in nodes:nodes[nxt]={'parent':prev,'sinks':[]}
   edges.add((prev,nxt));prev=nxt
 nodes[prev]['sinks'].append(k);s['branch_owner']=f'joint_hbm_{prev[0]}_{prev[1]}'
# Spatial bins for exact frozen outlines and all clock envelopes. No alternate-home search.
bins=collections.defaultdict(list);obs=[]
for v in placements:
 obs.append(dict(name=v['name'],kind='placed_outline',rect=[v['x'],v['y'],v['x']+v['w'],v['y']+v['h']]))
for v in clock:obs.append(dict(name=v['name'],kind='clock_allocator_envelope',rect=[v['x'],v['y'],v['x']+1.62,v['y']+.27]))
for i,v in enumerate(obs):
 x0,y0,x1,y1=v['rect']
 for bx in range(int(x0//500),int(x1//500)+1):
  for by in range(int(y0//500),int(y1//500)+1):bins[bx,by].append(i)
ledger=[]
for key,n in sorted(nodes.items()):
 x,y=[origin[i]+step*key[i] for i in [0,1]];r=[x-16.2,y-16.2,x+16.2,y+16.2];hit=set()
 for bx in range(int(r[0]//500),int(r[2]//500)+1):
  for by in range(int(r[1]//500),int(r[3]//500)+1):
   for i in bins[bx,by]:
    a,b,d,e=obs[i]['rect']
    if max(r[0],a)<min(r[2],d) and max(r[1],b)<min(r[3],e):hit.add(i)
 children=sorted(b for a,b in edges if a==key);local=n['sinks'];copies=max(1,math.ceil(len(local)/24));ledger.append(dict(id=f'joint_hbm_{key[0]}_{key[1]}',grid=list(key),center_um=[x,y],proposed_outline_um=r,parent=list(n['parent']) if n['parent'] else None,children=[list(x) for x in children],sink_indices=local,local_copy_lower_bound=copies,conflicts=[obs[i]['name'] for i in sorted(hit)],status='REJECTED_CONFLICT' if hit else 'UNQUALIFIED_PG_TRACK_NATIVE'))
report=dict(status='FINITE_CANDIDATE_REJECTED_NO_ENGINE',die_um=m['die_um'],sinks=len(sinks),pin_errors=sum(s['pin_error'] is not None for s in sinks),placed_outlines=len(placements),clock_cells=len(clock),clock_master_counts=dict(collections.Counter(x.get('master','UNBOUND') for x in clock)),source={'instance':'hb_ckgen','port':'por_hbm','xy_um':source,'new_binding':True,'old_failed_predecessor':None},grid_origin_um=origin,grid_step_um=step,homes=len(ledger),conflicted_homes=sum(bool(x['conflicts']) for x in ledger),edges=len(edges),pg_track_via_occupancy=None,actual_tt_ff_phase=None,native_clock_out_master=None,leaf_pin_distance_max_um=max(sum(abs(s['xy_um'][i]-(origin[i]+step*round((s['xy_um'][i]-origin[i])/step))) for i in [0,1]) for s in sinks if s['xy_um']),inputs=inputs)
for name,obj in [('sinks.json',sinks),('placements.json',placements),('clock_cells.json',clock),('reservation_ledger.json',ledger),('report.json',report),('consumed_lef_pins.json',lefs)]: (O/name).write_text(json.dumps(obj,indent=1)+'\n')
print(json.dumps(report,indent=2))
# Complete inherited row ownership and native macro supply-role inventory (not routed connectivity).
pgmasters={}
for v in placements:
 master=v.get('m') or v.get('master')
 if master not in pgmasters:
  try:pgmasters[master]={k:p for k,p in lef(master).items() if p['use'] in ['POWER','GROUND']}
  except Exception as e:pgmasters[master]={'ERROR':str(e)}
(O/'row_ownership.json').write_text(json.dumps({k:rows[k] for k in ['heads','parent','depth','lag','root','stats']},indent=1)+'\n')
(O/'macro_supply_roles.json').write_text(json.dumps(pgmasters,indent=1)+'\n')
report['macro_masters']=len(pgmasters);report['macro_pg_term_bindings_required']=sum(len(pgmasters[v.get('m') or v.get('master')]) for v in placements);report['row_original_hbm_pins']=3793;report['row_contracted_hbm_children']=2983;report['inputs']=inputs
(O/'report.json').write_text(json.dumps(report,indent=1)+'\n')
files={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in O.glob('*.json') if p.name!='manifest.json'}
(O/'manifest.json').write_text(json.dumps(files,indent=1)+'\n')
