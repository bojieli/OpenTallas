import json,gzip,re,sys,collections,math
from pathlib import Path
r=Path(__file__).resolve().parent;d=json.load(open(r/'sd_r52_control_full_xy_inventory.json'));by={z['instance']:z for z in d};pairs=json.load(gzip.open(r/'sd_r52_all_ff_related_pairs.json.gz'));data=set(json.load(open(r/'phy_split_data_ff_rows.json'))['positions']);moves={}
for n,z in by.items():
 if n.startswith('u_bound.u_bin_i_host_fdi/'):
  m=re.search(r'/q\\?\[(\d+)',n)
  z['xy_um']=[1874.718,170.1+.27*int(m[1])] if m else [1874.718,311.58]
  
  if m and int(m[1])==522:z['xy_um']=[1873.53,300.78]
  z['basis']='held actual FDI boundary FF locality anchor, same source cell/pin/cycle'
 elif n.startswith('u_bound.u_bin_i_host_link_rst_n/'):
  z['xy_um']=[1875.906,433.08 if '/q$' in n else 433.62];z['basis']='held actual link boundary FF locality anchor, same source cell/pin/cycle'
adj=collections.defaultdict(set)
for c in pairs['captures']:
 if c['capture'] not in by:continue
 for i in c['source_indices']:
  n=pairs['sources'][i]
  if n==c['capture']:continue
  if '.u_rrl_' in n or '.u_srl_' in n:continue # planned same-depth physical rawtap rebinding handled separately; NOT waived.
  adj[n].add(c['capture']);adj[c['capture']].add(n)
controls=[n for n in by if 'u_bound.u_core.u_fdi_cdc.' in n and n not in data]
for iteration in range(12):
 for n in controls:
  pts=[by[k]['xy_um'] for k in adj[n]];z=by[n]
  if not pts:continue
  x=1872.72;A=max(y+abs(X-x) for X,y in pts);B=min(y-abs(X-x) for X,y in pts);y=(A+B)/2
  if z['clock_net']=='clk' and 365.0<y<435.0:y=364.77 if y<400 else 435.24
  y=4.32+.27*round((max(21.6,min(835,y))-4.32)/.27)
  z['xy_um']=[x,round(y,6)];z['basis']='held actual whole-cone minimax control anchor (not legal cell placement)'
  moves[n]=z['xy_um']
bad=[];cnt=0;matrix=collections.Counter()
for c in pairs['captures']:
 if c['capture'] not in by:continue
 C=by[c['capture']]
 for i in c['source_indices']:
  S=by[pairs['sources'][i]];dist=abs(S['xy_um'][0]-C['xy_um'][0])+abs(S['xy_um'][1]-C['xy_um'][1]);cnt+=1
  if dist>405+1e-6:bad.append({'source':S['instance'],'capture':C['instance'],'L1_um':dist,'source_xy':S['xy_um'],'capture_xy':C['xy_um']});matrix[S['instance'].split('/')[0]]+=1
bad.sort(key=lambda x:-x['L1_um']);sys.path.insert(0,str(r/'src/tools/die_plan'));import taps
p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'));ts=[(x['name'],*x['xy']) for x in p['partition_types']['kv3_sys_SD']['clock']['taps']];ss=[z['xy_um']+[1] for z in d if z['clock_net']=='clk'];lo,fa,asg=taps.assign(ts,ss,2400,400,max_distance_um=400)
rep={'qualified':False,'native_controls':len(controls),'FDI_link_boundary_FF_count':sum('held actual FDI boundary' in z['basis'] or 'held actual link boundary' in z['basis'] for z in d),'all_FFpairs':cnt,'over405':len(bad),'worst':bad[:50],'failing_sources':dict(matrix),'controls':moves,'tap_capacity':[{'root':t[0],'load':n,'maxL1':f} for t,n,f in zip(ts,lo,fa)],'primary_over220':sum(abs(s[0]-ts[j][1])+abs(s[1]-ts[j][2])>220+1e-6 for s,j in zip(ss,asg)),'scope':'Actual CURRENT SYNTH graph before mandatory physical reset tap rebinding. Raw-prefix edges excluded ONLY from choosing control anchor locations, INCLUDED in final failures. Collocated control anchors require legal packing, not a physical PASS.'}
(r/'sd_r52_minimax_control_prep.json').write_text(json.dumps(rep,indent=2));(r/'sd_r52_minimax_full_xy_inventory.json').write_text(json.dumps(d,indent=1));print(json.dumps({k:v for k,v in rep.items() if k not in ['controls','worst']},indent=2));print(json.dumps(bad[:12],indent=1))
