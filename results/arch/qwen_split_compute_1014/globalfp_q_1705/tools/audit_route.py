import sys,json,math,heapq,copy,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,'/home/ubuntu/artifacts/globalfp/qwen/recovery-1325/recovered-source');import gfp_core as C
C.REACH=500;C.TILE_MASTERS=('qfd_tile_nk','qfd_tile_nl')
p=Path(sys.argv[1]);md=json.load(open(p/'route-metadata.json'));inp=open(p/'route.in');nx,ny,B,E,K=inp.readline().split();nx=int(nx);ny=int(ny);E=int(E);K=int(K);B=float(B);edges=[]
for _ in range(E):
 u,v,cap,occ=inp.readline().split();edges.append((int(u),int(v),int(cap),float(occ)))
accepted=float(sys.argv[4]) if len(sys.argv)>4 else .55;used=np.zeros(E,dtype=np.int64);out=open(p/'route.out');out.readline();busmax=[0.]*len(md['buses']);buswire=[0.]*len(md['buses']);fail=[];netpaths=[];x=md['grid_centers_x'];y=md['grid_centers_y']
def xy(q):return x[q//ny],y[q%ny]
def leng(u,v):a,b=xy(u),xy(v);return abs(a[0]-b[0])+abs(a[1]-b[1])
for k,net in enumerate(md['nets']):
 z=list(map(int,out.readline().split()));assert z[0]==k and z[1]==len(z)-2;es=z[2:];adj={};assert len(es)==len(set(es))
 for ei in es:
  u,v,cap,occ=edges[ei];used[ei]+=net['bits'];adj.setdefault(u,[]).append((v,leng(u,v)));adj.setdefault(v,[]).append((u,leng(u,v)))
 root=net['terms'][0];ds={root:0.};pq=[(0.,root)]
 while pq:
  dv,u=heapq.heappop(pq)
  if dv!=ds[u]:continue
  for v,w in adj.get(u,[]):
   vv=dv+w
   if vv<ds.get(v,1e99):ds[v]=vv;heapq.heappush(pq,(vv,v))
 if any(q not in ds for q in net['terms']):fail.append({'net':k,'bus':md['buses'][net['rid']]['bus'],'unconnected':[q for q in net['terms'] if q not in ds]})
 pathmax=max((ds.get(q,1e99)+net['max_endpoint_stub_um'][0]+net['max_endpoint_stub_um'][j] for j,q in enumerate(net['endpoint_nodes'])),default=0.)
 busmax[net['rid']]=max(busmax[net['rid']],pathmax);buswire[net['rid']]+=net['bits']*(sum(leng(edges[e][0],edges[e][1]) for e in es)+sum(net['max_endpoint_stub_um']))
 netpaths.append({'net':k,'root_to_sink_upper_um':round(pathmax,6),'tree_edges':len(es)})
assert out.readline().strip()=='USES'
for e in range(E):z=list(map(int,out.readline().split()));assert z[0]==e and z[1]==used[e] and z[2]==edges[e][2]
rat=[];over=[]
for e,(u,v,cap,occ) in enumerate(edges):
 full=md['edge_metadata'][e][6];r=used[e]/full if full else(0 if not used[e] else 1e99);rat.append(r)
 if used[e]>math.floor(full*accepted+1e-8):over.append({'edge':e,'used':int(used[e]),'allocated_cap':cap,'physical_model_util':r})
for net in md['local_groups']:
 buswire[net['rid']]+=net['bits']*sum(net['max_endpoint_stub_um']);busmax[net['rid']]=max(busmax[net['rid']],max(net['max_endpoint_stub_um'][0]+v for v in net['max_endpoint_stub_um']))
source=Path(sys.argv[2]);die=C.Die(source);C.attach_ports(die);h=json.load(open(sys.argv[3]));m=copy.deepcopy(die.base)
for n,v in h['homes'].items():
 for k in ('x','y','o'):m[n][k]=v[k]
ev=[C.bus_geom(r,m) for r in die.recs];pev=[];rows=[];beforeff=afterff=0;pinwire=sum(e[0] for e in ev)
for k,r in enumerate(die.recs):
 a=ev[k];L=max(a[1],busmax[k]);b=list(a);b[1]=L;pev.append(b);sf=C.stages(L);sb=C.stages(a[1]);beforeff+=(sb-1)*r['n'];afterff+=(sf-1)*r['n'];rows.append({'bus':r['b'],'bits':r['n'],'pin_pair_max_um':round(a[1],6),'planned_tree_plus_stubs_max_um_upper':round(L,6),'pin_pair_ideal500_stages':sb,'planned_ideal500_stages_upper':sf,'extra_ideal_relay_ff_upper':(sf-sb)*r['n'],'planned_bundle_wire_bit_um_upper':round(buswire[k],6)})
me=C.me_loop(die,m,pev);beforeme=C.me_loop(die,m,ev);worst=sorted(range(E),key=lambda e:-rat[e])[:20];nbit=sum(n['bits'] for n in md['nets'])+sum(n['bits'] for n in md['local_groups']);assert nbit==md['total_source_bus_bits'];rank=sorted(rows,key=lambda r:-r['extra_ideal_relay_ff_upper'])
report={'source_graph_sha256':md['source_graph_sha256'],'source_model_sha256':md['source_model_sha256'],'candidate':md['candidate'],'allocation_target':accepted,'search_target':md['allocation_target'],'physical_gate':md['physical_gate'],'desired_margin_target':.55,'under_margin_target':bool(max(rat)<=.55),'under_physical_gate':bool(max(rat)<=md['physical_gate']),'capacity_model':md['actual_global_layers'],'phy_overmacro_capacity':md['phy_overmacro_routing_capacity'],'grid_um':B,'routed_nonlocal_bundles':K,'local_bundles':len(md['local_groups']),'all_source_bus_bits_represented':nbit,'missing_pin_buses':md['source_pins_missing'],'disconnected_bundles':fail,'allocated_cut_overflows':over,'all_allocated_grid_cuts_under_target':not over and not fail,'worst_grid_cut_util':float(max(rat)),'routed_tree_me_stage_upper':me,'pin_pair_me_stage_model':beforeme,'data_pin_pair_relay_ff':beforeff,'data_planned_relay_ff_upper':afterff,'relay_budget_interpretation':'Geometric500um hop budget only; actualFF inventory can be larger due measuredreach, tree/equalagepads and legal-frame detours. Not an upperbound on actual implementation.','extra_data_relay_ff_upper':afterff-beforeff,'extra_relay_area_model_mm2_upper':(afterff-beforeff)/26*74.65/1e6,'top_extra_ff_buses':rank[:25],'worst_cuts':[{'edge':e,'window':md['edge_metadata'][e],'demand_bits':int(used[e]),'utilization':rat[e]} for e in worst],'qualified':False,'scope':'Independent replay of every edge route and every source bundle, exact rectangle-union grid-window capacity under listed actual-layer/worstPG assumptions. Not actual GRT, signal detailed routing, physical-clock or relay placement proof.','open':['NonPHY overmacroM8/M9 requires actualmasterOBS top<=7; actualexport still required.','Finite-grid aggregate edge allocation; pin-access within cells, layerassignment, vias and finer/sliding cut windows unproved.','Samecell local interconnect and stubs stay inside respective grid cells; their fine local cut/via demand must be checked.','Every routed length includes conservative endpoint stub bounds.500um stage counts are geometry budgets, not measuredregisteredpin reach.','RelayFF count is an ideal geometric budget only; legal relay frames, ownership, regional roots and phase not placed.','Allcapacity figures are afteractualM2-M5zeroing and actualsource worst-presentregionalPG+via reduction, but unknownOBS cannot be waived.']};(p/'route-audit.json').write_text(json.dumps(report,indent=2)+'\n');(p/'all-bus-route-costs.json').write_text(json.dumps(rows,indent=2)+'\n');(p/'net-path-bounds.json').write_text(json.dumps(netpaths,separators=(',',':'))+'\n');print({k:report[k] for k in ['candidate','routed_nonlocal_bundles','all_source_bus_bits_represented','worst_grid_cut_util','all_allocated_grid_cuts_under_target','data_planned_relay_ff_upper','extra_data_relay_ff_upper','extra_relay_area_model_mm2_upper']});print('ME',beforeme['me_loop'],me['me_loop'])
