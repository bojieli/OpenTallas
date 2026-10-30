"""Price the preserved north input stub into a frozen macro-aware R7 tree."""
import sys,json,inspect
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-rtplanner-1030');OLD=Path('/srv/opentallas-scratch2/claude/codex-rtclock-1030');S=O/'src'
sys.path[:0]=[str(S/'tools/die_plan'),str(S/'results/core_lat_r7_1026')]
import core_infra_htree as H, l0r_r7_model as M,core_family_slice as C
variant=sys.argv[1];D=O/variant/'ot_s81sl_cap_rt';r=json.loads((D/'plan.json').read_text())[0]
class Maze:
 def xy(self,p):return p
_,_,sinks,_=C.read_macro_geo(D/'geo.txt')
pts={q[2]+'/'+q[3]:q for q in sinks}
P=dict(mz=Maze(),nodes=r['nodes_xy'],wires=[],land={},leafsinks={u:[pts[k] for k in ks] for u,ks in r['leaf_sinks'].items()},sinkcap=r['sinkcap'])
for w in r['wire_paths']:
 P['wires'].append(dict(w,cells=w['paths']))
 prev=w['edge']+'_r'+str(len(w['segs'])-2) if len(w['segs'])>1 else w['edge']+'_br'
 P['land'][prev]=(w['segs'][-1],w['edge'])
cells=sorted({n[3] for n in P['nodes']});libs={c:H.lib_cells(str(OLD/('asap7sc7p5t_INVBUF_RVT_'+c+'_nldm_220122.lib')),cells) for c in ('TT','FF')}
rr=.5*(.0180365+.0189935)*.8;cc=.5*(.178475+.164264)*.9
wc={i:r['wire'] for i in range(1,10)};base,_=M.model_x(P,libs,rr,cc,wc)
for co in base:
 for k in ('mean','window'):
  assert abs(base[co][k]-r.get('model_r7_info',r)[co][k])<=.03,(co,k,base[co][k],r[co][k])
entry=[129.612,129.36];root=r['nodes_xy'][0][2];length=sum(abs(a-b) for a,b in zip(entry,root))
wr=rr*(M.NDR_R if r['wire']=='ndr2w' else 1);wc_unit=cc*(M.NDR_C if r['wire']=='ndr2w' else 1)
arrival={co:wr*length*(wc_unit*length/2+libs[co][r['nodes_xy'][0][3]]['cin']) for co in libs}
P['entry_arrival']=arrival;P['entry_slew']={co:2.2*v for co,v in arrival.items()}
src=inspect.getsource(M.model_x);old="arr = {'root': 0.0}; slew = {'root': 0.0}"
assert src.count(old)==1
src=src.replace(old,"arr = {'root': P['entry_arrival'][corner]}; slew = {'root': P['entry_slew'][corner]}")
ns=dict(M.__dict__);exec(src,ns);full,_=ns['model_x'](P,libs,rr,cc,wc)
out=dict(scope='PLAN MODEL ONLY UNCHECKED; preserved native north clock input; no RTL/pin movement',native_entry_um=entry,root_um=root,trunk_um=length,wire=r['wire'],r_kohm_um=wr,c_ff_um=wc_unit,root_arrival_ps=arrival,root_slew_ps=P['entry_slew'],baseline=base,full_input=full,macro_sinkcap=r['sinkcap'],baseline_reproduces_frozen_model=True)
out['converted_root']='NOT RUN: timing model prevents conversion; stub currently to frozen model root'
if variant=='uf3':
 sys.path.insert(0,str(S/'results/core_lat_r8_1026'))
 import l0r_r8_uf3 as A
 for cell in cells:
  if cell not in A.U.SIZES:A.U.SIZES.append(cell)
 UL=A.U.load_libs(O/'libs');AP=A.PlanFromRecord(r,str(D/'geo.txt'));fit=json.loads((S/'results/model_refit3_1026/uf_phys3_v1.json').read_text());pm,pe=fit['PMAX'],fit['PMIN']
 cb=A.calibrated_summary(AP,UL,pm,pe)
 for co in cb:
  for key in ('mean','window'):assert abs(cb[co][key]-r[co][key])<=.03
 predictor=A.V3.predict3
 def input_seed(plan,libs,corner,*args,**kwargs):
  kwargs['s_root']=P['entry_slew'][corner]
  return predictor(plan,libs,corner,*args,**kwargs)
 A.V3.predict3=input_seed
 cf=A.calibrated_summary(AP,UL,pm,pe)
 for co in cf:
  for key in ('mean','leaf_mean_min','leaf_mean_max','sink_min','sink_max'):cf[co][key]=round(cf[co][key]+arrival[co],3)
 out['uf3_baseline']=cb;out['uf3_full_input']=cf;out['input_boundary_condition']='Same calibrated kernel with root slew from native wire Elmore, plus common native wire arrival; no predictor term refit'
(D/'native_entry_priced.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
