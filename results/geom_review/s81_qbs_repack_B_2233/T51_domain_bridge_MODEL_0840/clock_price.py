from pathlib import Path
import json,gzip,sys,collections,hashlib
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
from exact_current_assign import assign
D=G.Design(P/'geom.tsv');F=json.load(open(P/'joint_FF_targets.json'));idof={c[6]:i for i,c in D.cells.items()};roots={};cache={}
def root(n,seen=frozenset()):
 if n in cache:return cache[n]
 if n in seen:return None
 dr=D.nets[n][1]
 if not dr:return None
 if dr[0]=='p':return D.pin_by_k[dr[1]]['name']
 if D.kind(dr[1])!='B':return None
 ins=[nn for nn,ck in D.cell_in.get(dr[1],[])];res=root(ins[0],seen|{n})if len(ins)==1 else None;cache[n]=res;return res
native=json.load(open(P/'clock_pins.json'));assert len(native)==52044
for name,pin,net,xy,ok,sig in native:
 i=idof[name];nets=[n for n,ck in D.cell_in.get(i,[])if ck];roots[name]=root(nets[0])if len(nets)==1 else None
assert all(roots.values()),collections.Counter(roots.values())
planpath=P/'current_plan.json';plan=json.load(open(planpath));ck=plan['partition_types']['slice_station__t51']['clock'];taps=[(p['name'],*p['xy'])for p in ck['taps']if p.get('kind')!='core'];radius=ck['tap_radius_um'];cap=ck['tap_max_sinks'];old={n:G.ctr(D.cells[idof[n]])for n in roots};new={n:F[n]['xy_um']if n in F else xy for n,xy in old.items()};core_names=[n for n in roots if roots[n]=='clk' or roots[n].startswith('clk_t')];edge_names=[n for n in roots if n not in core_names]
assert len(core_names)+len(edge_names)==52044
reports={}
for label,points in [('actual_baseline',old),('joint_model',new)]:
 sinks=[(*points[n],1.)for n in core_names];load,far,assignment=assign(taps,sinks,cap,radius,max_distance_um=radius)
 bad=[dict(tap=taps[j][0],load=load[j],far_um=far[j])for j in range(len(taps))if load[j]>cap or far[j]>radius+1e-8];viol=[]
 for n,j in zip(core_names,assignment):
  dist=abs(points[n][0]-taps[j][1])+abs(points[n][1]-taps[j][2])
  if dist>radius+1e-8:viol.append(dict(name=n,xy=points[n],tap=taps[j][0],distance_um=dist,moved=n in F))
 edge=collections.defaultdict(list)
 for n in edge_names:
  rt=roots[n];p=next(p for p in D.pins if p['name']==rt);xy=points[n];edge[rt].append((abs(xy[0]-p['x'])+abs(xy[1]-p['y']),n))
 reports[label]=dict(actual_native_FFs=len(roots),mission_FFs=len(core_names),forwarded_FFs=len(edge_names),declared_taps=len(taps),cap=cap,radius_um=radius,max_load=max(load),max_radius_um=max(far),bad_taps=bad,radius_violation_FFs=len(viol),moved_radius_violation_FFs=sum(v['moved']for v in viol),radius_witnesses=sorted(viol,key=lambda x:-x['distance_um'])[:20],tap_table=[dict(name=t[0],xy=t[1:],load=load[j],radius_um=far[j])for j,t in enumerate(taps)],forwarded_root_direct_reach_INFO={rt:dict(count=len(v),max_um=max(v)[0],witness=max(v)[1])for rt,v in edge.items()})
 with gzip.open(R/(label+'_mission_assignment_MODEL.json.gz'),'wt')as f:json.dump([dict(name=n,root=roots[n],tap=taps[j][0])for n,j in zip(core_names,assignment)],f,separators=(',',':'))
 print(label,'core',len(core_names),'edge',len(edge_names),'load',max(load),'far',max(far),'bad',len(bad),'movedbad',sum(v['moved']for v in viol),flush=True)
report=dict(scope='DISABLED actual52044FF unchanged-root geometric assignment using literal current source39 taps.assign; not a CTS/netlist/phase or reset qualification',source_plan_sha256=hashlib.sha256(planpath.read_bytes()).hexdigest(),native_root_counts=dict(collections.Counter(roots.values())),clock_ports_added=0,clock_control_FFs_added=0,reset_FFs_added=0,reset_release_cycles_delta=0,functional_pipeline_cycles_delta=0,fullgraph_counts_and_R2R_in_model_json=True,source_forwarded_domains_not_merged_into_mission=True,planned_source_sink_count_35382_is_not_actual_FF_count=True,results=reports,holds=['all original native missingPG95696/partialface/fill/GRT4843 holds remain','core assignment uses same native root domain; a future source geometry event must publish exact assignment coherently, no old nearest-binding transfer','forwarded-root direct distance is INFO only; actual source export/window and propagated clock phase required','all unchanged-domain clock/control/reset graph node counts remain identical; spatial graph edges checked in complete r2r model'])
(R/'clock_price.json').write_text(json.dumps(report,indent=2))
