import copy,json,sys
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'src/tools/die_plan'))
import schema as S,reset_tree as RT,count_align_bind as CAB,taps
# PROPOSAL ONLY: solve tree geometry, never claim density-budget qualification.
RT._S_TAP_GRID=lambda P,tn: taps.explicit_tap_sites(P,tn) if P.types[tn].get('clock',{}).get('tap_mode')=='explicit' else S.tap_grid(P,tn)
raw=json.load(open(r/'plan_of_record/plan_c_sd_coherent_safe.json'));old=copy.deepcopy(raw)
sc=json.load(open(r/'bindbase/kv40/eW_sidecar_sd_coherent_safe.json'))
trial=json.load(open('/srv/opentallas-scratch2/claude/die-kv-43-1030/sd43/kitplan_sd44.json'))
selected=('kv3_sys_SD','kv3_sys_SD_v1')
for d in trial['die']['pg']['domains']:
 if 'serdes' in d['name']:
  d=copy.deepcopy(d)
  if 'SW' in d['name']:d['rect_um'][2]=1870.56
  elif 'SE' in d['name']:d['rect_um'][0]=9205.92
  else:raise ValueError(d['name'])
  raw['die']['pg']['domains'].append(d)
for tn in selected:
 t=raw['partition_types'][tn];ck=t['clock'];lc=ck['landing_contract']
 ck['taps']=[{'name':'clk' if i==0 else 'clk_t'+str(i),'xy':[x,21.6]} for i,x in enumerate([190.56,570.72,949.92,1331.04,1711.2])]+[{'name':'clk_t5','xy':[1874.88,160.0]},{'name':'clk_t6','xy':[1874.88,640.0]}]
 for p in lc['pins']:
  if p.get('source_clock_tap')=='clk_t4':p['source_clock_tap']='clk_t6'
 t['reset']['local_taps_um']=[[1872.72 if x>1800 else x,y] for x,y in t['reset']['local_taps_um']]
 # Remove stale source-derived collector data before rebuilding the actual tree.
 for key in ['collector_tree','collector_root_node','collector_local_sources','collector_children']:lc.pop(key,None)
 lc.pop('ring_place',None)
 lc['bands']['i_host_fdi']['rect_um']=[1877.04,149.904,1896.48,329.184]
 lc['bands']['i_host_link_rst_n']['rect_um']=[1877.04,438.48,1896.48,462.24]
 for b in lc['bands'].values():b['ring_place']='ff';b['placement']='CODEX SD R6W7 unadopted FF-only E-bank; actual legality/reach/G1 pending'
P=S.Plan(raw,str(r/'plan_of_record/plan_c_sd_r6w7_candidate.json'));receipt={}
for tn in selected:
 t=raw['partition_types'][tn];ck=t['clock'];lc=ck['landing_contract'];T=RT.for_type(P,tn)
 assert T['depth']==5,(tn,T['depth'])
 taps=[n for n in T['relays'] if n['q'].startswith('rst_n_t')]
 def nearest(xy,depth):
  n=min((n for n in T['relays'] if n['depth']==depth),key=lambda n:sum(abs(a-b) for a,b in zip(n['xy'],xy)))
  assert sum(abs(a-b) for a,b in zip(n['xy'],xy))<=400.68,(tn,xy,n)
  return n
 origin=[190.56,21.6];outputs=sc['collector']['types'][tn]['mask']['outputs'];pins={p['name']:p['xy_um'] for p in lc['pins']}
 copies=[{'name':'sd_origin','raw':nearest(origin,4)['q'],'xy_um':origin,'consumers':['u_cland_origin']}]
 for bus in outputs:
  xy=[1872.72,pins['cland_fstart_out_'+bus][1]]
  copies.append({'name':'sd_fstart_'+bus,'raw':nearest(xy,4)['q'],'xy_um':xy,'consumers':['u_cland_fstart_'+bus]})
 ck['landing_local_resets']=copies
 def stages(points):
  prev=origin;out=[]
  for xy in points:
   assert sum(abs(a-b) for a,b in zip(prev,xy))<=400.68,(tn,prev,xy)
   out.append({'xy_um':xy,'raw_reset':nearest(xy,5)['q']});prev=xy
  return out
 base=[[570.72,21.6],[949.92,21.6],[1331.04,21.6],[1711.2,21.6],[1872.72,200.0]]
 ck['landing_reader_start']={'depth':6,'origin_rect_um':[188.4,19.44,192.72,23.76],'branches':{b:{'stages':stages(base+[[1872.72,250.0 if b=='i_host_fdi' else 450.0]])} for b in lc['bands']}}
 ck['landing_writer_start']={'depth':7,'branches':{b:{'stages':stages(base+[[1872.72,500.0],[1872.72,800.0]])} for b in outputs}}
 inf=sc['collector']['types'][tn];inf['tree']=T;inf['bands']=copy.deepcopy(lc['bands'])
 for src in inf['local_sources']:
  xy=src.get('pin_xy_um',src['xy_um']);n=min(taps,key=lambda n:sum(abs(a-b) for a,b in zip(n['xy'],xy)))
  src.update(tap=int(n['q'].split('rst_n_t')[1]),xy_um=xy,band=copy.deepcopy(lc['bands'][src['name']]))
 lc.update(collector_tree=T,collector_root_node=inf['collector_root_node'],collector_local_sources=inf['local_sources'],collector_children=inf['children'])
 receipt[tn]={'raw_depth':T['depth'],'relays':len(T['relays']),'copies':copies,'reader':ck['landing_reader_start'],'writer':ck['landing_writer_start']}
before=CAB.strap_ties(sc['count_aligned'],old);after=CAB.strap_ties(sc['count_aligned'],raw);changes=[]
for pn,v in after['instances'].items():
 for b,k in v['K'].items():
  oldk=before['instances'][pn]['K'][b]
  if k!=oldk:changes.append({'part':pn,'type':v['type'],'bus':b,'old':oldk,'new':k,'bits':v['values']['strap_ca_k_'+b]})
receipt['K_changes']=changes;receipt['boot']={'public_budget':392,'status':'OPEN: actual native reset/status maturity proof required; no arithmetic-only bound adopted'}
receipt['physical_qualified']=False
(r/'plan_of_record/plan_c_sd_r6w7_candidate.json').write_text(json.dumps(raw,indent=1))
(r/'bindbase/kv40/eW_sidecar_sd_r6w7_candidate.json').write_text(json.dumps(sc,indent=1))
(r/'sd_r6w7_receipt.json').write_text(json.dumps(receipt,indent=1))
print(json.dumps({'relay_counts':{k:v['relays'] for k,v in receipt.items() if k in selected},'K_changes':changes},indent=1))
