import odb,sys,json,collections,hashlib,gzip,re
from pathlib import Path
src,summary,rowsfile,out=map(Path,sys.argv[1:]);d=json.loads(summary.read_text());roles=d['master_roles'];rows=json.loads(rowsfile.read_text());db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();insts={i.getName():i for i in b.getInsts()};points={};net_drivers=collections.defaultdict(list);pins={};pg=collections.Counter();pgsamples=[]
def point(p):
 r=p.getBBox();return [(r.xMin()+r.xMax())/(2*u),(r.yMin()+r.yMax())/(2*u)]
for i in b.getInsts():
 mn=i.getMaster().getName()
 for p in i.getITerms():
  mt=p.getMTerm();key=i.getName()+'/'+mt.getName();n=p.getNet();points[key]=point(p);pins[key]=p
  if str(mt.getSigType()) in ['POWER','GROUND']:
   if n is None or str(n.getSigType()) not in ['POWER','GROUND']:
    prot=i.isDoNotTouch() if hasattr(i,'isDoNotTouch') else 'UNKNOWN_API';st=str(i.getPlacementStatus());kind='macro' if i.getMaster().isBlock() else 'standard';why='empty_net' if n is None else 'wrong_net_role';k=(mn,kind,str(prot),st,why);pg[k]+=1
    if len(pgsamples)<30:pgsamples.append({'iterm':key,'master':mn,'kind':kind,'protected':prot,'placement_status':st,'net':n.getName() if n else None,'why':why})
   continue
  if n and str(mt.getIoType())=='OUTPUT':net_drivers[n.getId()].append(key)
for p in b.getBTerms():
 n=p.getNet();key='PORT/'+p.getName();points[key]=point(p)
 if n and str(p.getIoType())=='INPUT':net_drivers[n.getId()].append(key)
errors=[];memo={}
def upstream(n,seen=()):
 if n is None:return []
 nid=n.getId()
 if nid in memo:return memo[nid]
 if nid in seen:errors.append('comb_cycle:'+n.getName());return []
 result=[]
 for key in net_drivers[nid]:
  if key.startswith('PORT/'):
   result.append({'pin':key,'kind':'input_port','xy_um':points[key]});continue
  p=pins[key];i=p.getInst();mn=i.getMaster().getName();role=roles.get(mn)
  if i.getMaster().isBlock():result.append({'pin':key,'kind':'hardmacro_output_boundary_semantics_unqualified','xy_um':points[key]});continue
  if role is None:errors.append('unknown_master:'+mn);continue
  if role['sequential']:result.append({'pin':key,'kind':'actual_lib_sequential_output','xy_um':points[key]});continue
  fn=role['pins'][p.getMTerm().getName()].get('function')
  if fn is None:errors.append('missing_function:'+key);continue
  names=set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*',fn))
  if not names:continue
  for pn in names:
   ip=i.findITerm(pn)
   if ip is None:errors.append('missing_actual_input:'+key+':'+pn);continue
   result.extend(upstream(ip.getNet(),seen+(nid,)))
 memo[nid]=list({x['pin']:x for x in result}.values());return memo[nid]
models=[]
for r in rows:
 if r['max_L1_pin_centers_um']<=405 or not roles.get(r['master'],{}).get('sequential'):continue
 qkey=r['driver'];qp=pins[qkey];i=qp.getInst();dp=i.findITerm('D')
 if dp is None:errors.append('bad_root_no_D:'+qkey);continue
 q=points[qkey];dd=point(dp);offset=[dd[k]-q[k] for k in range(2)];sources=upstream(dp.getNet());sinks=[{'pin':k,'xy_um':points[k]} for k in r['endpoints'] if k in points];missing=[k for k in r['endpoints'] if k not in points];constraints=[s['xy_um'] for s in sinks]+[[s['xy_um'][k]-offset[k] for k in range(2)] for s in sources];loU=loV=-float('inf');hiU=hiV=float('inf')
 for x,y in constraints:loU=max(loU,x+y-405);hiU=min(hiU,x+y+405);loV=max(loV,x-y-405);hiV=min(hiV,x-y+405)
 clocks=[]
 for p in i.getITerms():
  rp=roles[r['master']]['pins'].get(p.getMTerm().getName(),{})
  if rp.get('clock'):clocks.append({'pin':p.getMTerm().getName(),'net':p.getNet().getName() if p.getNet() else None})
 feasible=loU<=hiU and loV<=hiV;models.append({'driver':qkey,'master':r['master'],'Q_xy_um':q,'D_xy_um':dd,'clock_pins':clocks,'placement_status':str(i.getPlacementStatus()),'protected':i.isDoNotTouch() if hasattr(i,'isDoNotTouch') else 'UNKNOWN_API','input_D_actual_full_comb_origins':sources,'all_actual_transparent_output_endpoints':sinks,'unresolved_output_endpoints':missing,'original_worst_output_L1_um':r['max_L1_pin_centers_um'],'geometric_only_Q_diamond_intersection_uv_um':[loU,loV,hiU,hiV],'geometric_intersection_nonempty':feasible,'minimum_geometric_root_L1_shift_um':max(0,loU-(q[0]+q[1]),q[0]+q[1]-hiU,loV-(q[0]-q[1]),q[0]-q[1]-hiV) if feasible else None})
out.mkdir(exist_ok=True)
s={'scope':'READONLY actualGRT PG status classes and failed sequential-output driver placement model. Source-D origins traverse complete actual Liberty Boolean input dependencies; output endpoints traverse original native unary unions. Hardmacro output boundary semantics explicitly UNQUALIFIED. Geometric diamond intersection necessary only: no legal placement/density/clock/reset/pinface/newstage or global feasible claim. No source/layout edits or global_connect applied.','odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'input_summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'PG_unbound_classes':[{'master':k[0],'kind':k[1],'protected':k[2],'placement_status':k[3],'why':k[4],'iterms':v} for k,v in pg.items()],'PG_unbound_total':sum(pg.values()),'PG_samples':pgsamples,'sequential_bad_roots_modeled':len(models),'geometric_nonempty_roots':sum(x['geometric_intersection_nonempty'] for x in models),'role_or_trace_errors':sorted(set(errors)),'worst10':sorted(models,key=lambda x:-x['original_worst_output_L1_um'])[:10]}
(out/'cause_summary.json').write_text(json.dumps(s,indent=2)+'\n')
with gzip.open(out/'stage_placement_models.json.gz','wt') as f:json.dump(models,f)
print(json.dumps({k:v for k,v in s.items() if k in ['PG_unbound_total','PG_unbound_classes','sequential_bad_roots_modeled','geometric_nonempty_roots','role_or_trace_errors']}))
