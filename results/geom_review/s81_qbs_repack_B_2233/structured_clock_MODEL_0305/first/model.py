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
# Conservative macro-body visibility, with own-pin final entry treated explicitly.
def segclear(a,b,obs):
 if abs(a[0]-b[0])<1e-8:
  return not any(x0+1e-8<a[0]<x1-1e-8 and min(a[1],b[1])<y1-1e-8 and max(a[1],b[1])>y0+1e-8 for x0,y0,x1,y1 in obs)
 return not any(y0+1e-8<a[1]<y1-1e-8 and min(a[0],b[0])<x1-1e-8 and max(a[0],b[0])>x0+1e-8 for x0,y0,x1,y1 in obs)
def path(a,b,omit=None):
 obs=[q for i,q in enumerate(boxes)if i!=omit];xs={a[0],b[0]}|{v+d for q in obs for v,d in((q[0],-.054),(q[2],.054))};yy={a[1],b[1]}|{v+d for q in obs for v,d in((q[1],-.054),(q[3],.054))};cand=[]
 for x in xs:cand.append([a,(x,a[1]),(x,b[1]),b])
 for y in yy:cand.append([a,(a[0],y),(b[0],y),b])
 ok=[z for z in cand if all(segclear(u,v,obs)for u,v in zip(z,z[1:]))]
 return min(ok,key=lambda z:sum(abs(a-b)for u,v in zip(z,z[1:])for a,b in zip(u,v)))if ok else None
def plen(z):return sum(abs(a-b)for u,v in zip(z,z[1:])for a,b in zip(u,v))
def pointon(z,s):
 for a,b in zip(z,z[1:]):
  d=sum(abs(x-y)for x,y in zip(a,b))
  if s<=d+1e-9:
   f=s/d if d else 0;return[a[i]+f*(b[i]-a[i])for i in(0,1)]
  s-=d
 return z[-1]
# Deterministic actual-pin regions: at most1024FF and at most150um half-box L1 radius.
groups=[]
def partition(ps):
 xx=[p['xy_dbu'][0]/1000 for p in ps];yy=[p['xy_dbu'][1]/1000 for p in ps];rect=[min(xx),min(yy),max(xx),max(yy)];rad=(rect[2]-rect[0]+rect[3]-rect[1])/2
 if (len(ps)<=1024 and rad<=150)or len(ps)<=8:groups.append(dict(pins=ps,rect=rect,count=len(ps)));return
 axis=0 if rect[2]-rect[0]>=rect[3]-rect[1]else 1;a=sorted(ps,key=lambda p:(p['xy_dbu'][axis],p['inst']));h=len(a)//2;partition(a[:h]);partition(a[h:])
partition(FF)
root=alloc('hist_root',[324.012,331.212],'port:ck','entry',True);assert root
roots={};hubs={};leaves=[];connections=[]
for q in range(4):roots[q]=alloc(f'branch_q{q}',root['xy'],root['name'],'root_fanout',True)
def quad(xy):return(int(xy[0]>=324)+2*int(xy[1]>=324))
for g in groups:g['quad']=quad([(g['rect'][0]+g['rect'][2])/2,(g['rect'][1]+g['rect'][3])/2])
for m in MP:m['quad']=quad([x/1000 for x in m['xy_dbu']])
# One-point-to-point edge per long branch; explicitrepeaters every80um forecast.
def link_to(start,target,name,kind):
 z=path(start['xy'],target['xy']);L=plen(z)if z else sum(abs(a-b)for a,b in zip(start['xy'],target['xy']));k=max(1,math.ceil(L/80));par=start
 for i in range(1,k):
  want=pointon(z,L*i/k)if z else[start['xy'][0]+(target['xy'][0]-start['xy'][0])*i/k,start['xy'][1]+(target['xy'][1]-start['xy'][1])*i/k];n=alloc(f'{name}_rep{i}',want,par['name'],'repeater')
  if n:par=n
 target['parent']=par['name']
for q in range(4):
 ps=[p for g in groups if g['quad']==q for p in g['pins']];ms=[p for p in MP if p['quad']==q];xy=[[v/1000 for v in p['xy_dbu']]for p in ps+ms];want=[sum(p[i]for p in xy)/len(xy)for i in(0,1)];hub=alloc(f'hub_q{q}',want,roots[q]['name'],'regional_hub');assert hub;hubs[q]=hub;link_to(roots[q],hub,f'q{q}','trunk')
