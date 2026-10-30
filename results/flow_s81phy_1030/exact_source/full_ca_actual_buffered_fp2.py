"""New candidate geometry -> modeled arrivals -> canonical CA. Old truth is read-only.
This is a feasibility model, never a physical timing receipt.
"""
import json,sys,math,copy
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
import die_sta_related as D;import count_align_plan as CA
from die_clock_128 import _bilin
D.CPPR_LCA=True
EDGE_MAP=json.load(open(R/'edge_map0.json'));DIRECT_CAP={};DIRECT_WIRE={};DIRECT_EXTRA={};CAP_AT={};EXTRA_AT={};WIRE_AT={}
# Seven native clockpins; existing negative-edge DFFLQN needs no external inverter.
# Shortest rectilinear clockbranch within reserved8.64x.81bay: 2perimeter+actualsourceoffset.

G=json.load(open(R/'start_graph_estimate.json'));P=json.load(open(R/'input.json'));F=json.load(open(R/'old_feed.json'));OLD=json.load(open(R/'old_regional.json'));BASE=json.load(open(R/'old_truth/ca_phase_plan.json'));C=json.load(open(R/'cal_g03b_refit.json'));LIB=json.load(open(R/'direct_lib.json'))['corners'];ST=json.load(open(R/'start_ancestry.json'));BAYS=json.load(open(R/'relay_bay_estimate.json'))
ROOT=ST[1]['region'][3:];oldbranch=ST[0]['region'][3:];parts={p['name']:p for p in P['partitions']};tree=json.load(open(R/'tree_exact_lk_ES0_63.64.json'));tout=tree['out'];troot=tree['root'];legs={z['label']:z for z in G['legs']};nodes={};tapspec={};feedroots={};parents={}
def glob(p,q):return [p['origin_um'][0]+2885.76-q[0],p['origin_um'][1]+q[1]]
# Materialize actual inverter vertices. Each path character is one actual inverter, preserving true-polarity pairs.
def attach(parent,label,branch,pn=None):
 z=legs[label];path=parent;chain=[glob(parts[pn],q) for q in z['chain']] if pn else z['chain'];made=[]
 for i,(a,b,length) in enumerate(zip(chain,chain[1:],z['lens'])):
  path=path+(str(branch) if i==0 else '0');nodes[path]=dict(parent=parent if i==0 else made[-1],xy=b,length=length,leg=label,part=pn,branch_charge=(i==0 and (label.startswith('dme_') or label=='feed_942')));parents[path]=nodes[path]['parent'];made.append(path)
 return path
cur=ROOT
for pn in ['lk_ES0','lk_ES1']:
 for n in reversed(F[pn]['nodes'][:-1]):cur=attach(cur,'feed_'+str(n['id']),0)
 feedroots[pn]=cur
 def walk(i,path):
  n=tout[i]
  for t in n['taps']:tapspec['t_'+pn+'__'+t[1]]=dict(node=path,xy=glob(parts[pn],[t[2],t[3]]),part=pn)
  for k,j in enumerate(n['kids']):
   dest=attach(path,'dme_'+str(j),k+1,pn);walk(j,dest)
 walk(troot,cur)
# Keep only relays along the two existing region-origin capture paths, not32 new START interfaces.
capture={'lk_ES0':'t_lk_ES0__clk','lk_ES1':'t_lk_ES1__clk_t7'}
native_home={'lk_ES0':[7.56,74.655],'lk_ES1':[2873.88,185.895]}
native_pin={'lk_ES0':dict(face='W',layer='M4',window_um=[74.736,75.168],xy=[.096,74.952]),'lk_ES1':dict(face='E',layer='M4',window_um=[186.624,187.056],xy=[2885.664,186.84])}
native_clock_port={'lk_ES0':'clk','lk_ES1':'clk_t7'}
native_paths={tapspec[t]['node']:pn for pn,t in capture.items()};selected=set()
for tap in capture.values():
 path=tapspec[tap]['node']
 while path!=ROOT:
  if (len(path)-len(ROOT))%2==0:selected.add(path)
  path=parents[path]
