import sys,json,inspect,copy
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/codex-s81phys-0336')
O=Path('/srv/opentallas-scratch2/claude/codex-s81phys-0336')
sys.path[:0]=[str(W/'tools/die_plan'),str(W/'results/core_lat_r7_1026')]
import core_infra_htree as H
import l0r_r7_model as M
r=json.load(open(O/'l0r_ndr/dsdv_gunit_l0r/plan.json'))[0]
class Maze:
 def xy(self,p): return p
pts={}
for ln in open(O/'l0r_ndr/dsdv_gunit_l0r/geo.txt'):
 f=ln.split()
 if f[0]=='SINK': pts[f[4]+'/'+f[5]]=(float(f[1]),float(f[2]),f[4],f[5],f[3])
P=dict(mz=Maze(),nodes=r['nodes_xy'],wires=[],land={},leafsinks={u:[pts[k] for k in ks] for u,ks in r['leaf_sinks'].items()})
for w in r['wire_paths']:
 P['wires'].append(dict(w,cells=w['paths']))
 prev=w['edge']+'_r'+str(len(w['segs'])-2) if len(w['segs'])>1 else w['edge']+'_br'
 P['land'][prev]=(w['segs'][-1],w['edge'])
cells=sorted({n[3] for n in P['nodes']})
libs={c:H.lib_cells(str(O/'libs'/('asap7sc7p5t_INVBUF_RVT_'+c+'_nldm_220122.lib')),cells) for c in ['TT','FF']}
rr=.5*(.0180365+.0189935)*.8; cc=.5*(.178475+.164264)*.9
wc={i:'ndr2w' for i in range(1,10)}
base,_=M.model_x(P,libs,rr,cc,wc)
for co in base:
 for k in ['mean','window']:
  assert abs(base[co][k]-r[co][k])<=.03,(co,k,base[co][k],r[co][k])
entry=[.06,100.236]; root=r['nodes_xy'][0][2]
length=sum(abs(a-b) for a,b in zip(entry,root))
arrival={co:rr*M.NDR_R*length*(cc*M.NDR_C*length/2+libs[co][r['nodes_xy'][0][3]]['cin']) for co in libs}
P['entry_arrival']=arrival; P['entry_slew']={co:2.2*v for co,v in arrival.items()}
src=inspect.getsource(M.model_x).replace("arr = {'root': 0.0}; slew = {'root': 0.0}","arr = {'root': P['entry_arrival'][corner]}; slew = {'root': P['entry_slew'][corner]}")
ns=dict(M.__dict__);exec(src,ns)
full,_=ns['model_x'](P,libs,rr,cc,wc)
out=dict(scope='PLAN MODEL ONLY UNCHECKED; native input trunk plus original sized NLDM tree, no RTL or pins changed',native_entry_um=entry,root_um=root,trunk_um=length,wire='ndr2w',r_kohm_um=rr*M.NDR_R,c_ff_um=cc*M.NDR_C,root_arrival_ps=arrival,root_slew_ps=P['entry_slew'],baseline=base,full_input=full,baseline_reproduces_frozen_model=True)
json.dump(out,open(O/'l0r_entry_priced.json','w'),indent=2)
print(json.dumps(out,indent=2))
