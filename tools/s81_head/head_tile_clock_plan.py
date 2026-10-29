#!/usr/bin/env python3
"""Fresh HEAD tile clock groups/pads, before build. No routed-result trimming.

Consumes current sink dump, an unpadded reg_spine plan, and matched h17 routed
calibration. Closes actual projected tap radius before fitting each new group.
"""
import argparse,json,math,re,sys
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import reg_spine as R

def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--footprint',type=Path,help='tap_footprint JSON (core_um, extra_keepouts_um): legalize whole pad+driver footprints, iterate pads to a fixed point');a=p.parse_args();d=a.directory
 spec=json.loads((d/'fresh_unpadded_spec.json').read_text());prior=json.loads((d/'unpadded_plan.json').read_text())
 sinks=R.load_sinks(d/'sinks.txt');taps=prior['taps'];attach=[t for t in spec['trunk'] if t[3]!='-' and t[0] not in spec.get('express',[])]
 spec['projected_radius_um']=spec['radius_um']
 taps=R.close_projected_radius(taps,sinks,spec['trunk'],spec)
 import copy;orig=copy.deepcopy(taps)
 if a.footprint:spec['tap_footprint']=json.loads(a.footprint.read_text())
 def regroup(taps):
  asg={n:min(range(len(taps)),key=lambda i:(abs(taps[i]['x']-x)+abs(taps[i]['y']-y),i)) for n,x,y in sinks}
  for t in taps:
   t['node']=min(attach,key=lambda n:(abs(n[1]-t['x'])+abs(n[2]-t['y']),n[0]))[0]
   group=[(x,y) for n,x,y in sinks if asg[n]==t['id']];t['sinks']=len(group);t['radius_um']=max(abs(x-t['x'])+abs(y-t['y']) for x,y in group)
  return asg
 asg={n:min(range(len(taps)),key=lambda i:(abs(taps[i]['x']-x)+abs(taps[i]['y']-y),i)) for n,x,y in sinks}
 for t in taps:
  t['node']=min(attach,key=lambda n:(abs(n[1]-t['x'])+abs(n[2]-t['y']),n[0]))[0]
  group=[(x,y) for n,x,y in sinks if asg[n]==t['id']];t['sinks']=len(group);t['radius_um']=max(abs(x-t['x'])+abs(y-t['y']) for x,y in group)
 assert max(t['radius_um'] for t in taps)<=spec['radius_um']
 # Physical prefix calibration is keyed by matched node/coordinates, never tap ID.
 prefix={}
 for line in (d/'calibration_trunk.txt').read_text().splitlines():
  f=line.split()
  if f[1].startswith('h16_n_'):prefix[f[1][6:]]=float(f[-1])
 old=json.loads((d/'calibration_plan.json').read_text());trunk={t[0]:t for t in spec['trunk']}
 oldtr={t[0]:t for t in old['trunk']}
 delta={n:abs(t[1]-trunk[t[3]][1])+abs(t[2]-trunk[t[3]][2])-abs(oldtr[n][1]-oldtr[t[3]][1])-abs(oldtr[n][2]-oldtr[t[3]][2]) for n,t in trunk.items() if t[3] not in ('-', 'CLK')}
 declared_moves={n.split(':',1)[1] for n in spec.get('prebuild_body_moves_um',{}) if n.startswith('trunk:')}
 assert {n for n,t in trunk.items() if t[1:3]!=oldtr[n][1:3]}<= {'HR0'}|declared_moves
 gold=json.loads((ROOT/'tools/die_plan/model_corr_golden.json').read_text())['raw_rows']
 stage={}
 for corner in ('TT','FF'):
  rows=[r for r in gold if r['case']=='bufx4_dly2_d32' and r['corner']==corner and r['src_edge']=='rise'];lo=min(rows,key=lambda r:r['depth']);hi=max(rows,key=lambda r:r['depth']);stage[corner]=(hi['spice_ps']-lo['spice_ps'])/(hi['depth']-lo['depth'])
 def feat(t, tree=None):
  n=(tree or trunk)[t['node']];stub=abs(t['x']-n[1])+abs(t['y']-n[2]);return [1,stub,math.log2(max(1,t['sinks'])),t['radius_um']]
 model={};pred={}
 for corner,scale,target in [('TT',1.,525.),('FF',.81,425.25)]:
  means={int(m[1]):float(m[2]) for line in (d/f'calibration_{corner}.txt').read_text().splitlines() if (m:=re.search(r'^tap\s+(\d+).* mean\s+([\d.]+)',line))}
  X=np.array([feat(t,oldtr) for t in old['taps']]);y=np.array([means[t['id']]-t['pad']*stage[corner]-scale*prefix[t['node']] for t in old['taps']]);coef,res=nnls(X,y)
  model[corner]=dict(prefix_scale=scale,local_coefficients=coef.tolist(),calibration_max_residual_ps=float(max(abs(X@coef-y))),stage_ps=stage[corner],target_ps=target)
  pred[corner]=[float(scale*prefix[t['node']]+coef[1]*delta.get(t['node'],0)+np.dot(feat(t),coef)) for t in taps]
 def fitpads(taps):
  pred={}
  for corner,scale,target in [('TT',1.,525.),('FF',.81,425.25)]:
   coef=np.array(model[corner]['local_coefficients']);pred[corner]=[float(scale*prefix[t['node']]+coef[1]*delta.get(t['node'],0)+np.dot(feat(t),coef)) for t in taps]
  return pred
 history=[]
 for it in range(8 if a.footprint else 1):
  if it:
   pads={t['id']:t['pad'] for t in taps};taps=copy.deepcopy(orig)
   for t in taps:t['pad']=pads[t['id']]
   taps=R.legalize_tap_footprints(taps,spec);asg=regroup(taps);pred=fitpads(taps)
  before=[t.get('pad') for t in taps]
  for i,t in enumerate(taps):
   pad=min(range(33),key=lambda p:sum(((pred[c][i]+p*stage[c]-model[c]['target_ps'])/model[c]['target_ps'])**2 for c in ('TT','FF')));t['pad']=pad;t['predicted_ps']={c:round(pred[c][i]+pad*stage[c],2) for c in ('TT','FF')}
  history.append(sum(t['pad'] for t in taps))
  if it and before==[t['pad'] for t in taps]:break
 else:
  if a.footprint:raise SystemExit('footprint/pad iteration did not reach a fixed point: '+str(history))
 if a.footprint:assert max(t['radius_um'] for t in taps)<=spec['radius_um'],'footprint move broke radius'
 spec['pads']={str(t['id']):t['pad'] for t in taps};spec['note']='Fresh actual3_place groups; projected-radius refinement; prebuild h17 matched-prefix and qualifiedspice BUFx4 calibration. No postbuild trimming.'
 R.write(str(d),spec['trunk'],taps,asg,spec);(d/'reg_spine.json').write_text(json.dumps(spec,indent=2)+'\n')
 report=dict(sinks=len(sinks),taps=len(taps),max_radius_um=max(t['radius_um'] for t in taps),max_sinks=max(t['sinks'] for t in taps),min_sinks=min(t['sinks'] for t in taps),pads=sum(t['pad'] for t in taps),model=model,predicted_ranges={c:[min(t['predicted_ps'][c] for t in taps),max(t['predicted_ps'][c] for t in taps)] for c in ('TT','FF')},assumptions=['Matched physical h17 BUFx24 trunk prefixes; changed tap loads only modeled by new local group fit.','FF prefix scales TT by0.81: planning approximation, actual dualcorner measurement required.','NNLS local-tree delay vs stub/log2sinkcount/radius calibrated to h17 after subtracting old pad physical stage delay.','BUFx4 rise-stage slope from qualified model_corr golden SPICE, bothcorners; no BUFx24factor applied to BUFx4.','HR0 inherited illegal ideal site660,690 moved to legal uppercrossbar660,717; prefix wirelength difference modeled, actual legalclocksites required.', 'Existing macro early-tap paths unchanged, stagesA6/B4 retained; actual corepin insertion must be remeasured.','Plan only; no timing closure or signoff claim.'])
 (d/'planning_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
