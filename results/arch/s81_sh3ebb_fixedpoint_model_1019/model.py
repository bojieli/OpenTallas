import collections,gzip,hashlib,json,math,pathlib,re
H=pathlib.Path(__file__).resolve().parent; G=H/'graph.json.gz';d=json.load(gzip.open(G,'rt'));rs=d['records']
def inst(pin):return pin.rsplit('/',1)[0]
by={inst(r['driver']):r for r in rs if r['role'] not in ('input','macro')};incoming=collections.defaultdict(dict)
for r in rs:
 for e in r['endpoints']:
  dst,p=e['pin'].rsplit('/',1)
  assert p not in incoming[dst],(dst,p)
  incoming[dst][p]={'owner':r['driver'],'master':r['master'],'inverted':e['inverted']}
copies={n:1 for n in by}; rounds=[]
for i in range(100):
 nxt={n:max(copies[n],math.ceil(sum(copies.get(inst(e['pin']),1) for e in r['endpoints'])/32)) for n,r in by.items()}
 rounds.append(sum(v-1 for v in nxt.values()))
 if nxt==copies:break
 copies=nxt
else:raise AssertionError('no fixedpoint')
geo={r['driver']:r for r in map(json.loads,gzip.open(H/'input/logical_roots.jsonl.gz','rt'))}
rows=[];assign=[];positions={};groups={}
for n,r in by.items():
 es=[(e,k) for e in r['endpoints'] for k in range(copies.get(inst(e['pin']),1))]
 xy={e['pin']:e['xy_um'] for e in geo[r['driver']]['endpoints']}
 es.sort(key=lambda x:(*(xy[x[0]['pin']] or [0,0]),x[0]['pin'],x[1]))
 groups[n]=[es[k:k+32] for k in range(0,len(es),32)]
 if not es:groups[n]=[[]]
 assert len(groups[n])<=copies[n]
 for k,g in enumerate(groups[n]):
  pts=[xy[e['pin']] for e,j in g if xy[e['pin']] is not None]
  positions[n,k]=geo[r['driver']]['source_xy_um'] if k==0 or not pts else [(min(p[a] for p in pts)+max(p[a] for p in pts))/2 for a in (0,1)]
  for e,j in g:assign.append([r['driver'],k,e['pin'],j,e['inverted']])
 if copies[n]>1:rows.append({'instance':n,'driver':r['driver'],'role':r['role'],'master':r['master'],'copies':copies[n],'expanded_loads':len(es),'copy_loads':[len(g) for g in groups[n]],'incoming':incoming[n],'area_um2':(copies[n]-1)*d['masters'][r['master']]['area_um2']})
inputs=[]
for r in rs:
 total=sum(copies.get(inst(e['pin']),1) for e in r['endpoints'])
 assert total<=32*copies.get(inst(r['driver']),1),(r['driver'],total)
 if r['role']=='input':inputs.append({'port':r['driver'],'expanded_loads':total})
extra={role:sum(r['copies']-1 for r in rows if r['role']==role) for role in ('ff','comb','tie')}
lib=pathlib.Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM');clocks={};libhash={};functions={}
for corner in ('TT','FF'):
 p=lib/('asap7sc7p5t_SEQ_RVT_'+corner+'_nldm_220123.lib');t=p.read_text();libhash[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();caps={}
 for m in {r['master'] for r in rows if r['role']=='ff'}:
  c=t[t.index('cell ('+m+')'):];c=c[:c.find('\n  cell (',1)];q=c[c.index('pin (CLK)'):];q=q[:q.index('}')];caps[m]=float(re.search(r'capacitance\s*:\s*([0-9.]+)',q)[1])
 clocks[corner]={'masters_fF':caps,'added_fF':sum((r['copies']-1)*caps[r['master']] for r in rows if r['role']=='ff')}
for p in sorted(lib.glob('*RVT_TT*.lib*')):
 if not any(k in p.name for k in ('AO_','OA_','SIMPLE_','SEQ_')):continue
 t=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text();libhash[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 cells=list(re.finditer(r'cell\s*\(\s*([^\s)]+)\s*\)',t))
 for j,m in enumerate(cells):
  name=m[1];c=t[m.start():cells[j+1].start() if j+1<len(cells) else len(t)]
  if name in {r['master'] for r in rows}:functions[name]={'function_strings':re.findall(r'function\s*:\s*"([^"]+)"',c),'ff_strings':re.findall(r'(?:next_state|clocked_on|clear|preset)\s*:\s*"([^"]+)"',c)}
assert all(r['master'] in functions for r in rows if r['role'] in ('ff','comb'))
far=[]
for driver,k,pin,j,inv in assign:
 src=positions[inst(driver),k];dst=positions.get((inst(pin),j))
 if dst is None:dst=next(e['xy_um'] for e in geo[driver]['endpoints'] if e['pin']==pin)
 if src is not None and dst is not None:
  v=sum(abs(src[a]-dst[a]) for a in (0,1))
  if v>405:far.append([driver,k,pin,j,v])
fam=collections.Counter()
for r in rows:
 if r['role']=='ff':fam[r['instance'].split('[')[0].rstrip('\\')]+=r['copies']-1
out={'scope':'MODEL ONLY; geometric points are not legal placement','source_commit':'3ebb699a9bd3564837e84e018e4c2c7c1e3cae8c','odb_sha256':d['odb_sha256'],'graph_sha256':hashlib.sha256(G.read_bytes()).hexdigest(),'all_roots':len(rs),'assigned_nonmacro_endpoints':len(assign),'all_expanded_endpoints':sum(sum(copies.get(inst(e['pin']),1) for e in r['endpoints']) for r in rs),'round_totals':rounds,'added':extra,'added_area_um2':sum(r['area_um2'] for r in rows),'clock_increment':clocks,'input_max':max(r['expanded_loads'] for r in inputs),'ff_families':dict(fam),'changed':rows,'inputs':inputs,'library_sha256':libhash,'native_master_functions':functions,'point_model_over405':far,'point_model_max_over405':max((r[-1] for r in far),default=0),'extra_data_edges_capacity_model':0,'regional_edges':None,'physical_qualification':False}
(H/'model.json').write_text(json.dumps(out,indent=2)+'\n');(H/'assignments.json.gz').write_bytes(gzip.compress(json.dumps(assign,separators=(',',':')).encode(),mtime=0));(H/'positions.json.gz').write_bytes(gzip.compress(json.dumps([[n,k,v] for (n,k),v in positions.items()],separators=(',',':')).encode(),mtime=0))
print(json.dumps({k:v for k,v in out.items() if k not in ('changed','inputs','native_master_functions','library_sha256','point_model_over405','ff_families')},indent=2));print('FF_FAMILIES',json.dumps(dict(fam)));print('PASS full recursive graph capacity including source-D/reset/set/tie loads and parity')
assert rounds[0]<rounds[-1];print('REJECT firstpass',rounds[0],'vs',rounds[-1])
