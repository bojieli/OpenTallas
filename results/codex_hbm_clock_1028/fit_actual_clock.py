"""Diagnostic raw OpenSTA parent-leg fit on retained route; no timing invocation."""
import json,sys,collections
from pathlib import Path
import numpy as np
base=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
t=json.load(open(base/'kit/clock/tree.json'));xy=t['sites'];par=t['parent_of'];fan=collections.Counter(par.values());report={'scope':'diagnostic raw OpenSTA units, same CKINVDCx16 retained route; no SPICE factor, no new STA','views':{}}
for corner in ('TT','FF'):
 rows={}
 for line in open(base/f'c_{corner}/arr_{corner}.txt'):
  p=line.split()
  if p and p[0]=='N':rows[p[1]]=[float(v) for v in p[2:6]]
 for k,view in enumerate(('LATE','EARLY')):
  X=[];Y=[];lens=[];details=[]
  for child,parent in par.items():
   if child not in rows or parent not in rows:continue
   a,b=xy[child],xy[parent];L=abs(a[0]-b[0])+abs(a[1]-b[1]);X.append([1,L,L*L,max(0,fan[parent]-1)]);Y.append(rows[child][k]-rows[parent][k]);lens.append(L);details.append(dict(child=child,parent=parent,n=1,actual_hop_um=L,parent_fanout=fan[parent],child_fanout=fan[child],parent_N=rows[parent],child_N=rows[child]))
  a=np.array(X);b=np.array(Y);coef=np.linalg.lstsq(a,b,rcond=None)[0];err=a@coef-b
  report['views'][corner+'_'+view]=dict(leg_coeff_ps_um_um2_fan=coef.tolist(),samples=len(Y),rms_ps=float(np.sqrt(np.mean(err**2))),max_abs_residual_ps=float(np.max(abs(err))),length_min_um=min(lens),length_max_um=max(lens),raw_delay_min_ps=min(Y),raw_delay_max_ps=max(Y),largest_residuals=[dict(details[int(i)],residual_ps=float(err[i]),observed_delta_ps=Y[int(i)],predicted_delta_ps=float((a@coef)[i])) for i in np.argsort(abs(err))[-8:][::-1]])
  mask=a[:,1]<=405.;aa=a[mask];bb=b[mask];cc=np.linalg.lstsq(aa,bb,rcond=None)[0];ee=aa@cc-bb
  selected=[d for d,m in zip(details,mask) if m]
  report['views'][corner+'_'+view]['guarded_405_domain']=dict(samples=len(bb),leg_coeff_ps_um_um2_fan=cc.tolist(),rms_ps=float(np.sqrt(np.mean(ee**2))),max_abs_residual_ps=float(max(abs(ee))),max_actual_child_input_slew_ps=max(d['child_N'][2] for d in selected),max_actual_child_output_slew_ps=max(d['child_N'][3] for d in selected),largest_residuals=[dict(selected[int(i)],residual_ps=float(ee[i]),observed_delta_ps=float(bb[i])) for i in np.argsort(abs(ee))[-5:][::-1]])
(out/'raw_parent_fits.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1))
