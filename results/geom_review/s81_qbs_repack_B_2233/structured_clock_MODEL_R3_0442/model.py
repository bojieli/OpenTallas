"""DISABLED native-hist structured clock forecast. No ODB mutation or implementation emission."""
import sys,json,gzip,math,bisect,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
import die_clock_128 as NL,core_infra_plan as CP
O=Path(__file__).resolve().parent;P=O/'inputs'
S=json.load(gzip.open(P/'all_instance_PG.json.native_snapshot.json.gz','rt'));pins=json.load(open(P/'actual_clock_pins.json'));caps=json.load(open(P/'FF_clock_caps.json'));mcaps=json.load(open(P/'macro_clock_caps.json'));libs={c:NL.lib_cells(c,O/'lib',names=['BUFx24_ASAP7_75t_R'])for c in('TT','FF')}
FF=[p for p in pins if not p['macro']];MP=[p for p in pins if p['macro']];assert len(FF)==31847 and len(MP)==32 and {p['net']for p in pins}=={'ck'}
master='BUFx24_ASAP7_75t_R';W,H=1620,270;SITE=54;bay=[321840,328320,326160,332640];norm=lambda s:s.replace('\\','');macros=json.load(open(P/'post_place_snapshot.json'))['macros'];boxes=[tuple(v/1000 for v in m['bbox_dbu'])for m in macros]
# Exact native rows and every existing cell footprint are immutable obstacles.
ys=sorted({r[1][1]for r in S['rows']});byrow=collections.defaultdict(list);spans=collections.defaultdict(list)
for r in S['rows']:spans[r[1][1]].append(r)
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-H):bisect.bisect_left(ys,bb[3])]:byrow[y].append((bb[0],bb[2]))
for c in S['cells']:occupy(c[2])
for m in macros:occupy([m['bbox_dbu'][0]-4320,m['bbox_dbu'][1]-4320,m['bbox_dbu'][2]+4320,m['bbox_dbu'][3]+4320])
for y,ints in list(byrow.items()):
 merged=[]
 for a,b in sorted(ints):
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 byrow[y]=merged
nodes=[];fails=[]
def alloc(name,want,parent,kind,allow_bay=False,rect=None):
 cx,cy=[v*1000 for v in want];area=rect or([v for v in bay]if allow_bay else[4320,4320,643680,643680]);best=None
 for y in ys[bisect.bisect_left(ys,max(area[1],cy-80000)):bisect.bisect_right(ys,min(area[3]-H,cy+80000))]:
  for r in spans[y]:
   lo=max(r[1][0],area[0]);hi=min(r[1][2],area[2]);free=[];last=lo
   for a,b in byrow[y]:
    if b<=lo:continue
    if a>=hi:break
    if a>last:free.append((last,min(a,hi)))
    last=max(last,b)
   if last<hi:free.append((last,hi))
   for a,b in free:
    ia=math.ceil((a-r[2][0])/SITE);ib=math.floor((b-W-r[2][0])/SITE)
    if ib<ia:continue
    k=min(ib,max(ia,round((cx-W/2-r[2][0])/SITE)));x=r[2][0]+k*SITE;bb=[x,y,x+W,y+H]
    if not allow_bay and bb[0]<bay[2]and bb[2]>bay[0]and bb[1]<bay[3]and bb[3]>bay[1]:continue
    d=abs(x+W/2-cx)+abs(y+H/2-cy);key=(round(d,6),y,x)
    if best is None or key<best[0]:best=(key,bb,r[3])
 if best is None:fails.append({'name':name,'want':want,'rect':area});return None
 _,bb,orient=best;occupy(bb)
 for y in ys[bisect.bisect_right(ys,bb[1]-H):bisect.bisect_left(ys,bb[3])]:byrow[y].sort()
 n=dict(name=name,parent=parent,master=master,kind=kind,xy=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000],bbox_dbu=bb,orient=orient,want_xy=want,jog_um=best[0][0]/1000);nodes.append(n);return n
