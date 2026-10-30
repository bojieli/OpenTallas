"""Exploratory PHY topology feasibility only; no builder, placement, or signoff claim."""
import sys,json,re,math,gzip,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import clk_aocv as AO
import die_clock_128 as C
import core_infra_plan as P
W=Path(__file__).parent
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--choice',type=int,default=3);ap.add_argument('--library-dir',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--plan-out',type=Path);args=ap.parse_args()
if args.out.exists():raise FileExistsError('Use a new immutable estimate output path: '+str(args.out))
rows=json.load(gzip.open(W/'phy_sinks_SD.json.gz'))['sinks']
# ANALYTIC proposed RX group only, not a complete selected-root recipe.
# Real FF maxwidth1.134,rowheight.27, site.054. Existing PGfree E1883.52..1896.48.
# Entire selected root retained including TX subtree.
controls=[];moved=0
for r in rows:
 if r[0]!='ff':continue
 if '.p_tx_d' in r[1]:
  b=int(re.search(r'p_tx_d\\?\[(\d+)',r[1])[1]);r[-2:]=[1883.574,17.28+.27*(2*b+(5*b)//6)];continue
 if '.u_tx.' in r[1] or '.p_tx_' in r[1]:
  controls.append(r);continue
 m=re.search(r'rq_d\\?\[(\d+)',r[1])
 if m:bit=int(m[1]);slot=0
 else:
  m=re.search(r'u_rx.mem\\?\[(\d+)\\?\]\\?\[(\d+)',r[1])
  if not m:controls.append(r);continue
  slot=int(m[1])+1;bit=int(m[2])
 r[-2:]=[1883.574+slot*1.188,480.06+.27*(3*bit+(4*bit)//9)];moved+=1
for i,r in enumerate(controls):
 centre=216.27 if '.u_tx.' in r[1] or '.p_tx_' in r[1] else 722.25
 r[-2:]=[1883.574+(i%8)*1.566,centre-(i//8)*1.08]
print('RX group only: moved',moved,'bitFFs +',len(controls),'controlFFs')

points={str(i):r[-2:] for i,r in enumerate(rows)}
libs={c:C.lib_cells(c,args.library_dir,['BUFx24_ASAP7_75t_R']) for c in ('TT','FF')}
caps={c:{} for c in libs}
for c in libs:
 txt=(args.library_dir/f'asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib').read_text();cache={}
 for i,r in enumerate(rows):
  if r[0]=='macro':cap=50.
  else:
   m=r[2]
   if m not in cache:
    start=txt.index('cell ('+m+')');end=txt.find('\n  cell (',start+10);b=txt[start:end if end>0 else None]
    p=b.index('pin (CLK)');match=re.search(r'\b(?:rise_)?capacitance\s*:\s*([0-9.eE+-]+)',b[p:]);cache[m]=float(match[1])
   cap=cache[m]
  caps[c][str(i)]=cap
nodes=[]
def node(xy,children=None,sinks=None):
 k=len(nodes);nodes.append(dict(xy=xy,children=children or [],sinks=sinks or []));return k
def branch(ids,depth=0):
 xy=[sum(points[i][a] for i in ids)/len(ids) for a in (0,1)]
 if depth==8 or len(ids)==1:return node(xy,sinks=ids)
 axis=max((0,1),key=lambda a:max(points[i][a] for i in ids)-min(points[i][a] for i in ids));ids=sorted(ids,key=lambda i:points[i][axis]);m=len(ids)//2
 children=[branch(ids[:m],depth+1),branch(ids[m:],depth+1)];return node(xy,children=children)
entry=node([1895.4,354.]);root=node([1890.,469.26]);nodes[entry]['children']=[root];mi=next(str(i) for i,r in enumerate(rows) if r[0]=='macro');rxids=[str(i) for i,r in enumerate(rows) if r[0]!='macro' and '.p_tx_' not in r[1] and '.u_tx.' not in r[1]];txids=[i for i in points if i not in rxids and i!=mi];subrx=branch(rxids);subtx=branch(txids);nodes[root]['children']=[subrx,subtx]
# Macro load gets a dedicated branch independently of the FF tree partition.
# Start from nearest FF leaf's parent and enumerate existing ancestors as geometric electrical planner choices.
nearest=min((k for k,n in enumerate(nodes) if n['sinks'] and all(i in rxids for i in n['sinks'])),key=lambda k:sum(abs(nodes[k]['xy'][a]-points[mi][a]) for a in (0,1)))
par=next(k for k,n in enumerate(nodes) if nearest in n['children']);mk_new=node(points[mi],sinks=[mi]);nodes[par]['children'].append(mk_new)

# Per-master load class: the actual50fF PHY input gets its own same-depth driver,
# not a leaf with20FFs in addition. Geometry follows the actual pin, no delay pads.
for k,n in enumerate(list(nodes)):
 macro=[i for i in n['sinks'] if rows[int(i)][0]=='macro']
 if macro and len(n['sinks'])>1:
  n['sinks']=[i for i in n['sinks'] if i not in macro]
  for m in macro:
   alt=node(points[m],sinks=[m])
   parent=next(q for q in nodes if k in q['children']);parent['children'].append(alt)

# Actual BUFx24 width1.62: driver centres stay outside PHY/PG and inside core.
# Y row occupancy still needs legalizer; no placement gate is claimed.
for n in nodes:n['xy'][0]=max(1884.384,min(1895.616,n['xy'][0]))
# Geometry/load-class planner: macro clock may fork at an existing ancestor; no added pads.
choice=args.choice
mk=next(k for k,n in enumerate(nodes) if any(rows[int(i)][0]=='macro' for i in n['sinks']))
chain=[];cur=mk
while cur!=entry:
 parent=next(k for k,n in enumerate(nodes) if cur in n['children']);chain.append(parent);cur=parent
if choice>=len(chain):raise ValueError(('macro ancestor choice',choice,'available',len(chain)))
old=chain[0];nodes[old]['children'].remove(mk);new=chain[choice];nodes[new]['children'].append(mk)
print('macro forks at existingancestor',choice,'of',len(chain),'xy',nodes[new]['xy'])
# Minimum repeater count per shortest Manhattan edge; a wire bend is NOT a driver.
for n in list(nodes):
 ch=[]
 for kid in n['children']:
  a=n['xy'];b=nodes[kid]['xy'];dx=abs(b[0]-a[0]);dy=abs(b[1]-a[1]);length=dx+dy;segments=max(1,math.ceil(length/150));prev=None;first=None
  for z in range(1,segments):
   t=length*z/segments
   xy=[a[0]+(b[0]-a[0])*min(t/dx,1.) if dx else a[0],a[1]+(b[1]-a[1])*max(0.,(t-dx)/dy) if dy else a[1]]
   r=node(xy)
   if prev is not None:nodes[prev]['children']=[r]
   else:first=r
   prev=r
  if prev is not None:nodes[prev]['children']=[kid]
  ch.append(first if first is not None else kid)
 n['children']=ch
out={};leaf_models={k:{} for k,n in enumerate(nodes) if n['sinks']}
for c in libs:
 lib=libs[c]['BUFx24_ASAP7_75t_R'];arr={entry:0.};slew={entry:20.};todo=[entry];sinkarr={};maxslew=0.;worst=None;celld={};netd={};owner={}
 while todo:
  k=todo.pop();n=nodes[k];targets=[(str(ch),nodes[ch]['xy'],lib['cap'],ch) for ch in n['children']]+[(s,points[s],caps[c][s],None) for s in n['sinks']]
  if not targets:continue
  wire=P._mst_length([n['xy']]+[t[1] for t in targets]);load=sum(t[2] for t in targets);cw=wire*.17137*.9
  delay=C._bilin(lib['delay'],slew[k],cw+load);celld[k]=delay;tr=C._bilin(lib['trans'],slew[k],cw+load)
  for name,xy,cap,ch in targets:
   d=abs(xy[0]-n['xy'][0])+abs(xy[1]-n['xy'][1]);el=d*.018515*.8*(d*.17137*.9/2+cap);v=arr[k]+delay+el;sv=math.hypot(tr,2.2*el);
   if sv>maxslew:maxslew=sv;worst=dict(driver=k,driver_xy=n['xy'],target_xy=xy,wire_um=wire,cap_ff=cw+load,targetcap_ff=cap,targetdistance_um=d,arrival_ps=v)
   if ch is None:sinkarr[name]=v;owner[name]=k;netd[name]=el
   else:arr[ch]=v;slew[ch]=sv;netd[ch]=el;todo.append(ch)
 vals=list(sinkarr.values());macro=[sinkarr[str(i)] for i,r in enumerate(rows) if r[0]=='macro']
 
 
 for k in leaf_models:
  vv=[sinkarr[q] for q in nodes[k]['sinks']];leaf_models[k][c]=dict(min=min(vv),max=max(vv))
 rq=[sinkarr[str(i)] for i,r in enumerate(rows) if r[0]=='ff' and 'rq_d' in r[1]]
 macro_related=dict(rq_d_count=len(rq),rq_d_min_ps=min(rq) if rq else None,rq_d_max_ps=max(rq) if rq else None,max_abs_macro_pair_ps=max(abs(x-macro[0]) for x in rq) if rq else None)
 
 pairs=json.load(gzip.open(W/'phy_related_pairs.json.gz')); names={r[1]:str(i) for i,r in enumerate(rows)};pm=[];missing=set()
 for cap in pairs['captures']:
  if not cap['capture_in_root']:continue
  ck=names.get(cap['capture'])
  if ck is None:missing.add(cap['capture']);continue
  for ix in cap['source_indices']:
   sk=names.get(pairs['sources'][ix])
   if sk is None:missing.add(pairs['sources'][ix]);continue
   pm.append((abs(sinkarr[ck]-sinkarr[sk]),pairs['sources'][ix],cap['capture']))
 # Canonical approved AOCV table on actual noncommon cell/net delays only.
 T=AO.load(Path(AO.__file__).with_name('clk_aocv_table_g021.json'));scale={'TT':1.0485,'FF':1.0552}[c]
 parent={ch:k for k,n in enumerate(nodes) for ch in n['children']};paths={}
 for key,ow in owner.items():
  path=[ow]
  while path[-1] in parent:path.append(parent[path[-1]])
  paths[key]=path[::-1]
 cache={};bounds=[]
 for diff,sn,cn in pm:
  sk=names[sn];ck=names[cn];pa,pb=paths[sk],paths[ck];key=(owner[sk],owner[ck]);rev=(owner[ck],owner[sk])
  if key not in cache:
   depth=0
   while depth<min(len(pa),len(pb)) and pa[depth]==pb[depth]:depth+=1
   xa=pa[depth:];xb=pb[depth:];pts=[nodes[q]['xy'] for q in xa+xb]+[points[q] for q in nodes[owner[sk]]['sinks']+nodes[owner[ck]]['sinks']]
   dist=max(x[0] for x in pts)-min(x[0] for x in pts)+max(x[1] for x in pts)-min(x[1] for x in pts)
   def side(path):return dict(cell_ps=sum(celld[q] for q in path)*scale,net_ps=sum(netd[q] for q in path)*scale,stages={'A':len(path)})
   aa,bb=side(xa),side(xb)
   cache[key]=(aa,bb,dist)
  aa,bb,dist=cache[key];a=dict(aa,net_ps=aa['net_ps']+netd[sk]*scale);b=dict(bb,net_ps=bb['net_ps']+netd[ck]*scale)
  pes=max(AO.branch_pessimism(T,c,a,b,dist,True,ch) for ch in ('setup','hold'))
  bounds.append((diff*scale+pes,sn,cn,diff*scale,pes))
 aocv=dict(max_ps=max(x[0] for x in bounds),over80=sum(x[0]>80 for x in bounds),worst=sorted(bounds,reverse=True)[:3],spice_scale=scale,same_PDN_region=True,table='clk_aocv_table_g021.json',branch_pairs=len(cache))
 pairinfo=dict(pairs=len(pm),max_abs_ps=max(v[0] for v in pm),over80=sum(v[0]>80 for v in pm),over150=sum(v[0]>150 for v in pm),worst=sorted(pm,reverse=True)[:3],missing=len(missing))
 out[c]=dict(aocv=aocv,pairinfo=pairinfo,macro_related=macro_related,min_ps=min(vals),max_ps=max(vals),window_ps=max(vals)-min(vals),max_slew_ps=maxslew,macro_pin_ps=macro,worst_slew_net=worst)
result=dict(basis='Exploratory ASAP7 NLDM + same A0 Manhattan-MST/direct Elmore model, allBUFx24, repeaters<=150um, no timing measurements consumed; no legalization/PG/DRC performed',cells=len(nodes),sinks=len(rows),corners=out,verdict='NOT QUALIFIED',build_allowed=False)
if args.plan_out:
 if args.plan_out.exists():raise FileExistsError(args.plan_out)
 parent={ch:k for k,n in enumerate(nodes) for ch in n['children']};order=[];todo=[entry]
 while todo:
  k=todo.pop(0);order.append(k);todo.extend(nodes[k]['children'])
 name=lambda k:f'mp_phy_n{k}'
 clocknodes=[dict(name=name(k),parent=('port:clk_clk_phy[0]' if k==entry else name(parent[k])),master='BUFx24_ASAP7_75t_R',xy_um=nodes[k]['xy']) for k in order]
 leaves=[]
 for k in order:
  if not nodes[k]['sinks']:continue
  pins=[rows[int(q)][1]+('/clk' if rows[int(q)][0]=='macro' else '/CLK') for q in nodes[k]['sinks']]
  leaves.append(dict(node=name(k),load_class=('macro' if any(rows[int(q)][0]=='macro' for q in nodes[k]['sinks']) else 'register'),sinks=pins,pin_latency_ps=leaf_models[k]))
 corners={c:dict(leaf_min=r['min_ps'],leaf_max=r['max_ps'],leaf_window=r['max_ps']-r['min_ps'],slew_max=r['max_slew_ps']) for c,r in out.items()}
 ordinary=['clk','clk_t1','clk_t2','clk_t3','clk_t4','clk_t5','fclk_in_i_host_fdi[0]','fclk_in_i_host_link_rst_n[0]']
 tree=dict(clock_port='clk_clk_phy[0]',stage_basis='electrical_latency',latency_target_ps={c:(r['min_ps']+r['max_ps'])/2 for c,r in out.items()},nodes=clocknodes,leaves=leaves,equal_load=False,load_balance='joint_nldm_plan',root_scope=dict(ordinary_roots=ordinary,ordinary_cts_roots=ordinary[:6],clock_editor_roots={}),model_qualification=dict(measured_timing_used=False,electrical_latency_qualified=False,source='results/flow_secondary_phy_1030/candidate_clock_estimate.json',model='Actual ASAP7 NLDM + shortest Manhattan geometry; row/PG legalizer NOT RUN',band_policy='info',window_policy='info',corners=corners))
 proposed=dict(kind='ANALYSIS_ONLY_PHY_CLOCK_CANDIDATE',build_allowed=False,physical_qualification='NOT RUN',clock_entry_port_um=[1898.656,354.],suggested_core_tree=tree,selected_sink_positions_um={rows[int(q)][1]+('/clk' if rows[int(q)][0]=='macro' else '/CLK'):xy for q,xy in points.items()},pending=['legal row/PG/occupied-site placement','primary FIFO/clock capacity review','complete clock_entries and real per-editor root scopes','actual TX ring-bit data reach','G1 then routed TT/FF signoff'])
 write=gzip.open if args.plan_out.suffix=='.gz' else open
 with write(args.plan_out,'xt') as f:json.dump(proposed,f,indent=1)
json.dump(result,args.out.open('x'),indent=1)
print(json.dumps(result,indent=1))