selected=sorted(selected,key=lambda x:(len(x),x));stageparent={p:next((q for q in [p[:k] for k in range(len(p)-1,len(ROOT)-1,-1)] if q in selected),ROOT) for p in selected}
# Bay centers are taken from exact geometric capacity positions, with no imaginary per-pair wire.
baymap={tuple(round(v,4) for v in z['clock_xy']):[(z['bay'][0]+z['bay'][2])/2,(z['bay'][1]+z['bay'][3])/2] for z in BAYS['placements']}
for p in selected:
 nodes[p]['bay_xy']=(glob(parts[native_paths[p]],native_home[native_paths[p]]) if p in native_paths else baymap[tuple(round(v,4) for v in nodes[p]['xy'])])
# New graph timing envelopes anchored to actual unchanged b705. For each old feed leg and local region,
# retain OLD routed late/early delay / OLD calibrated geometric-delay ratio. No fitting to new target phase.
contexts={};model_info={};tap_pairs={};degree={}
for n in nodes.values():degree[n['parent']]=degree.get(n['parent'],0)+1
clock_nldm={}
for c in ['TT','FF']:
 meta,taps=D.load_taps(R/'old_truth',c);original=copy.deepcopy(meta);original_taps=copy.deepcopy(taps);lookup={tuple(round(v,4) for v in xy):p for p,xy in meta['node_xy_um'].items()};coef=C['leg' if c=='TT' else 'leg_FF'];d0,k1,k2,kf=coef
 rates={};cumold={};rootold={}
 lib=LIB[c]['cells'];ck=lib['CKINVDCx16_ASAP7_75t_R'];pin_cap=5*lib['DFFHQNx1_ASAP7_75t_R']['clock_cap_ff']+2*lib['DFFLQNx1_ASAP7_75t_R']['clock_cap_ff'];branchwire=1.10*(2*(8.64+.81)+BAYS['max_clock_to_bay_center_um']);wirecap=branchwire*(.103962+.0928446)/2*1.1;cap=pin_cap+wirecap;DIRECT_CAP[c]=cap;DIRECT_WIRE[c]=branchwire;DIRECT_EXTRA[c]=max(_bilin(ck['cell_'+p],s,ld+cap)-_bilin(ck['cell_'+p],s,ld) for s in [5,80] for p in ['rise','fall'] for ld in [0,5,10,20,40,60,80,100])
 for pn in ['lk_ES0','lk_ES1']:
  for n in reversed(F[pn]['nodes'][:-1]):
   ch=n['physical_leg']['chain'];a,b=[lookup[tuple(round(v,4) for v in q)] for q in [ch[0],ch[-1]]];model=sum(d0+k1*(abs(x[0]-y[0])+abs(x[1]-y[1]))+k2*(abs(x[0]-y[0])+abs(x[1]-y[1]))**2 for x,y in zip(ch,ch[1:]));rates['feed_'+str(n['id'])]={key:(meta[key][b]-meta[key][a])/model for key in D.NODE_TIME_KEYS};rootold[pn]=b
 for pn in parts:
  ot=[t for t in taps.values() if t.get('part')==pn];base=rootold[pn];oldmean=json.load(open(R/'old_model.json'))[pn][c]['mean'];rates[pn]={key:(max if 'late' in key else min)((t[{'node_late_ps':'late_ps','node_early_ps':'early_ps','node_fall_late_ps':'fall_late_ps','node_fall_early_ps':'fall_early_ps'}[key]]-meta[key][base])/oldmean for t in ot) for key in D.NODE_TIME_KEYS}
 CAP_AT[c]={};EXTRA_AT[c]={};WIRE_AT[c]={}
 for p in selected:
  hq=3 if p in native_paths else 5;lq=(1 if p in native_paths else 2) if EDGE_MAP[p] else 0
  pc=hq*lib['DFFHQNx1_ASAP7_75t_R']['clock_cap_ff']+lq*lib['DFFLQNx1_ASAP7_75t_R']['clock_cap_ff']
  bw=1.10*(2*((4.32+.27) if p in native_paths else (8.64+.81))+sum(abs(a-b) for a,b in zip(nodes[p]['bay_xy'],nodes[p]['xy'])))
  cp=pc+bw*(.103962+.0928446)/2*1.1;CAP_AT[c][p]=cp;WIRE_AT[c][p]=bw
  EXTRA_AT[c][p]=max(_bilin(ck['cell_'+po],si,ld+cp)-_bilin(ck['cell_'+po],si,ld) for si in [5,80] for po in ['rise','fall'] for ld in [0,5,10,20,40,60,80,100])
 for p,n in sorted(nodes.items(),key=lambda v:len(v[0])):
  l=n['length'];delay=d0+k1*l+k2*l*l+(kf*max(0,degree[n['parent']]-1) if n['branch_charge'] else 0);rate=rates[n['part']] if n['part'] else rates[n['leg']];extra=EXTRA_AT[c][p] if p in selected else 0
  for key in D.NODE_TIME_KEYS:meta[key][p]=meta[key][n['parent']]+delay*rate[key]+extra
  meta['node_stages'][p]=meta['node_stages'][n['parent']]+1;meta['node_xy_um'][p]=n['xy']
  meta['cppr_node_range_ps'][p]=max(0.,meta['node_late_ps'][p]-meta['node_early_ps'][p])
 for port,s in tapspec.items():
  t=taps[port];path=s['node'];dist=sum(abs(a-b) for a,b in zip(s['xy'],nodes[path]['xy']));td=C['tap' if c=='TT' else 'tap_FF'][0]*dist
  t.update(tree_path=path+'0',stages_from_root=meta['node_stages'][path],xy_um=s['xy'])
  for key,tk in [('node_late_ps','late_ps'),('node_early_ps','early_ps'),('node_fall_late_ps','fall_late_ps'),('node_fall_early_ps','fall_early_ps')]:t[tk]=meta[key][path]+td
 # Explicit standardcell isolation and falling conversion, rather than median old abstracttap leg.
 lib=LIB[c]['cells'];ck=lib['CKINVDCx16_ASAP7_75t_R'];pin_cap=5*lib['DFFHQNx1_ASAP7_75t_R']['clock_cap_ff']+2*lib['DFFLQNx1_ASAP7_75t_R']['clock_cap_ff'];branchwire=1.10*(2*(8.64+.81)+BAYS['max_clock_to_bay_center_um']);wirecap=branchwire*(.103962+.0928446)/2*1.1;cap=pin_cap+wirecap
 DIRECT_CAP[c]=cap;DIRECT_WIRE[c]=branchwire
 DIRECT_EXTRA[c]=max(_bilin(ck['cell_'+p],s,ld+cap)-_bilin(ck['cell_'+p],s,ld) for s in [5,80] for p in ['rise','fall'] for ld in [0,5,10,20,40,60,80,100])
 wireel=branchwire*(.00844765+.00889556)/4*(wirecap/2+pin_cap)
 bd=[0.,wireel];fd=[0.,0.]
 for path in [ROOT]+selected:
  key='__st__'+path;xy=nodes[path]['bay_xy'] if path in nodes else original['node_xy_um'][ROOT]
  if path in selected:
   bw=WIRE_AT[c][path];cw=bw*(.103962+.0928446)/2*1.1;pc=CAP_AT[c][path]-cw;bd=[0.,bw*(.00844765+.00889556)/4*(cw/2+pc)]
  taps[key]=dict(port=key,part=native_paths.get(path),cppr_node='h',tree_path=path,stages_from_root=meta['node_stages'][path],xy_um=xy,late_ps=meta['node_late_ps'][path]+max(bd),early_ps=meta['node_early_ps'][path]+min(bd),fall_late_ps=meta['node_fall_late_ps'][path]+max(bd)+max(fd),fall_early_ps=meta['node_fall_early_ps'][path]+min(bd)+min(fd))
  if path==ROOT:
   # Existing source FF clock is unchanged, so its upstream prior START edge remains admissible.
   tl=D.tap_leg(original,original_taps);tf=D.tap_leg_fall(original,original_taps);taps[key].update(late_ps=original['node_late_ps'][path]+tl[0],early_ps=original['node_early_ps'][path]+tl[1],stages_from_root=original['node_stages'][path]+tl[2],fall_late_ps=original['node_fall_late_ps'][path]+tf[0],fall_early_ps=original['node_fall_early_ps'][path]+tf[1])
 assert all(p in meta['cppr_node_range_ps'] for p in nodes)
 meta,taps=D.apply_clock_cal(meta,taps,c,'inv','spice_edge',proof=R/'old_truth');rng=D.clock_cppr_ranges(meta);ocv=D.ca_ocv(R/'old_truth',meta,taps,c,250 if c=='TT' else 202.5,'table','shared','mesh',R/'old_truth/droop_regions.json',clock_cell='inv');contexts[c]=dict(meta=meta,taps=taps,rng=rng,ocv=ocv);model_info[c]=dict(routed_old_to_geometry_ratios=rates)
 # Independent pure-NLDM electrical feasibility of the actual new clock geometry.
 ck=lib['CKINVDCx16_ASAP7_75t_R'];outsl={};insl={};maxclock=0.;maxout=0.
 kids={}
 for q,n in nodes.items():kids.setdefault(n['parent'],[]).append(q)
 for q,n in sorted(nodes.items(),key=lambda z:len(z[0])):
  par=n['parent'];length=n['length'];rwire=length*(.00844765+.00889556)/4;cwire=length*(.103962+.0928446)/2*1.1;el=rwire*(cwire/2+ck['cap_ff'])
  # The first new stage inherits the unchanged source-provider input slew contract.
  inp={p:(80. if par==ROOT else math.hypot(outsl[par][p],2.2*el)) for p in ['rise','fall']}
  load=sum(nodes[k]['length']*(.103962+.0928446)/2*1.1+ck['cap_ff'] for k in kids.get(q,[]))+(CAP_AT[c][q] if q in selected else 0.)
  if not kids.get(q):load+=3. # existing partition tap-load contract
  outsl[q]={p:_bilin(ck[p+'_transition'],inp['fall' if p=='rise' else 'rise'],load) for p in ['rise','fall']}
  insl[q]=inp;maxclock=max(maxclock,*inp.values());maxout=max(maxout,*outsl[q].values())
 clock_nldm[c]=dict(direct7ff_pin_cap_ff=pin_cap,direct_clock_branch_cap_ff=DIRECT_CAP[c],direct_branch_wire_bound_um=DIRECT_WIRE[c],direct_clock_load_delay_bound_ps=DIRECT_EXTRA[c],input_contract_ps=80.,max_input_slew_ps=maxclock,max_output_slew_ps=maxout,max_fanout=max(degree.values()),source='Actual ASAP7 CKINVDCx16 TT/FF NLDM; shared M8/M9 2W2S NDR RC R/2 Cx1.1; actual branchloads+directvirtual7FF/native4FF caps+tap3fF. Inherited unchanged upstream provider80ps input contract, model only.',pass_slew80=max(maxclock,maxout)<=80.)
 # Exact affected old landed tap pairs retained; matching metadata from old LPO.
 oldcorn=json.load(open(R/'old_ocv.json'))['corners'][next(k for k in json.load(open(R/'old_ocv.json'))['corners'] if k.startswith(c))]
 tap_pairs[c]={r['port']:(r['tap_src'][0],r['tap_dst'][0]) for r in oldcorn}