import core_infra_wire as CW,core_infra as CI
# Finer regions are geometry/load selected before prediction; no measured latency feedback.
groups=[]
def partition(ps):
 rect=[min(p['xy_dbu'][0] for p in ps)/1000,min(p['xy_dbu'][1] for p in ps)/1000,max(p['xy_dbu'][0] for p in ps)/1000,max(p['xy_dbu'][1] for p in ps)/1000]
 rad=(rect[2]-rect[0]+rect[3]-rect[1])/2
 if (len(ps)<=576 and rad<=64)or len(ps)==1:groups.append(dict(pins=ps,rect=rect,count=len(ps)));return
 axis=0 if rect[2]-rect[0]>=rect[3]-rect[1]else 1
 ps=sorted(ps,key=lambda p:(p['xy_dbu'][axis],p['inst']));h=len(ps)//2;partition(ps[:h]);partition(ps[h:])
partition(FF);leaves={};ends=[]
for i,g in enumerate(groups):
 n=alloc(f'ff_leaf{i}',[(g['rect'][k]+g['rect'][k+2])/2 for k in(0,1)],None,'FF_regional_driver');assert n
 g['node']=n['name'];leaves[n['name']]=('FF',g);ends.append(n)
for i,p in enumerate(MP):
 ma=next(m for m in macros if norm(m['name'])==norm(p['inst']));b=[v/1000 for v in ma['bbox_dbu']];x,y=[v/1000 for v in p['xy_dbu']]
 want=min([([b[0]-4.32,y],x-b[0]),([b[2]+4.32,y],b[2]-x),([x,b[1]-4.32],y-b[1]),([x,b[3]+4.32],b[3]-y)],key=lambda z:z[1])[0]
 n=alloc(f'macro_leaf{i}',want,None,'macro_singleton');assert n;leaves[n['name']]=('M',p);ends.append(n)
