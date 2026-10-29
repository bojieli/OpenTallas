#!/usr/bin/env python3
"""Deterministic HBM source-demand transport plan transform; never routes silicon.
Preserves existing lane payloads and appends source obligations in declared order.
New types are keyed by their complete interface, so identical types stay identical.
Run --geometry first to construct windows; --allocate regenerates all changed FT
sites and reports every actual lane latency delta. A failure is never a PASS.
"""
import argparse,collections,copy,hashlib,heapq,json,math,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('census');ap.add_argument('out');ap.add_argument('--tools',required=True);a=ap.parse_args()
sys.path.insert(0,a.tools);sys.path.insert(0,str(Path(a.tools).parents[1]));import schema as S
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
P=json.loads(Path(a.plan).read_text());C=json.loads(Path(a.census).read_text());actual_schema=C.get('schema')=='opentallas.hbm.source_transport_census.v1'
if actual_schema:
 boot=[b for r in C['pairs'] for b in r['drivers'] if b.get('lane')=='HOST_BOOT' and not b.get('unplanned')]
 if boot:
  assert len(boot)==320 and {b['bit_index'] for b in boot}==set(range(320)), 'HOST_BOOT bit inventory'
  assert all(b['driver']=='u_host_boot_hop24' and b['port']=='q' for b in boot), 'HOST_BOOT reserved-payload violation'
 C={'pairs':[dict(src=r['src'],dst=r['dst'],bits=r['unplanned_bits'],drivers=[b for b in r['drivers'] if b['unplanned']]) for r in C['pairs'] if r.get('unplanned_bits',0)]}
old=S.Plan(copy.deepcopy(P));parts={p['name']:p for p in P['partitions']};types=P['partition_types'];ports={p['id']:p for p in P['ports']};lanes={l['id']:l for l in P['lanes']}
report=dict(schema='opentallas.hbm_transport_candidate.v1',status='CONSTRUCTING',source_plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),source_census_sha256=hashlib.sha256(Path(a.census).read_bytes()).hexdigest(),allocations=[],edges=[],changed_types={},ft=[],internal=[],failures=[],latency=[],source_bits_status='EXACT_UNPLANNED_BITMAP' if actual_schema else 'AGGREGATED_COUNTS_ONLY_PENDING_ACTUAL_BITMAP')
for pr in P['ports']:
 for key in ('face','layers','window_um','order'):
  if key not in pr and key in old.ports[pr['id']]:pr[key]=copy.deepcopy(old.ports[pr['id']][key])
# Copy each affected instance's template before changes; never mutate a shared type
# for an instance whose transport contract remains unchanged.
worktypes={};original_types={};changed=set();edges=set();changed_buses=collections.defaultdict(set)
def typ(part):
 if part not in worktypes:
  tn=parts[part]['type'];original_types[part]=tn;nn='__transport_'+part;types[nn]=copy.deepcopy(types[tn]);worktypes[part]=nn;parts[part]['type']=nn
 return types[worktypes[part]]
def rect(n):return old.rect(n)
def shared(s,d):
 A,B=rect(s),rect(d)
 if abs(A[2]-B[0])<.6 or abs(A[0]-B[2])<.6:
  return ('E' if A[0]<B[0] else 'W'),max(A[1],B[1]),min(A[3],B[3])
 if abs(A[3]-B[1])<.6 or abs(A[1]-B[3])<.6:
  return ('N' if A[1]<B[1] else 'S'),max(A[0],B[0]),min(A[2],B[2])
 raise ValueError(f'nonabutted {s}|{d}')
def endpoint(part,bus,width,window,df,layers,direction,slot=False):
 t=typ(part);changed.add(part);changed_buses[part].add(bus)
 # Die/type orientations are involutions, with face coordinate reversal.
 tf=old.type_face(part,df);ori=parts[part].get('orient','R0');axis=1 if tf in 'EW' else 0;lo,hi=window;lo-=parts[part]['origin_um'][axis];hi-=parts[part]['origin_um'][axis]
 if ori in (('MX','R180') if tf in 'EW' else ('MY','R180')):lo,hi=t['outline_um'][axis]-hi,t['outline_um'][axis]-lo
 order='lsb_high' if ori in (('MX','R180') if tf in 'EW' else ('MY','R180')) else 'lsb_low'
 bn=next((b for b in t.get('buses',[]) if b['name']==bus),None)
 if bn is not None:bn.update(width=width,face=tf,window_um=[round(lo,6),round(hi,6)],layers=layers,order=order);return
 sl=next((s for s in t.get('ft_slots',[]) if bus in (s['name']+'_i',s['name']+'_o')),None)
 if sl is not None:
  stem='in' if bus.endswith('_i') else 'out';sl.update(width=width);sl[stem+'_face']=tf;sl[stem+'_window_um']=[round(lo,6),round(hi,6)];sl[stem+'_layers']=layers;sl[stem+'_order']=order
  for k in ('bit_sites_um','bit_site_cell_um'):sl.pop(k,None)
  return
 if slot:raise RuntimeError(f'missing new FT slot {part}/{bus}')
 t.setdefault('buses',[]).append(dict(name=bus,dir=direction,width=width,kind='data',face=tf,window_um=[round(lo,6),round(hi,6)],layers=layers,order=order))
