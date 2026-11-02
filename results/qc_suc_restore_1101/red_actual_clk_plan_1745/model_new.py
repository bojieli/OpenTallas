from pathlib import Path
import sys,csv,json,collections,math,inspect,hashlib,copy
r=Path('/srv/opentallas-scratch2/claude/codex-qc-red-new-model-1620');old=Path('/srv/opentallas-scratch2/claude/codex-qc-red-power-1101');sys.path.insert(0,str(old/'tools/die_plan'));import core_family_slice as F
ns=list(csv.DictReader((r/'actual_clock_nodes.tsv').open(),delimiter='\t'));ss=list(csv.DictReader((r/'actual_clock_sinks.tsv').open(),delimiter='\t'));entry=list(csv.DictReader((r/'actual_clock_entry.tsv').open(),delimiter='\t'))[0]
placed=Path('/srv/opentallas-scratch2/claude/codex-qc-red-lattice8-kit-1101/qfd_dv_s5_red2_leaf_pin1lat8/placed.csv');ps={x['name']:x for x in csv.DictReader(placed.open()) if x['kind']!='pin'}
rename=lambda n: n[len('mp_ck_'):] if n.startswith('mp_ck_') else n
assert len(ns)==8269 and len(ss)==34225 and len({x['instance'] for x in ss})==34225
nd={rename(n['instance']):n for n in ns};netdrv={n['output_net']:rename(n['instance']) for n in ns};actual_leafs=sorted({rename(x['drivers']) for x in ss});assert len(actual_leafs)==3452
pos={u:(float(ps[n['instance']]['x'])+float(ps[n['instance']]['w'])/2,float(ps[n['instance']]['y'])+float(ps[n['instance']]['h'])/2) for u,n in nd.items()}
parents={u:netdrv.get(n['input_net']) for u,n in nd.items()};assert [u for u,p in parents.items() if p is None]==['root']
kids=collections.defaultdict(list)
for u,p in parents.items():
 if p:kids[p].append(u)
P=dict(mz=F._LatticeMaze([4.32,4.32,272.16,272.16]),nodes=[(u,parents[u],pos[u],n['master'],'entry' if u=='root' else 'leaf' if u in actual_leafs else 'branch') for u,n in nd.items()],land={},wires=[],leafsinks={},sinkcap={'TT':{},'FF':{}})
for u,cs in kids.items():
 hub=(sum(pos[v][0] for v in cs)/len(cs),sum(pos[v][1] for v in cs)/len(cs));seg=abs(pos[u][0]-hub[0])+abs(pos[u][1]-hub[1]);key='hub_'+u;P['land'][u]=(seg,key);P['wires'].append(dict(edge=key,segs=[seg],cells=[[hub]]))
caps={'DFFHQNx1_ASAP7_75t_R':{'TT':.474736,'FF':.522010},'DFFASRHQNx1_ASAP7_75t_R':{'TT':.462899,'FF':.503152}}
sp=[(float(x['CLK_x']),float(x['CLK_y']),x['instance'],'CLK') for x in ss]
for x in ss:
 assert x['master'] in caps
 for c in ['TT','FF']:P['sinkcap'][c][x['instance']+'/CLK']=caps[x['master']][c]
L={c:F.H.lib_cells(str(old/('INVBUF_'+c+'.lib')),['BUFx8_ASAP7_75t_R']) for c in ['TT','FF']};rr=.5*(.0180365+.0189935)*.8;cc=.5*(.178475+.164264)*.9
# Exact shared R7 equations. Only expose the formerly hardcoded input-boundary state as parameters.
source=inspect.getsource(F.M7.model_x);before="arr = {'root': 0.0}; slew = {'root': 0.0}";after="arr = {'root': P.get('input_arrival_ps',0.0)}; slew = {'root': P.get('input_slew_ps',0.0)}";assert source.count(before)==1;adapted=source.replace(before,after);scope=dict(F.M7.__dict__);exec(adapted,scope);model=scope['model_x'];(r/'shared_R7_boundary_adapter.py').write_text(adapted)
(r/'boundary_adapter_receipt.json').write_text(json.dumps(dict(shared_model='existing R7 NLDM+Elmore equations, centrepoint buffer geometry and exact native CLKpin sinks',only_change='Expose root input arrival/slew boundary; no sizing/topology/threshold/RC calibration change',before_sha256=hashlib.sha256(source.encode()).hexdigest(),after_sha256=hashlib.sha256(adapted.encode()).hexdigest(),root_boundary_qualified=False,input_cases='0/20/40/60ps hypotheses only; no source-backed parent input waveform or absolute frame yet'),indent=2)+'\n')
leaf_xy={u:(float(nd[u]['Y_x']),float(nd[u]['Y_y'])) for u in actual_leafs};B=8.64
bins=collections.defaultdict(list)
for u,(x,y) in leaf_xy.items():bins[(math.floor(x/B),math.floor(y/B))].append(u)
def near(x,y,rad=35.):
 a=[]
 for bx in range(math.floor((x-rad)/B),math.floor((x+rad)/B)+1):
  for by in range(math.floor((y-rad)/B),math.floor((y+rad)/B)+1):
   for u in bins.get((bx,by),[]):
    px,py=leaf_xy[u];d=abs(x-px)+abs(y-py)
    if d<=rad:a.append((d,u))
 return sorted(a)
