"""Repair actual internal95ps calibration HOLD on bestnative adf frame.

Shift only the two existing Tpqt repeaters on the SAME existing shortest path,
farthest-legal-first; no added wire/stages/masters or window-target tuning.
"""
from pathlib import Path
import copy,functools,json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);O=R/'tpqt_slew_geometry'
if O.exists():raise SystemExit('calibration geometry output exists')
O.mkdir();sys.path.insert(0,str(S/'tools/die_plan'))
import core_family_slice as F,core_plan_to_infra as C,core_infra as CI
base=json.loads((R/'final_model/plan_model.json').read_text())[0];r=copy.deepcopy(base);ns=json.loads((R/'final_model/slice_model.json').read_text())
core,_,_,macros=F.read_macro_geo(R/'baseline/geo.txt');mz=F.H.Maze(core,macros,keepout=r['macro_keepout_um'])
def cell(p):return tuple(round((x-o)/mz.G)for x,o in zip(p,core[:2]))
def man(a,b):return sum(abs(x-y)for x,y in zip(a,b))*mz.G
w=next(w for w in r['wire_paths']if w['edge']=='Tpqt');path=[]
for ps in w['paths']:
 for a,b in zip(ps,ps[1:]):
  a,b=cell(a),cell(b);assert a[0]==b[0]or a[1]==b[1]
  segment=[a];p=a
  while p!=b:
   q=(p[0]+(1 if b[0]>p[0]else -1)if b[0]!=p[0]else p[0],p[1]+(1 if b[1]>p[1]else -1)if b[1]!=p[1]else p[1])
   assert mz.step_ok(*p,*q);segment.append(q);p=q
  path.extend(segment[bool(path):])
assert len(set(path))==len(path);last=len(path)-1;k=len(w['segs']);assert k==3
oldnodes={n[0]:n for n in r['nodes_xy']};owned={'Tpqt_r0','Tpqt_r1'};occupied={cell(n[2])for n in r['nodes_xy']if n[0]not in owned};MAX=math.floor(70/mz.G+1e-9)
def legal(a,z):return(z-a)*mz.G<=70+1e-9 and(z-a)*mz.G<=1.1*man(path[a],path[z])+1e-9
@functools.lru_cache(None)
def choose(a,remaining):
 if remaining==1:return ()if legal(a,last)else None
 for z in range(min(last-remaining+1,a+MAX),a,-1):
  if path[z]in occupied or not mz.site_ok(*path[z])or not legal(a,z):continue
  tail=choose(z,remaining-1)
  if tail is not None:return(z,)+tail
 return None
indices=choose(0,k)
if indices is None:raise ValueError('no legal existing-stage partition on identical Tpqt path')
for i,j in enumerate(indices):oldnodes['Tpqt_r%d'%i][2]=list(mz.xy(path[j]))
at=[0]+list(indices)+[last];before=copy.deepcopy(w);w['segs']=[(z-a)*mz.G for a,z in zip(at,at[1:])];w['paths']=[[list(mz.xy(p))for p in path[a:z+1]]for a,z in zip(at,at[1:])]
assert abs(sum(before['segs'])-sum(w['segs']))<1e-8
assert r['frozen_masters']==base['frozen_masters']and r['leaf_sinks']==base['leaf_sinks']and r['sinkcap']==base['sinkcap']
r['name']=base['name']+'_tpqt_calibration_home';r['model']='NOT RUN; repair internal80ps calibration only; historical20windowFAIL retained, currentwindowtargetINFO12.3a';r['tpqt_calibration_repair']=dict(before_segments_um=before['segs'],after_segments_um=w['segs'],same_total_wire_um=sum(w['segs']),repeaters={u:oldnodes[u][2]for u in sorted(owned)},purpose='Actual13internalTTinput95.53ps violations, not window design-target tuning')
sl=C.convert(r,C.read_sites(R/'baseline/sites.txt'),'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1));sl.pop('clock_ndr',None)
for key in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event','islands','native_clock_pin_contract','native_input_preserved'):sl[key]=copy.deepcopy(ns[key])
sl['core_tree']['model_qualification']['band_policy']='info';sl['core_tree']['model_qualification']['window_policy']='info';sl['core_tree']['model_qualification']['status']='NOT RUN for calibration-repaired frame; all-buffer80 required'
p=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,p);checks=dict(scope='One calibration repair geometry, no new full model',repair=r['tpqt_calibration_repair'],counts_masters_memberships_depth_unchanged=True,all_other_nodes_fixed=True,converter=sl['plan_conversion'],native_pg=pg,all_segments70=all(x<=70+1e-9 for w in r['wire_paths']for x in w['segs']),all_detour1p10=all(x<=1.1*sum(abs(a-b)for a,b in zip(ps[0],ps[-1]))+1e-9 for w in r['wire_paths']for x,ps in zip(w['segs'],w['paths'])))
checks['verdict']='PASS'if checks['all_segments70']and checks['all_detour1p10']and pg['verdict']=='PASS'and sl['plan_conversion']['displacement_um']['max']<=2 else'FAIL'
(O/'plan_geometry.json').write_text(json.dumps([r])+'\n');(O/'slice_geometry_native.json').write_text(json.dumps(sl,indent=1)+'\n');(O/'geometry_checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