# Canonical full model START intervals plus real NLDM wire data between actual chosen bays.
exec(compile((R/'actual_buffered_data_bound.py').read_text().split('rows=[]')[0],str(R/'actual_buffered_data_bound.py'),'exec'))
actual_data=data;L=LIB
DATA_NATIVE=False; DATA_FANOUT=1
def data(c,length,slew,pol):return actual_data(c,length,slew,pol,kind='start',fanout=DATA_FANOUT,spacing=100,local_um=1.0,native=DATA_NATIVE)

edges=[];checks=[]
for p in selected:
 par=stageparent[p];aa='__st__'+par;bb='__st__'+p;ivs=[];fallivs=[];nom=[];details={}
 DATA_NATIVE=not EDGE_MAP[p];DATA_FANOUT=sum(q==par for q in stageparent.values())
 for c,k in contexts.items():
  a,b=k['taps'][aa],k['taps'][bb];walk=p;wire=0.
  while walk!=par:wire+=nodes[walk]['length'];walk=parents[walk]
  if p in native_paths:
   pn=native_paths[p];pin=native_pin[pn];pxy=glob(parts[pn],pin['xy']);wire+=sum(abs(x-y) for x,y in zip(pxy,nodes[p]['xy']))+sum(abs(x-y) for x,y in zip(pxy,b['xy_um']))+.432
  else:wire+=sum(abs(x-y) for x,y in zip(b['xy_um'],nodes[p]['xy']))
  wire+=(10. if par==ROOT else sum(abs(x-y) for x,y in zip(a['xy_um'],nodes[par]['xy'])))
  wire+=(4.32+.405)+(2.16+.135 if p in native_paths else 4.32+.405)
  saved_end=L[c]['cells']['DFFLQNx1_ASAP7_75t_R']['cap_ff']
  if False:pass
  v=[data(c,wire,s,pol) for s in [5,80] for pol in ['rise','fall']]
  L[c]['cells']['DFFLQNx1_ASAP7_75t_R']['cap_ff']=saved_end;dl=min(x[0] for x in v)*.95;dh=max(x[0] for x in v)*1.1011
  lo,hi,_,_=D.ca_pair_interval(a,b,aa,bb,k['rng'],k['ocv']);fl,fh,_,_=D.ca_pair_interval(a,b,aa,bb,k['rng'],k['ocv'],'fall');ivs.append((lo-dh,hi-dl));fallivs.append((fl-dh,fh-dl));nom.append((lo+hi-dh-dl)/2);details[c]=dict(wire_um=wire,data_ps=[dl,dh],phase_ps=ivs[-1],fall_phase_ps=fallivs[-1],data_slew_ps=max(x[1] for x in v))
 lo=min(x[0] for x in ivs);hi=max(x[1] for x in ivs);fl=min(x[0] for x in fallivs);fh=max(x[1] for x in fallivs);dn=nom[0];edge=dict(port='start:model:'+p,src='st:'+par,dst='st:'+p,d_ps=dn,p_dn_ps=dn-lo,p_up_ps=hi-dn,fall_lo=fl,fall_hi=fh,lo=lo,hi=hi,retime=True,launch=aa,capture=bb,launch_part=None,capture_part=native_paths.get(p),clean_ok=True,unshared_a_ps=0,unshared_b_ps=0);choice=CA.sync_choice_iv(edge,833.,104.125);edge['clean_ok']=choice[0]==1;edges.append(edge);checks.append(dict(path=p,site_xy=nodes[p]['bay_xy'],clock_xy=nodes[p]['xy'],choice=choice,details=details))
