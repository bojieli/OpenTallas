"""DISABLED source-only clock load sizing on immutable forecast slots. No EDA stage or measurements."""
from pathlib import Path
import json,sys,math,collections
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'tools'));import die_clock_128 as NL,core_infra_wire as W,core_infra_plan as CP,core_infra as CI
names=['BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R','BUFx8_ASAP7_75t_R','BUFx12_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={c:NL.lib_cells(c,R/'lib',names=names)for c in('TT','FF')};ns=json.load(open(R/'inputs/nodes.json'));groups=json.load(open(R/'inputs/FF_region_assignments.json'));pins=json.load(open(R/'inputs/actual_clock_pins.json'));macro=[p for p in pins if p['macro']];mcaps=json.load(open(R/'inputs/macro_clock_caps.json'));obs=[tuple(v/1000 for v in p['bbox_dbu'])for p in json.load(open(R/'inputs/post_place_snapshot.json'))['macros']];macby={p['name']:i for i,p in enumerate(json.load(open(R/'inputs/post_place_snapshot.json'))['macros'])};regions={g['node']:g for g in groups};leaves={g['node']:('FF',g)for g in groups}
for i,p in enumerate(macro):leaves[f'macro_leaf{i}']=('M',p)
for n in ns:n['master']=names[0]
def width(n):return CI.BUF_WIDTH_UM[n['master'].split('_ASAP7')[0]]
def xy(n):return[(n['bbox_dbu'][0]/1000+width(n)/2),(n['bbox_dbu'][1]+n['bbox_dbu'][3])/2000]
def indexes():
 by={n['name']:n for n in ns};ch=collections.defaultdict(list)
 for n in ns:
  if n['parent']in by:ch[n['parent']].append(n)
 def walk(n):
  yield n
  for c in ch[n['name']]:yield from walk(c)
 return by,ch,list(walk(by['hist_root']))
# Exact actual layer RC; no NDR or route measurement used.
rc_h=(.0118796,.1305);rc_v=(.0125096,.0925)
def net(n,c,ch):
 targets=[(p['name'],xy(p),libs[c][p['master']]['cap'])for p in ch[n['name']]];kind,g=leaves.get(n['name'],(None,None));omit=None
 if kind=='FF':targets.append(('open',xy(n),libs[c][names[-1]]['cap']))
 if kind=='M':
  targets.append(('macro',[x/1000 for x in g['xy_dbu']],mcaps[g['master']][c.lower()]['capacitance']));omit=macby[g['inst']]
 boxes=[r for i,r in enumerate(obs)if i!=omit]
 q=W.rooted_rc([xy(n)]+[t[1]for t in targets],[t[2]for t in targets],horizontal_rc=rc_h,vertical_rc=rc_v,obstacles=boxes,vertical_obstacles=boxes,clearance=0.,outline_um=[648,648])
 return targets,q
collapsed=[];selection_failures=[]
# Bottom-up capacitance selection precedes any latency prediction. Forecast slots reserve BUF24 width, so every
# selected smaller master fits the same immutable slot without moving any existing cell. Two passes settle centres.
for passn in range(2):
 by,ch,order=indexes()
 for n in reversed(order):
  data={c:net(n,c,ch)for c in('TT','FF')};load={c:d[1]['total_load_ff']for c,d in data.items()}
  valid=[m for m in names if all(libs[c][m]['delay'][1][0]<=load[c]<=libs[c][m]['delay'][1][-1]for c in('TT','FF'))]
  if valid:n['master']=valid[-1]
  elif n['kind']in('regional_branch','macro_branch','repeater')and len(ch[n['name']])==1:
   kid=ch[n['name']][0];kid['parent']=n['parent'];collapsed.append(dict(node=n['name'],load_ff=load,reason='unnecessary underloaded serial feed below every actual characterized input range'));ns.remove(n);by,ch,_=indexes()
  else:selection_failures.append(dict(node=n['name'],loads=load,reason='no characterized master; no load clamp'))
by,ch,order=indexes();report={};allroutes=[]
for c in('TT','FF'):
 arrival={'hist_root':0.};slew={'hist_root':40.};rows=[];nets=[]
 for n in order:
  targets,q=net(n,c,ch);lib=libs[c][n['master']];load=q['total_load_ff'];s0=slew[n['name']];d=NL._bilin(lib['delay'],s0,load);so=NL._bilin(lib['trans'],s0,load);outside=not(lib['delay'][1][0]<=load<=lib['delay'][1][-1]and lib['delay'][0][0]<=s0<=lib['delay'][0][-1]);nets.append(dict(node=n['name'],master=n['master'],load_ff=load,input_slew_ps=s0,NLDM_out_of_table=outside,wire_um=q['wire_um'],shared_wire_basis=q['basis']))
  for k,(dst,pt,cap)in enumerate(targets):
   a=arrival[n['name']]+d+q['target_elmore_ps'][k];s=math.hypot(so,2.2*q['target_elmore_ps'][k])
   if dst in by:arrival[dst]=a;slew[dst]=s
   elif dst=='open':
    g=regions[n['name']];t=CP.open_subtree(g['count'],g['rect'],c,xy(n),fanout=24);why=CP.calibration_check(g['count'],t['levels'],t['region_d_um'],g['rect'],[648,648]);rows.append(dict(node=n['name'],kind='FF_cts_open',sinks=g['count'],min_ps=a+t['min_ps'],mean_ps=a+t['mean_ps'],max_ps=a+t['max_ps'],calibration_reasons=why,region_reach_um=t['region_d_um'],cts_levels=t['levels']))
   else:rows.append(dict(node=n['name'],kind='macro_PIN',sinks=1,min_ps=a,mean_ps=a,max_ps=a,calibration_reasons=[]))
  if c=='TT':
   for k,t in enumerate(targets):allroutes.append(dict(driver=n['name'],target=t[0],points=[xy(n),t[1]],elmore_ps=q['target_elmore_ps'][k],rooted_parent=q['parent'],path_segments=q['paths']))
 lo=min(x['min_ps']for x in rows);hi=max(x['max_ps']for x in rows);mean=sum(x['mean_ps']*x['sinks']for x in rows)/31879;target=250 if c=='TT' else 202.5
 report[c]=dict(sinks=sum(x['sinks']for x in rows),min_ps=lo,mean_ps=mean,max_ps=hi,window_ps=hi-lo,target_ps=target,target_window_ps=40,target_pass=abs(mean-target)<=20 and hi-lo<=40,NLDM_out_nets=sum(x['NLDM_out_of_table']for x in nets),calibration_out_leaves=sum(bool(x['calibration_reasons'])for x in rows),leaves=rows,nets=nets)
for n in ns:n['xy_sized']=xy(n);n['bbox_sized_dbu']=[n['bbox_dbu'][0],n['bbox_dbu'][1],round(n['bbox_dbu'][0]+width(n)*1000),n['bbox_dbu'][3]]
O=dict(scope='DISABLED source-only load-sized/shared-wire successor, no GEN/CTS/GRT/RC/STA; forecast cells only',inherited_slots=285,planned_buffers=len(ns),collapsed_unnecessary_serial=collapsed,selection_failures=selection_failures,master_counts=dict(collections.Counter(n['master']for n in ns)),area_um2=sum(width(n)*.270 for n in ns),RC={'horizontal_M6':rc_h,'vertical_M7':rc_v,'source':'actualhistsetRC_rcx.tcl','wire_model':'native helper rooted directional MST/shared downstream capacitance; conservative unmerged paths/no vias/coupling/capacity qualification'},corners=report,holds=['actualM2-M7placedcongestion1.200horizontal/1.143column','all buffer slots inherited exact native-row/footprint legal forecast; every existingcell unchanged','macroclockPINarrivals only, nativechildclock/pinaccess remains physical prerequisite','no timing-measurement feedback, capclamp, table-extrapolation waiver, stagepadding, or targetchange'])
(R/'model.json').write_text(json.dumps(O,indent=2)+'\n');(R/'nodes.json').write_text(json.dumps(ns,indent=2)+'\n');(R/'routes.json').write_text(json.dumps(allroutes));print({k:v for k,v in O.items()if k not in('corners','holds')});print({c:{k:v for k,v in x.items()if k not in('leaves','nets')}for c,x in report.items()})