# Four-way geometric hierarchy with exactly four branch levels for every real leaf.
# Singleton continuations preserve the selected global architecture, not timing-tuned delay padding.
root=alloc('hist_root',[324.012,331.212],'port:ck','entry',True);assert root
edges=[]
def build(ps,parent,level):
 if level==4:
  assert len(ps)<=4,len(ps)
  for leaf in ps:leaf['parent']=parent['name'];edges.append((parent,leaf,level))
  return
 axis=0 if max(n['xy'][0] for n in ps)-min(n['xy'][0] for n in ps)>=max(n['xy'][1] for n in ps)-min(n['xy'][1] for n in ps)else 1
 ss=sorted(ps,key=lambda n:(n['xy'][axis],n['name']));chunks=[ss[len(ss)*i//4:len(ss)*(i+1)//4] for i in range(4)]
 for i,chunk in enumerate(chunks):
  if not chunk:continue
  want=[(min(n['xy'][a] for n in chunk)+max(n['xy'][a] for n in chunk))/2 for a in(0,1)]
  n=alloc(f"{parent['name']}_b{i}",want,parent['name'],'global_branch');assert n;edges.append((parent,n,level));build(chunk,n,level+1)
build(ends,root,1)
# Actual macro OBS do not block M6/M7. Actual M6 PG shapes obstruct horizontal wire; M7 has no saved PG rectangles.
pg=[tuple(v/1000 for v in p['bbox_dbu']) for p in json.load(open(P/'post_place_snapshot.json'))['PG_rects'] if p['layer']=='M6']
def path(a,b):return CW.channel_path(a,b,obstacles=pg,vertical_obstacles=[],clearance=.024,return_points=True)
def plen(z):return sum(abs(a-b)for u,v in zip(z,z[1:])for a,b in zip(u,v))
def pointon(z,s):
 for a,b in zip(z,z[1:]):
  d=sum(abs(x-y)for x,y in zip(a,b))
  if s<=d+1e-9:
   f=s/d if d else 0;return[a[i]+f*(b[i]-a[i])for i in(0,1)]
  s-=d
 return z[-1]
# Equal serial repeater count per structural level from longest directional-PG route /168um input.
counts={};edge_routes=[]
for a,b,level in edges:
 z=path(a['xy'],b['xy']);edge_routes.append((a,b,level,z,plen(z)));counts[level]=max(counts.get(level,1),math.ceil(plen(z)/168))
for a,b,level,z,L in edge_routes:
 par=a
 for j in range(1,counts[level]):
  n=alloc(f"{b['name']}_rep{j}",pointon(z,L*j/counts[level]),par['name'],'global_level_repeater');assert n;par=n
 b['parent']=par['name']
assert not fails,fails
names=['BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R','BUFx8_ASAP7_75t_R','BUFx12_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={c:NL.lib_cells(c,O/'lib',names=names)for c in('TT','FF')}
for n in nodes:n['master']=names[0]
def width(n):return CI.BUF_WIDTH_UM[n['master'].split('_ASAP7')[0]]
def xy(n):return[n['bbox_dbu'][0]/1000+width(n)/2,(n['bbox_dbu'][1]+n['bbox_dbu'][3])/2000]
by={n['name']:n for n in nodes};ch=collections.defaultdict(list)
for n in nodes:
 if n['parent']in by:ch[n['parent']].append(n)
def walk(n):
 yield n
 for kid in ch[n['name']]:yield from walk(kid)
order=list(walk(root));assert len(order)==len(nodes)
def net(n,c):
 ts=[(k['name'],xy(k),libs[c][k['master']]['cap'])for k in ch[n['name']]];kind,g=leaves.get(n['name'],(None,None))
 if kind=='FF':ts.append(('open',xy(n),libs[c][names[-1]]['cap']))
 if kind=='M':ts.append(('macro',[x/1000 for x in g['xy_dbu']],mcaps[g['master']][c.lower()]['capacitance']))
 q=CW.rooted_rc([xy(n)]+[t[1]for t in ts],[t[2]for t in ts],horizontal_rc=(.0118796,.1305),vertical_rc=(.0125096,.0925),obstacles=pg,vertical_obstacles=[],clearance=.024,outline_um=[648,648]);return ts,q
selection=[]
for iteration in range(2):
 for n in reversed(order):
  loads={c:net(n,c)[1]['total_load_ff']for c in('TT','FF')}
  valid=[m for m in names if all(libs[c][m]['delay'][1][0]<=loads[c]<=libs[c][m]['delay'][1][-1]for c in('TT','FF'))]
  if valid:n['master']=valid[-1]
  elif iteration==1:selection.append(dict(node=n['name'],loads=loads,reason='no characterized master; preserve topology and report, no clamp/collapse'))
report={};routes=[]
for c in('TT','FF'):
 arrivals={root['name']:0.};slews={root['name']:0.};rows=[];nets=[]
 for n in order:
  ts,q=net(n,c);lib=libs[c][n['master']];load=q['total_load_ff'];s0=slews[n['name']];d=NL._bilin(lib['delay'],s0,load);so=NL._bilin(lib['trans'],s0,load)
  nets.append(dict(node=n['name'],master=n['master'],load_ff=load,input_slew_ps=s0,output_cell_slew_ps=so,load_out=not(lib['delay'][1][0]<=load<=lib['delay'][1][-1]),slew_out=not(lib['delay'][0][0]<=s0<=lib['delay'][0][-1]),wire_um=q['wire_um']))
  for k,(dst,pt,cap)in enumerate(ts):
   a=arrivals[n['name']]+d+q['target_elmore_ps'][k];s=math.hypot(so,2.2*q['target_elmore_ps'][k])
   if dst in by:arrivals[dst]=a;slews[dst]=s
   elif dst=='open':
    g=leaves[n['name']][1];t=CP.open_subtree(g['count'],g['rect'],c,xy(n),fanout=24);why=CP.calibration_check(g['count'],t['levels'],t['region_d_um'],g['rect'],[648,648]);rows.append(dict(node=n['name'],kind='FF_cts_open',sinks=g['count'],min_ps=a+t['min_ps'],mean_ps=a+t['mean_ps'],max_ps=a+t['max_ps'],calibration_reasons=why,region_reach_um=t['region_d_um'],cts_levels=t['levels'],internal_window_ps=t['max_ps']-t['min_ps']))
   else:rows.append(dict(node=n['name'],kind='macro_PIN',sinks=1,min_ps=a,mean_ps=a,max_ps=a,calibration_reasons=[],internal_window_ps=0))
  if c=='TT':routes.append(dict(driver=n['name'],points=[xy(n)]+[t[1]for t in ts],parent=q['parent'],paths=q['paths']))
 low=min(x['min_ps']for x in rows);high=max(x['max_ps']for x in rows);report[c]=dict(sinks=sum(r['sinks']for r in rows),min_ps=low,max_ps=high,window_ps=high-low,mean_ps=sum(r['mean_ps']*r['sinks']for r in rows)/31879,NLDM_load_out=sum(x['load_out']for x in nets),NLDM_slew_out=sum(x['slew_out']for x in nets),calibration_out=sum(bool(x['calibration_reasons'])for x in rows),internal_window_gt40=sum(x['internal_window_ps']>40 for x in rows),leaves=rows,nets=nets)
for n in nodes:n['xy_sized']=xy(n);n['bbox_sized_dbu']=[n['bbox_dbu'][0],n['bbox_dbu'][1],round(n['bbox_dbu'][0]+width(n)*1000),n['bbox_dbu'][3]]
depths={root['name']:0}
for n in order[1:]:depths[n['name']]=depths[n['parent']]+1
out=dict(scope='DISABLED finite R3 SOURCE MODEL ONLY: equal-structure feed, actual directional OBS/PG, ideal saved-SDC0ps input; no GEN/install/CTS/GRT/RC/STA',period_ps=833,source_input_transition_ps=0,source_transition_basis='exact saved3_place.sdc has no ck set_clock_transition/input driver; first root standard NLDM linear extrapolation below5ps remains unqualified, no clamp',FF=31847,macro_clock_pins=32,FF_regions=len(groups),planned_buffers=len(nodes),master_counts=dict(collections.Counter(n['master']for n in nodes)),selection_failures=selection,per_structural_level_segments=counts,leaf_feed_depths=dict(collections.Counter(depths[k]for k in leaves)),max_site_jog_um=max(n['jog_um']for n in nodes),native_rows=len(S['rows']),immutable_cells=len(S['cells']),macro_OBS_basis='SRAMM1-M4;histbankM1-M5;both permitM6/M7crossing;all32body4.32halos still buffer-siteobstacles',M6_PG_obstacles=len(pg),M7_PG_obstacles=0,wire_model='native rooted shared directionalM6/M7RC;M6PGclearance24nm;track/pinlanding/vias/capacity remain physical prerequisites',corners=report,holds=['actualM2-M7datacongestionH1.200/col1.143 nativeRUDYmiss;unchanged','no macro child internal insertion claim','existing calibration policy unchanged; any reported out-of-envelope remains FAIL','all31847FF/32macros/pins/source833 remain immutable; allproposedcellfootprints reserved on actualnative rows and against all155466cells','no buildableclockinstallation or sourcequalification implied'])
(O/'model.json').write_text(json.dumps(out,indent=2));(O/'nodes.json').write_text(json.dumps(nodes,indent=2));(O/'routes.json').write_text(json.dumps(routes));(O/'FF_region_assignments.json').write_text(json.dumps([{k:v for k,v in g.items()if k!='pins'}|{'sinks':[p['inst']+'/'+p['pin']for p in g['pins']]}for g in groups]));print({k:v for k,v in out.items()if k not in('corners','holds')});print({c:{k:v for k,v in q.items()if k not in('leaves','nets')}for c,q in report.items()})