for k,g in enumerate(groups):
 hub=hubs[g['quad']];branch=alloc(f'ff_branch{k}',hub['xy'],hub['name'],'regional_branch');want=[(g['rect'][i]+g['rect'][i+2])/2 for i in(0,1)];leaf=alloc(f'ff_leaf{k}',want,branch['name'],'FF_regional_driver');assert leaf;link_to(branch,leaf,f'f{k}','FF_trunk');g['node']=leaf['name'];leaves.append(dict(node=leaf['name'],kind='cts_open',pins=g['pins'],rect=g['rect'],count=g['count']))
for k,m in enumerate(MP):
 hub=hubs[m['quad']];branch=alloc(f'macro_branch{k}',hub['xy'],hub['name'],'macro_branch');xy=[v/1000 for v in m['xy_dbu']];ma=next(z for z in macros if norm(z['name'])==norm(m['inst']));b=[v/1000 for v in ma['bbox_dbu']];faces=[([b[0]-4.32,xy[1]],xy[0]-b[0]),([b[2]+4.32,xy[1]],b[2]-xy[0]),([xy[0],b[1]-4.32],xy[1]-b[1]),([xy[0],b[3]+4.32],b[3]-xy[1])];want=min(faces,key=lambda z:z[1])[0];leaf=alloc(f'macro_leaf{k}',want,branch['name'],'macro_cluster_singleton');assert leaf;link_to(branch,leaf,f'm{k}','macro_trunk');leaves.append(dict(node=leaf['name'],kind='macro',pins=[m],count=1))
assert not fails,fails
# Native row/site/obstacle occupancy was reserved before any electrical model.
nodeby={n['name']:n for n in nodes};child=collections.defaultdict(list)
for n in nodes:
 if n['parent']in nodeby:child[n['parent']].append(n)
leafby={g['node']:g for g in leaves};wires=[]
for n in nodes:
 if n['parent']not in nodeby:continue
 a=nodeby[n['parent']]['xy'];z=path(a,n['xy']);L=plen(z)if z else sum(abs(a-b)for a,b in zip(a,n['xy']));wires.append(dict(parent=n['parent'],child=n['name'],length_um=L,visibility_route=z,lower_bound_only=z is None))
bywire={w['child']:w for w in wires};corners={};rc={'r_kohm_um':.0214161,'c_ff_um':.113298,'basis':'actualhist set_wire_rc -clock; source-slew40ps; conservative uniform stock-clock layer aggregate, no NDR credit'}
def order(n):
 yield n
 for v in child[n['name']]:yield from order(v)
