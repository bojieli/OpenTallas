"""L1 bounded ONE further ordinary native-R7/NDR master proposal, maximum2total only. No qualification, ODB writes or physical launch."""
import sys,json,math,copy,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import core_family_slice as C
sys.path.insert(0,str(Path(__file__).parent));import joint_rvt as J
B=Path(sys.argv[2]);W=B/'l1_leaf25_model/dsdv_gunit_l1';F=json.load(open(B/'families_l1_leaf25.json'));fam=next(q for q in F['families']if'dsdv_gunit_l1'in q['members']);old=json.load(open(W/'plan.json'))[0]
name='l1_native_joint_proposal';rec=C.plan(W/'geo.txt',fam,B/'libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib',B/'libs/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib',name);P,libs,r,c,wc=C._PLANS[name]
assert rec['nodes_xy']==old['nodes_xy'] or json.loads(json.dumps(rec['nodes_xy']))==old['nodes_xy']
for cor in ['TT','FF']:
 for key in ['mean','window','leaf_out_slew_max']:assert abs(rec[cor][key]-old[cor][key])<.005,(cor,key)
base=tuple(P['nodes']);parents={n[0]:n[1]for n in base};cells={n[0]:n[3]for n in base}
def evaluate(assignments,need_slew):
 assert 0<=len(assignments)<=3
 P['nodes']=[(n[0],n[1],n[2],assignments.get(n[0],n[3]),n[4])for n in base]
 C.M7.model_x(P,libs,r,c,wc)
 means={};slews={}
 for cor,L in libs.items():
  I=P['_int'][cor];means[cor]={}
  out=[]
  for u,(cap,edges)in I['drv'].items():
   m=assignments.get(u,cells[u]);lib=L[m];si=I['slew'][u]
   delay=.5*(C.H.interp(lib['rise'],si,cap)+C.H.interp(lib['fall'],si,cap))
   so=.5*(C.H.interp(lib['trise'],si,cap)+C.H.interp(lib['tfall'],si,cap));out.append(so)
   if u in P['leafsinks']:means[cor][u]=I['arr'][u]+delay+edges[0][1]
  slews[cor+'_in']=max(I['slew'].values());slews[cor+'_out']=max(out)
 return means['TT'],means['FF'],slews
first=json.load(open(B/'l1_joint_native/proposal_single.json'))['proposal']['assignments'];assert first=={'T1033_br':'BUFx10_ASAP7_75t_R'}
raw_evaluate=evaluate
def evaluate(a,need):
 merged=dict(first);merged.update(a);return raw_evaluate(merged,need)
tt,ff,sl=evaluate({},True)
for cor,values in [('TT',tt),('FF',ff)]:assert abs((max(values.values())-min(values.values()))-json.load(open(B/'l1_joint_native/proposal_single.json'))['proposal']['key'][0])<3.0
log=[]
parent_path=lambda u: set()
def path(u):
 out=[]
 while parents.get(u) is not None:out.append(u);u=parents[u]
 return set(out)
corner,values=('TT',tt)if J.objective(tt,ff)==max(tt.values())-min(tt.values())else('FF',ff)
late=max(values,key=values.get);early=path(min(tt,key=tt.get))|path(min(ff,key=ff.get));eligible=sorted(path(late)-early-set(first));best=None
for node in eligible:
 for master in C.ENV:
  if master==cells[node]:continue
  t,f,ss=evaluate({node:master},True);score=J.objective(t,f);ok=score<J.objective(tt,ff)-J.GAIN and max(ss.values())<=80
  log.append(dict(node=node,old=cells[node],master=master,TT_window_ps=max(t.values())-min(t.values()),FF_window_ps=max(f.values())-min(f.values()),slews=ss,accepted_eligible=ok))
  key=(score,(max(t.values())-min(t.values()))+(max(f.values())-min(f.values())),node,master)
  if ok and(best is None or key<best['key']):best=dict(key=key,assignments=dict(first,**{node:master}),tt=t,ff=f,slews=ss,corner=corner,late_leaf=late)
p=best
P['nodes']=list(base);out=dict(scope='PROPOSAL ONLY nativeR7/NDR exactbaseline; no UF3 substitution, noqualification/P&R',baseline_reproduced=True,baseline_windows=dict(TT=max(tt.values())-min(tt.values()),FF=max(ff.values())-min(ff.values())),baseline_slew=sl,geometry_and_stage_and_cell_count_unchanged=True,source_joint_sha256=hashlib.sha256(Path(J.__file__).read_bytes()).hexdigest(),audit=log,proposal=p)
if p:
 out['master_changes']={n:dict(old=cells[n],new=m)for n,m in p['assignments'].items()};out['requires']='Root/FLOWsource+model+nativefootprint/PGreview beforeonequalification/physicalcohort'
Path(sys.argv[3]).write_text(json.dumps(out,indent=2));print('NATIVE_JOINT_PROPOSAL',out['baseline_windows'],'changes',out.get('master_changes'), 'scope',log[-1]if log else None)
