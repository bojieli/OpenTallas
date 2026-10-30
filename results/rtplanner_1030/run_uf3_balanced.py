import json,sys,subprocess,shutil
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-rtplanner-1030');OLD=Path('/srv/opentallas-scratch2/claude/codex-rtclock-1030');S=O/'src2';D=O/'balanced/ot_s81sl_cap_rt';U=O/'balanced_uf3/ot_s81sl_cap_rt';U.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(S/'tools/die_plan'),str(S/'results/core_lat_r7_1026')]
import core_family_slice as C,core_infra_htree as H,l0r_r7_model as M
for f in ('geo.txt','sites.txt','clkport.txt'):shutil.copy2(D/f,U/f)
libs=O/'libs';libs.mkdir(exist_ok=True)
for c in ('tt','ff'):
 p=libs/f'invbuf_{c}.lib'
 if not p.exists():p.symlink_to(OLD/f'asap7sc7p5t_INVBUF_RVT_{c.upper()}_nldm_220122.lib')
fit=S/'results/model_refit3_1026/uf_phys3_v1.json'
with (U/'d1.log').open('w') as f:
 r=subprocess.run([sys.executable,str(S/'results/core_lat_r9_1026/l0r_r9_d1.py'),str(D/'plan.json'),str(D/'geo.txt'),str(libs),str(fit),str(U/'plan_d1.json'),'--steps','60'],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit('R9 d1 failed '+str(r.returncode))
rec0=json.loads((D/'plan.json').read_text())[0];rec2=json.loads((U/'plan_d1.json').read_text())[0]
class Maze:
 def xy(self,p):return p
_,_,sinks,_=C.read_macro_geo(D/'geo.txt');pts={q[2]+'/'+q[3]:q for q in sinks}
P=dict(mz=Maze(),nodes=rec0['nodes_xy'],wires=[],land={},leafsinks={u:[pts[k] for k in ks] for u,ks in rec0['leaf_sinks'].items()},sinkcap=rec0['sinkcap'])
for w in rec0['wire_paths']:
 P['wires'].append(dict(w,cells=w['paths']))
 last=w['edge']+'_r'+str(len(w['segs'])-2) if len(w['segs'])>1 else w['edge']+'_br'
 if w['edge'] not in P['leafsinks']:P['land'][last]=(w['segs'][-1],w['edge'])
cells=sorted(set(C.ENV+[n[3] for n in P['nodes']]))
L={c:H.lib_cells(str(libs/f'invbuf_{c.lower()}.lib'),cells) for c in ('TT','FF')}
rr=.5*(.0180365+.0189935)*.8;cc=.5*(.178475+.164264)*.9;wc={i:'std' for i in range(1,10)}
baseline,_=M.model_x(P,L,rr,cc,wc)
for c in ('TT','FF'):
 for k in ('mean','window'):assert abs(baseline[c][k]-rec0[c][k])<=.03,(c,k,baseline[c][k],rec0[c][k])
C._PLANS[rec0['name']]=(P,L,rr,cc,wc)
rec=C.refresh_after_d1(rec0,rec2);(U/'plan.json').write_text(json.dumps([rec]))
cmd=[sys.executable,str(S/'tools/die_plan/core_plan_to_infra.py'),str(U/'plan.json'),'--sites',str(U/'sites.txt'),'--module','ot_s81sl_cap_rt','--clock-port','clk','--band','info','--ndr','none','--out',str(U/'slice.json')]
p=subprocess.run(cmd,capture_output=True,text=True);(U/'convert.log').write_text(p.stdout+p.stderr)
sl=json.loads((U/'slice.json').read_text()) if p.returncode==0 else None
ck=C.checks(rec,sl,U/'geo.txt')
if sl is None:ck['verdict']='FAIL';ck['fails'].append('converter rc '+str(p.returncode)+': '+(p.stdout+p.stderr)[-350:])
else:
 sl['islands'][0]['clock_pin']=None
 sl['native_input_preserved']=dict(layer='M5',xy_um=[129.612,129.36],outline_um=[259.2,129.6],note='Input stub pricing is required separately before physical; no IO relocation')
 (U/'slice_native_n.json').write_text(json.dumps(sl,indent=1)+'\n')
(U/'checks.json').write_text(json.dumps(ck,indent=1)+'\n')
print(json.dumps(ck,indent=1),flush=True)
