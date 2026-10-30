"""L1 bounded native-R7/NDR proposal only. No qualification, ODB writes or physical launch."""
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
tt,ff,sl=evaluate({},True)
for cor,values in [('TT',tt),('FF',ff)]:assert abs((max(values.values())-min(values.values()))-old[cor]['window'])<=.0051
log=[];p=J.propose(tt,ff,parents,cells,C.ENV,evaluate,80.0,audit=log)
P['nodes']=list(base);out=dict(scope='PROPOSAL ONLY nativeR7/NDR exactbaseline; no UF3 substitution, noqualification/P&R',baseline_reproduced=True,baseline_windows=dict(TT=max(tt.values())-min(tt.values()),FF=max(ff.values())-min(ff.values())),baseline_slew=sl,geometry_and_stage_and_cell_count_unchanged=True,source_joint_sha256=hashlib.sha256(Path(J.__file__).read_bytes()).hexdigest(),audit=log,proposal=p)
if p:
 out['master_changes']={n:dict(old=cells[n],new=m)for n,m in p['assignments'].items()};out['requires']='Root/FLOWsource+model+nativefootprint/PGreview beforeonequalification/physicalcohort'
Path(sys.argv[3]).write_text(json.dumps(out,indent=2));print('NATIVE_JOINT_PROPOSAL',out['baseline_windows'],'changes',out.get('master_changes'), 'scope',log[-1]if log else None)