# Existing partition origin is one selected native clock capture; no extra START clock stage at the interface.
endmap={pn:'st:'+tapspec[tp]['node'] for pn,tp in capture.items()}
for e in edges:
 for pn,end in endmap.items():
  if e['dst']==end:e['dst']=pn
for e in edges:
 for pn,end in endmap.items():
  if e['src']==end:e['src']=pn
# Keep immutable prior START edges only outside the replaced ES subgraph.
remove=set(['lk_ES0','lk_ES1']);remove.update(e['dst'] for e in BASE['start_edges'] if e['dst'].startswith('st:'+oldbranch));prior=[e for e in BASE['start_edges'] if e['dst'] not in remove]
rows=CA.load_rows(R/'old_truth/lpo.json','TT_droop-regions_corelat250,FF_droop-regions_corelat202.5');affected=[]
oldcross={x['port']:x for x in BASE['crossings']}
for r in rows:
 # Retain the full prior canonical STA hull for every unchanged crossing, not raw LPO-only data.
 oldrow=oldcross[r['port']]
 for key in ['d_ps','p_dn_ps','p_up_ps']:
  if key in oldrow:r[key]=oldrow[key]
 r['unshared_sta_ps']=oldrow.get('wander_ps',0)/.05
 if r['port'] not in tap_pairs['TT']:continue
 lo=[];hi=[];un=[];cn={}
 for c,k in contexts.items():
  a,b=tap_pairs[c][r['port']];x,y,_,_=D.ca_pair_interval(k['taps'][a],k['taps'][b],a,b,k['rng'],k['ocv']);lo.append(x);hi.append(y);un.append(D.ca_pair_unshared(k['taps'][a],k['taps'][b],k['meta']['node_late_ps']));cn[c]=[x,y]
 ta,tb=tap_pairs['TT'][r['port']];r['d_ps']=contexts['TT']['taps'][tb]['late_ps']-contexts['TT']['taps'][ta]['late_ps']
 r['p_dn_ps']=r['d_ps']-min(lo);r['p_up_ps']=max(hi)-r['d_ps'];r['unshared_sta_ps']=max(un);affected.append(dict(port=r['port'],model_corner_intervals=cn))