def edge_fit(s,d,nb,existing=None):
 try:df,lo,hi=shared(s,d)
 except ValueError:return False
 if hi-lo<20:return False
 ls=['M6','M4'] if df in 'EW' else ['M7','M5'];cursor=math.ceil((lo+.08)/.016)*.016
 pp=[p for p in P['ports'] if {p['src']['part'],p['dst']['part']}=={s,d}]
 pp.sort(key=lambda p:(sum(p['window_um'])/2,p['id']))
 widths=[S.port_pins_count(p)+(nb if p['id']==existing else 0) for p in pp]
 if existing is None:widths.append(nb+1)
 if sum(widths)>6*(hi-lo):return False
 for n in widths:
  cursor=S.window_for(cursor,n,ls,layers=old.layers,per_um=6.,track_max=.6)+.08
  if cursor>hi-.08:return False
 return True
def shortest(s,d,nb):
 dist={s:0.};prev={};q=[(0.,s)]
 while q:
  cost,u=heapq.heappop(q)
  if u==d:break
  if cost!=dist[u]:continue
  A=rect(u);ca=((A[0]+A[2])/2,(A[1]+A[3])/2)
  for v in sorted(parts):
   if u==v:continue
   try:f,lo,hi=shared(u,v)
   except ValueError:continue
   if hi-lo<20 or not edge_fit(u,v,nb):continue
   B=rect(v);cb=((B[0]+B[2])/2,(B[1]+B[3])/2);cc=cost+abs(ca[0]-cb[0])+abs(ca[1]-cb[1])
   if cc<dist.get(v,math.inf):dist[v]=cc;prev[v]=u;heapq.heappush(q,(cc,v))
 if d not in dist:raise ValueError(f'no abutted path {s}->{d}')
 path=[d]
 while path[-1]!=s:path.append(prev[path[-1]])
 return path[::-1]
