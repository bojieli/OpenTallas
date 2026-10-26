# Routed-detour stage model: per bus L = pin-pair length + worst routed detour (tree depth - grid Manhattan, x grid),
# which removes the grid-quantization/endpoint-stub inflation of audit_route's conservative upper bound.
import sys,json,copy,collections
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/artifacts/globalfp/qwen/recovery-1325/recovered-source');import gfp_core as C
C.REACH=500;C.TILE_MASTERS=('qfd_tile_nk','qfd_tile_nl')
rd=Path(sys.argv[1]);outp=Path(sys.argv[2]);G=Path(sys.argv[3]);homes=sys.argv[4]
md=json.load(open(rd/'route-metadata.json'));ny=md['ny'];B=md['grid_um']
inp=open(rd/'route.in');nx_,ny_,B_,E,K=inp.readline().split();E=int(E);edges=[tuple(map(int,inp.readline().split()[:2])) for _ in range(E)]
f=open(outp);f.readline();det=collections.defaultdict(float)
for k,net in enumerate(md['nets']):
 z=list(map(int,f.readline().split()));adj=collections.defaultdict(list)
 for e in z[2:]:u,v=edges[e];adj[u].append(v);adj[v].append(u)
 r=net['terms'][0];ds={r:0};q=[r]
 for u in q:
  for v in adj[u]:
   if v not in ds:ds[v]=ds[u]+1;q.append(v)
 dd=max(ds[t]-(abs(t//ny-r//ny)+abs(t%ny-r%ny)) for t in net['endpoint_nodes'])
 det[net['rid']]=max(det[net['rid']],dd*B)
die=C.Die(G);C.attach_ports(die);m=copy.deepcopy(die.base)
for n,v in json.load(open(homes))['homes'].items():
 for k in 'xyo':m[n][k]=v[k]
ev=[C.bus_geom(r,m) for r in die.recs];rev=[]
ff0=ff1=0;regress=[]
for k,r in enumerate(die.recs):
 a=list(ev[k]);L0=a[1];a[1]=L0+det.get(k,0.);rev.append(a);s0=C.stages(L0);s1=C.stages(a[1]);ff0+=(s0-1)*r['n'];ff1+=(s1-1)*r['n']
 if s1>s0:regress.append((r['b'],r['n'],s0,s1,round(det[k])))
me0=C.me_loop(die,m,ev);me1=C.me_loop(die,m,rev);ll0=C.layer_loops(die,ev);ll1=C.layer_loops(die,rev)
ex=lambda me,ll:C.ME_OPS*me['me_loop']+C.ARS*ll['coll_loop']+C.LAYERS*ll['kv_loop']
regress.sort(key=lambda x:-(x[3]-x[2])*x[1])
res={'route':str(outp),'pin_pair':{**{k:me0[k] for k in('bd','red','red_tree','red_transport','vm_to_tap','me_loop')},**ll0,'exposed_stage_cycles_per_token':ex(me0,ll0),'relay_ff':ff0},
 'routed_detour':{**{k:me1[k] for k in('bd','red','red_tree','red_transport','vm_to_tap','me_loop')},**ll1,'exposed_stage_cycles_per_token':ex(me1,ll1),'relay_ff':ff1,'relay_area_mm2':round(ff1/26*74.65/1e6,3)},
 'routed_me_path':{'bd_tail':me1['bd_path_tail'],'red_from':me1['red_from_tile'],'red_path':me1['red_path']},
 'stage_regressed_buses':len(regress),'top_regressions':regress[:15]}
(Path(outp).parent/'me-detour.json').write_text(json.dumps(res,indent=1));print(json.dumps({k:res[k] for k in('pin_pair','routed_detour','stage_regressed_buses')}))