summ,out,regs=CA.plan(rows,start_edges=prior+edges,start_root=BASE['summary']['tree_root'])
json.dump(dict(scope='MODELED DIRECT7FF 5DFFHQN+2DFFLQN candidate A clock/START/CA with immutable old prefix, explicit newtopology, oldroutedleg delay/geometry residual envelopes and realrelayNLDM. Full canonicalCA recompile, no physicalproof.',summary=summ,affected=affected,crossings=[x for x in out if x['port'] in {r['port'] for r in affected}],regions=[x for x in regs if x['region'] in ['lk_ES0','lk_ES1']],start_checks=checks,selected_relay_count=len(selected),virtual_stage_count=len(selected)-len(native_paths),native_endpoint_count=len(native_paths),native_endpoint_homes_local=native_home,native_start_pin_contract=native_pin,native_origin_clock_port=native_clock_port,model_hardware='source-derived32taps + direct7FFvirtual/3FFnativeR + explicitproposedmappedINV1/BUF8 DATA; nativepartclassB250/202.5 canonicalvariation, no phantomrawrelay atnativeorigin',clock_nldm=clock_nldm,model_info=model_info,build_allowed=False),open(R/'exact_actual_buffered_ca_fp2.json','w'),indent=1)
print(json.dumps(summ));print(json.dumps([x for x in regs if x['region'] in ['lk_ES0','lk_ES1']]));print('unclean model links',[(x['path'][-15:],x['choice']) for x in checks if x['choice'][0]!=1])