seq=list(order(root));assert len(seq)==len(nodes)
for c in('TT','FF'):
 arrivals={root['name']:0.};slews={root['name']:40.};rows=[];nets=[];outs=[]
 for n in seq:
  children=child[n['name']];leaf=leafby.get(n['name']);targets=[]
  for q in children:targets.append((q['name'],bywire[q['name']]['length_um'],libs[c][q['master']]['cap']))
  if leaf:
   if leaf['kind']=='cts_open':targets.append(('open',0,libs[c][master]['cap']))
   else:
    m=leaf['pins'][0];xy=[v/1000 for v in m['xy_dbu']];targets.append(('macro',sum(abs(a-b)for a,b in zip(n['xy'],xy)),mcaps[m['master']][c.lower()]['capacitance']))
  if not targets:continue
  # Child branches are individually buffered at local hubs; sum wires is conservative for local fanout.
  wire=sum(t[1]for t in targets);load=sum(t[2]for t in targets);lib=libs[c][master];Cwire=wire*rc['c_ff_um'];d=NL._bilin(lib['delay'],slews[n['name']],Cwire+load);so=NL._bilin(lib['trans'],slews[n['name']],Cwire+load)
  outside=not(lib['delay'][0][0]<=slews[n['name']]<=lib['delay'][0][-1]and lib['delay'][1][0]<=Cwire+load<=lib['delay'][1][-1]);nets.append(dict(driver=n['name'],fanout=len(targets),wire_um=wire,load_ff=load,wire_cap_ff=Cwire,input_slew_ps=slews[n['name']],NLDM_out_of_table=outside))
  for dst,L,cap in targets:
   el=L*rc['r_kohm_um']*(L*rc['c_ff_um']/2+cap);a=arrivals[n['name']]+d+el;s=math.hypot(so,2.2*el)
   if dst in nodeby:arrivals[dst]=a;slews[dst]=s
   elif dst=='open':
    sub=CP.open_subtree(leaf['count'],leaf['rect'],c,n['xy'],fanout=24);why=CP.calibration_check(leaf['count'],sub['levels'],sub['region_d_um'],leaf['rect'],[648,648]);rows.append(dict(node=n['name'],kind='cts_open',sinks=leaf['count'],min_ps=a+sub['min_ps'],mean_ps=a+sub['mean_ps'],max_ps=a+sub['max_ps'],calibration_reasons=why,levels=sub['levels'],region_reach_um=sub['region_d_um']));outs.extend(why)
   else:rows.append(dict(node=n['name'],kind='macro',sinks=1,min_ps=a,mean_ps=a,max_ps=a,calibration_reasons=[],scope='actualmacroclockPINarrival; no internalFFinsertionclaim'))
 count=sum(r['sinks']for r in rows);low=min(r['min_ps']for r in rows);high=max(r['max_ps']for r in rows);mean=sum(r['mean_ps']*r['sinks']for r in rows)/count;corners[c]=dict(sinks=count,min_ps=low,mean_ps=mean,max_ps=high,window_ps=high-low,target_ps=250 if c=='TT' else 202.5,target_window_ps=40,within_target=abs(mean-(250 if c=='TT' else 202.5))<=20 and high-low<=40,calibration_out_leaves=sum(bool(r['calibration_reasons'])for r in rows),NLDM_out_of_table_nets=sum(q['NLDM_out_of_table']for q in nets),leaves=rows,nets=nets)
report=dict(scope='DISABLED structuredclock model from ACTUALsavedPLACE+PG-onlyidentity-samecopy; no GEN/CTS/GRT/RC/STA',FF=31847,macro_clock_pins=32,actual_net='ck',period_ps=833,entry_xy_um=[324.012,331.212],macro_cluster_rule=dict(size_max=2,diameter_max_um=40,closest_pair_um=73.44,clusters=32,singletons=32),FF_regions=len(groups),planned_buffer_count=len(nodes),planned_buffer_area_um2=len(nodes)*W*H/1e6,master=master,native_rows=len(S['rows']),immutable_existing_cells=len(S['cells']),legal_forecast_buffer_sites=len(nodes),site_allocation_failures=fails,max_site_jog_um=max(n['jog_um']for n in nodes),planned_wire_max_um=max(w['length_um']for w in wires),visibility_unresolved=sum(w['lower_bound_only']for w in wires),driver_bay_native_empty=True,bay_entry_buffers=sum(n['kind']in('entry','root_fanout')for n in nodes),RC=rc,corners=corners,holds=['congestion:actualplacedM2-M7channel_h1.200/col_v1.143; nativeRUDYtargetmiss','sourceonlyforecast:buffercenters use exactmasterfootprints/native rows; actualpin escape/PG-track/clockwiretrackplanning remains','all32macroPINleaves explicit; no internalclockinsertionorchild-sourcequalifications transferred','globalvisibilityunresolved wires are Manhattan LOWERBOUNDS only','no clockinstallationorphysicalstageauthorized'])
(O/'model.json').write_text(json.dumps(report,indent=2)+'\n');(O/'nodes.json').write_text(json.dumps(nodes,indent=2)+'\n');(O/'wires.json').write_text(json.dumps(wires,indent=2)+'\n');(O/'FF_region_assignments.json').write_text(json.dumps([{k:v for k,v in g.items()if k!='pins'}|{'sinks':[p['inst']+'/'+p['pin']for p in g['pins']]}for g in groups]));print(json.dumps({k:v for k,v in report.items()if k!='corners'}));print({c:{k:v for k,v in q.items()if k not in('leaves','nets')}for c,q in corners.items()})