try:
 for ix,r in enumerate(sorted(C['pairs'],key=lambda r:(r['src'],r['dst']))):
  s,d,nb=r['src'],r['dst'],int(r['bits']);assert nb>0
  candidates=[l for l in P['lanes'] if ports[l['ports'][0]]['src']['part']==s and ports[l['ports'][-1]]['dst']['part']==d]
  if candidates:
   candidates=[l for l in candidates if all(edge_fit(ports[pid]['src']['part'],ports[pid]['dst']['part'],nb,existing=pid) for pid in l['ports'])]
  if candidates:
   l=max(candidates,key=lambda l:(min(ports[p]['width'] for p in l['ports']),l['id']));base=min(ports[p]['width'] for p in l['ports']);width=base+nb
   for pid in l['ports']:
    pr=ports[pid];assert pr['width']==base,(l['id'],'nonuniform prior width');pr['width']=width;edges.add(tuple(sorted((pr['src']['part'],pr['dst']['part']))))
   path=[ports[l['ports'][0]]['src']['part']]+[ports[pid]['dst']['part'] for pid in l['ports']]
  else:
   lid=f'TR{ix:03d}';assert lid not in lanes;path=shortest(s,d,nb);l=dict(id=lid,ports=[],note=f'Actual-source transport {s}->{d}; source-census {report["source_census_sha256"][:12]}');width=nb;base=0
   for j,part in enumerate(path[1:-1],1):
    t=typ(part);t.setdefault('ft_slots',[]).append(dict(name=lid+f'x{j}',width=width,stations=1,in_face='W',out_face='E',in_window_um=[0,1],out_window_um=[0,1],in_layers=['M6','M4'],out_layers=['M6','M4']))
   for j,(u,v) in enumerate(zip(path,path[1:])):
    pid=lid+f'_{j}';f,lo,hi=shared(u,v);ls=['M6','M4'] if f in 'EW' else ['M7','M5']
    pr=dict(id=pid,src=dict(part=u,bus=lid+'_o' if j==0 else lid+f'x{j}_o'),dst=dict(part=v,bus=lid+'_i' if j==len(path)-2 else lid+f'x{j+1}_i'),width=width,kind='data',face=f,layers=ls,window_um=[lo,hi]);ports[pid]=pr;P['ports'].append(pr);l['ports'].append(pid);edges.add(tuple(sorted((u,v))))
   P['lanes'].append(l);lanes[lid]=l
  rr=dict(src=s,dst=d,bits=nb,lane=l['id'],base_bit=base,new_width=width,path=path,drivers=r.get('drivers',{}));
  if actual_schema:
   assert len(r['drivers'])==nb,(s,d,'actual bitmap cardinality')
   rr['drivers']=[dict(b,assigned_lane=l['id'],assigned_lane_bit=base+j) for j,b in enumerate(r['drivers'])]
  report['allocations'].append(rr)
 # Repack both ends of an abutment in one die frame, with exact technology PG-track
 # supply. Preserve the previous bus ordering and make every bit align at the seam.
 for s,d in sorted(edges):
  df,lo,hi=shared(s,d);ps=[p for p in P['ports'] if {p['src']['part'],p['dst']['part']}=={s,d}];ps.sort(key=lambda p:(sum(p['window_um'])/2,p['id']));cursor=math.ceil((lo+.08)/.016)*.016
  for pr in ps:
   lays=['M6','M4'] if df in 'EW' else ['M7','M5'];end=S.window_for(cursor,S.port_pins_count(pr),lays,layers=old.layers,per_um=6.,track_max=.6)
   if end>hi-.08:raise ValueError(f'edge {s}|{d} lacks legal track/window supply: requires{end-lo:.3f}um available{hi-lo:.3f}um')
   f,_,_=shared(pr['src']['part'],pr['dst']['part']);pr.update(face=f,layers=lays,window_um=[round(cursor,6),round(end,6)]);pr.pop('segments',None)
   for side in ('src','dst'):
    ep=pr[side];endpoint(ep['part'],ep['bus'],pr['width'],pr['window_um'],f if side=='src' else S.OPP[f],lays,'out' if side=='src' else 'in')
   cursor=end+.08
  report['edges'].append(dict(parts=[s,d],span_um=hi-lo,used_um=cursor-lo,ports=len(ps),pins=sum(S.port_pins_count(p) for p in ps)))
 # Legacy slots often infer their opposite window from die ports. Materialize
 # both ends before allocation, without classifying unchanged windows as moved.
 saved_changed={p:set(v) for p,v in changed_buses.items()}
 for pr in P['ports']:
  for side in ('src','dst'):
   ep=pr[side]
   if ep['part'] not in worktypes:continue
   df=pr['face'] if side=='src' else S.OPP[pr['face']]
   endpoint(ep['part'],ep['bus'],pr['width'],pr['window_um'],df,pr['layers'],'out' if side=='src' else 'in')
 changed_buses.clear();changed_buses.update(saved_changed)
 # Full new/changed FT geometry invalidates every affected explicit-site seed.
 for part in sorted(changed):
  t=types[parts[part]['type']];w,h=t['outline_um']
  for sl in t.get('ft_slots',[]):
   if sl['name']+'_i' not in changed_buses[part] and sl['name']+'_o' not in changed_buses[part]:continue
   def mid(face,win):
    q=sum(win)/2;return {'W':(0,q),'E':(w,q),'S':(q,0),'N':(q,h)}[face]
   aa=mid(sl['in_face'],sl['in_window_um']);bb=mid(sl['out_face'],sl['out_window_um']);prior=int(sl['stations']);sl['stations']=max(prior,math.ceil((abs(aa[0]-bb[0])+abs(aa[1]-bb[1]))/360.))
   for k in ('bit_sites_um','bit_site_cell_um','regs_um'):sl.pop(k,None)
  t['note']=t.get('note','')+' | deterministic actual-source transport candidate; changed FT sites require fresh allocation'
  report['changed_types'][part]=dict(old=original_types[part],temporary=parts[part]['type'],buses=sorted(changed_buses[part]),old_wrapper_transport_ff=sum(b['width']+1 for b in old.ptype(part).get('buses',[]))+sum((s['width']+1)*s['stations'] for s in old.ptype(part).get('ft_slots',[])))
 P['note']=P.get('note','')+' | source-demand transport candidate; not adopted'
 model=S.Plan(P)
 for l in P['lanes']:
  row=model.lane_latency(l['id']);prior=old.raw.get('latency',{}).get('lanes',{}).get(l['id']);row['param']='LAT_'+l['id'].upper();P['latency']['lanes'][l['id']]=row
  if prior is None or row['cycles']!=prior['cycles']:report['latency'].append(dict(lane=l['id'],old=None if prior is None else prior['cycles'],new=row['cycles'],added=row['cycles']-(prior['cycles'] if prior else 0)))
 report['status']='GEOMETRY_CANDIDATE_NO_FT_SITES'
 (out/'die_plan.json').write_text(json.dumps(P,separators=(',',':'))+'\n')
except Exception as e:
 report['status']='FAIL';report['failures'].append(f'{type(e).__name__}: {e}');raise
finally:(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