import count_align_bind as B
# PROVISIONAL diagnostic candidate: source DATA recipe and exact cell homes not installed.
modeldoc=dict(summary=dict(summ,period_ps=833.,aperture_ps=104.125,sync_aperture_ps=26.5,model_only=True),regions=regs,crossings=out,start_edges=[{k:v for k,v in e.items() if not k.startswith('_')} for e in prior+edges])
json.dump(modeldoc,open(R/'native_ca_plan_fp2.json','w'),indent=1)
bind=B.bind(modeldoc,parts=B.ocv_parts(rows));bind['model_only']=True;json.dump(bind,open(R/'native_ca_bind_fp2.json','w'),indent=1)
stages=[]
rr={g['region']:g for g in regs}
for p in selected:
 name=native_paths.get(p,'st:'+p);g=rr[name];native=p in native_paths;hop=(g['origin_cycles']-8)//3
 stages.append(dict(region=name,path=p,parent=stageparent[p],kind='native_origin' if native else 'virtual',clock_port=native_clock_port.get(native_paths.get(p)) if native else '__st__'+p,home_global_um=nodes[p]['bay_xy'],clock_node_xy_global_um=nodes[p]['xy'],flops=dict(posedge=3 if native else 5,negedge=0 if native else 2),start_module='ot_dp_landing_origin',PAD=0,EDGE_FALL=0 if native else 1,start_origin_cycles=g['origin_cycles'],raw_reset_from_b705_cycles=2*(hop-1 if native else hop),raw_reset_module=None if native else 'ot_die_start_reset_relay',native_raw_collector_depth=(9 if name=='lk_ES0' else 8) if native else None,native_input_reset_relay=1 if native else None))
json.dump(dict(model_only=True,source_anchor=dict(region='st:'+ROOT,origin_cycles=8),clock_nodes=nodes,feed_roots=feedroots,stages=stages,clock_polylines=G['legs'],native_clock_port=native_clock_port,native_pin_contract=native_pin,holds=['rootreview','sourcefieldoriginprimarytapimplementation','nativehomes/sourceABIassembly/render','actualmappedwarmcold/nativeLEC','physicalqualification']),open(R/'native_emit_contract_fp2.json','w'),indent=1)
print('EXPORTED native_ca_plan_fp2.json native_ca_bind_fp2.json native_emit_contract_fp2.json',flush=True)

print('HARDWARE_EDGE_FIXED_POINT',all((q['choice'][1]=='fall')==EDGE_MAP[q['path']] for q in checks),flush=True)