candidates=[near(x,y) for x,y,_,_ in sp];assert all(candidates),'actual sink has no retained driver within35um'
actual=[rename(x['drivers']) for x in ss]
def rebind(cap):
 counts=collections.Counter();assign=[None]*len(sp)
 for i in sorted(range(len(sp)),key=lambda i:(len(candidates[i]),-candidates[i][0][0],i)):
  opts=[(d+.025*counts[u]**2,d,u) for d,u in candidates[i] if counts[u]<cap]
  if not opts:raise ValueError('capacity/35um assignment blocked at '+sp[i][2])
  _,_,u=min(opts);assign[i]=u;counts[u]+=1
 empty=[u for u in actual_leafs if not counts[u]]
 for u in sorted(empty,key=lambda u:-min(abs(x-leaf_xy[u][0])+abs(y-leaf_xy[u][1]) for x,y,_,_ in sp)):
  opts=[];ux,uy=leaf_xy[u]
  for i,(x,y,_,_) in enumerate(sp):
   a=assign[i]
   if counts[a]<=1:continue
   d=abs(x-ux)+abs(y-uy)
   if d>35:continue
   ax,ay=leaf_xy[a];opts.append((d-abs(x-ax)-abs(y-ay),d,i))
  if not opts:raise ValueError('cannot retain nonempty fixed leaf '+u)
  _,_,i=min(opts);counts[assign[i]]-=1;assign[i]=u;counts[u]+=1
 assert min(counts[u] for u in actual_leafs)>=1 and max(counts.values())<=cap
 return assign,dict(max_leaf_count=cap,all_3452_fixed_leaves_nonempty=True,originally_empty_leaves=len(empty),moved_sinks=sum(a!=b for a,b in zip(actual,assign)))
results=[]
for name,cap in [('current',None),('cap12',12),('cap16',16)]:
 out=r/name;out.mkdir(exist_ok=True)
 try:
  assign,meta=(actual,dict(original_binding=True)) if cap is None else rebind(cap)
  P['leafsinks']={u:[] for u in actual_leafs}
  for i,u in enumerate(assign):P['leafsinks'][u].append(sp[i])
  assert sum(map(len,P['leafsinks'].values()))==34225 and all(P['leafsinks'].values())
  dists=[abs(p[0]-leaf_xy[u][0])+abs(p[1]-leaf_xy[u][1]) for u,a in P['leafsinks'].items() for p in a]
  row=dict(name=name,scope='PLAN MODEL of ACTUAL NEW PLACE fixed8269nodes/nativeCLKpins; inputframe conditional/unqualified, no ODB edit or CTS',assignment=meta,clock_nodes=8269,sinks=34225,missing=0,duplicates=0,max_actual_Y_to_CLK_L1_um=max(dists),sinks_gt40=sum(d>40 for d in dists),leaf_counts=[min(map(len,P['leafsinks'].values())),max(map(len,P['leafsinks'].values()))],boundary_cases={})
  root=nd['root'];stub=abs(float(entry['x'])-float(root['A_x']))+abs(float(entry['y'])-float(root['A_y']))
  for slew in [0.,20.,40.,60.]:
   bycorner={}
   for corner in ['TT','FF']:
    rootcap=L[corner]['BUFx8_ASAP7_75t_R']['cin'];delay=rr*stub*(cc*stub/2+rootcap);P['input_arrival_ps']=delay;P['input_slew_ps']=math.hypot(slew,2.2*delay)
    res,st=model(P,{corner:L[corner]},rr,cc,{})
    ct=[v[0] for v in P['_int'][corner]['drv'].values()];ffcap=sum(P['sinkcap'][corner].values());bufcap=sum(L[corner][n[3]]['cin'] for n in P['nodes']);wirecap=sum(ct)-ffcap-(bufcap-rootcap)
    res[corner].update(estimated_clockwire_cap_fF=wirecap,buffer_input_cap_fF=bufcap,native_DFFcap_fF=ffcap,primary_input_cap_fF=rootcap+cc*stub,root_stub_L1_um=stub,model_load_sum_fF=sum(ct)+rootcap+cc*stub)
    bycorner[corner]=res[corner]
   row['boundary_cases'][str(int(slew))]=bycorner
  base=row['boundary_cases']['0'];row['relative_model_gate']=all(base[c]['window']<=20 and base[c]['leaf_out_slew_max']<=60 and base[c]['leaf_slew_in_max']<=80 for c in ['TT','FF']) and row['sinks_gt40']==0;row['absolute_frame_qualified']=False
  (out/'checks.json').write_text(json.dumps(row,indent=2)+'\n');(out/'leaf_sinks.json').write_text(json.dumps({u:[p[2]+'/CLK' for p in vs] for u,vs in P['leafsinks'].items()},indent=1)+'\n');results.append(row);print(name,json.dumps({k:row[k] for k in ['assignment','max_actual_Y_to_CLK_L1_um','sinks_gt40','leaf_counts','relative_model_gate']}),json.dumps(base),flush=True)
 except Exception as exc:
  row=dict(name=name,verdict='FAIL/NOTRUN',reason=repr(exc));(out/'checks.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row);print(name,repr(exc),flush=True)
(r/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
