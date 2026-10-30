#!/usr/bin/env python3
"""Actual mirrored2746b scorer source corridors +30active metadata, with coherent fixed latency.
Diagnostic candidate only until G0/C, source transport, clock/CA and token contracts pass.
"""
import sys,json,copy,heapq,ast,os,math
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import schema as S;import lane_add as L;import station_resite as SR;import hub_repack as HR
import anchored_resite as A
base,nw,out=map(Path,sys.argv[2:5]);out.mkdir(parents=True,exist_ok=False)
r0=json.loads((base/'die_plan.json').read_text());raw=json.loads((nw/'die_plan.json').read_text())
# Reuse only the already measured pure graph helper functions, without a constructor's top-level side effects.
mod=ast.parse(Path(__file__).with_name('scorer_flow_anchored.py').read_text());fs=[x for x in mod.body if isinstance(x,ast.FunctionDef)and x.name in ('can_alloc','paths')]
ns=dict(L=L,heapq=heapq);exec(compile(ast.Module(body=fs,type_ignores=[]),'<capacity_paths>','exec'),ns)
B=L.Builder(raw,near_um=20000,max_hops=16,require_cycle_match=False,first_id=950);B.shared=set();A.install(B)
meta=None;attempts=[]
for chain in ns['paths'](B,30,src='NW_b100',dst='NW_b102'):
 meta=B.build_one('NW_b100','NW_b102',30,chain,'path',None,record=False);attempts.append(dict(chain=chain,why=None if meta else B._why))
 if meta:break
if not meta:raise SystemExit('active metadata cannot route: '+json.dumps(attempts))
raw=B.raw;W=float(raw['die']['outline_um'][0]);parts={p['name']:p for p in raw['partitions']};T=raw['partition_types']
newids=[x['id']for x in raw['lanes']if x['id']not in {z['id']for z in r0['lanes']}];P=S.Plan(raw)
mp=lambda s:'NE_'+s[3:] if s.startswith('NW_')else s
flip=lambda s:'lsb_high'if s=='lsb_low'else'lsb_low'
def mirror_geom(part,face,win,order):
 df,dw,lays,do=P.geom_to_die(part,(face,win,[],order));f2=L.OPP[df]if df in'EW'else df
 w2=[W-dw[1],W-dw[0]]if df in'NS'else dw;dieorder=flip(do)if df in'NS'else do
 tf,tw,f=L.to_type_window(P,mp(part),f2,w2)
 return tf,[round(x,4)for x in tw],flip(dieorder)if f else dieorder
rep=dict(metadata=meta,metadata_attempts=attempts,lanes_nw=newids,mirrored=[],slot_resites=[],reset_bit='OPEN native reset/START delivery, not payload')
seen=set()
for lid in newids:
 ln=P.lanes[lid]
 # Add only the declarations used by this lane at every endpoint/interior slot.
 decls=[]
 for q in ln['ports']:
  for side in ('src','dst'):
   e=P.ports[q][side];part,bus=e['part'],e['bus'];t=P.ptype(part)
   hit=[('buses',b)for b in t.get('buses',[])if b['name']==bus]
   if not hit:
    stem=bus[:-2];hit=[('ft_slots',x)for x in t.get('ft_slots',[])if x['name']==stem]
   assert len(hit)==1,(part,bus)
   decls.append((part,hit[0][0],hit[0][1]))
 for part,key,d in decls:
  np=mp(part);nt=T[parts[np]['type']];tag=(np,key,d['name'])
  if tag in seen:continue
  seen.add(tag);nd=copy.deepcopy(d)
  if key=='buses':nd['face'],nd['window_um'],nd['order']=mirror_geom(part,d['face'],d['window_um'],d.get('order','lsb_low'))
  else:
   for stem in ('in','out'):
    nd[stem+'_face'],nd[stem+'_window_um'],nd[stem+'_order']=mirror_geom(part,d[stem+'_face'],d[stem+'_window_um'],d.get(stem+'_order',d.get('order','lsb_low')))
   nd['regs_um']=[[round(x,4)for x in P.to_type(np,(W-P.to_die(part,tuple(q))[0],P.to_die(part,tuple(q))[1]))]for q in d['regs_um']]
  existing=[x for x in nt.get(key,[])if x['name']==nd['name']]
  if existing:
   assert len(existing)==1 and existing[0]==nd,('shared declaration differs',np,key,nd['name'])
  else:
   if key=='ft_slots':
    rects=SR.core_rects(nt)
    if any(SR.blocked(rects,q)for q in nd['regs_um']):
     free=HR.Raster(*nt['outline_um'],[x[1:]for x in rects]).f
     def fp(f,w):
      m=sum(w)/2.;ww,hh=nt['outline_um'];return {'N':(m,hh),'S':(m,0.),'E':(ww,m),'W':(0.,m)}[f]
     a=fp(nd['in_face'],nd['in_window_um']);b=fp(nd['out_face'],nd['out_window_um']);got=None
     old=nd['stations']
     for n in range(old,old+4):
      got=A.anchored_route(free,a,b,n,B.reach,B.reach/2.)
      if got is not None:break
     assert got is not None,('no mirrored homes',np,nd['name'])
     nd['regs_um']=got;nd['stations']=len(got);rep['slot_resites'].append(dict(part=np,slot=nd['name'],old=old,new=len(got)))
   nt.setdefault(key,[]).append(nd)
 # Ports have type-frame declarations; MY transforms pin order consistently for both endpoints.
 nln=copy.deepcopy(ln);nln['id']=lid+'m';nln['ports']=[];nln['note']='CODEX source-exact row1 corridors MY mirror '+lid
 for q in ln['ports']:
  pr=copy.deepcopy(next(z for z in raw['ports'] if z['id']==q));pr['id']=q+'m'
  for side in ('src','dst'):pr[side]['part']=mp(pr[side]['part'])
  raw['ports'].append(pr);nln['ports'].append(pr['id'])
 raw['lanes'].append(nln);rep['mirrored'].append(nln['id'])
for suffix,lanes in (('NW',newids),('NE',[x+'m'for x in newids])):
 raw.setdefault('latency_groups',[]).append(dict(name='scorer_row1_payload_'+suffix,kind='bus',lanes=lanes,note='2176 key +570 query/control +30 active metadata must arrive on one beat; reset separate'))
P=S.Plan(raw)
for lid in newids+[x+'m'for x in newids]:
 n=P.lane_natural(lid);raw['latency']['lanes'][lid]=dict(n,natural=n['cycles'],pad=0,param='LAT_'+lid.upper())
(out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(out/'pair_event_report.json').write_text(json.dumps(rep,indent=1)+'\n')
for f in base.iterdir():
 if f.name in ('die_plan.json','gen','lat','g0_report.json')or f.name.startswith('g0')or(out/f.name).exists():continue
 os.symlink(f.resolve(),out/f.name)
print(json.dumps(rep))
