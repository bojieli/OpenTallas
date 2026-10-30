#!/usr/bin/env python3
"""Placement-only role model. Existing registers only; no timing/signoff claim."""
import sys, json, runpy, math
from pathlib import Path
import numpy as np
K,O=map(Path,sys.argv[1:3]); O.mkdir(parents=True,exist_ok=True)
sys.argv=[sys.argv[0],str(K),str(O/'ingest_initial')]
v=runpy.run_path(str(Path(__file__).with_name('ingest_estimate.py')))
xy,pins,macros,ports,w=v['xy'],v['pins'],v['macros'],v['ports'],v['w']
ribbons=[(246.24,4.32,293.76,225.18),(246.24,225.18,293.76,446.04),(306.72,4.32,349.92,225.18),(306.72,225.18,349.92,446.04)]
root=(259.2,190.08,336.96,259.2)
def corners(b):
 a,b,c,d=b; return np.array([(a,b),(a,d),(c,b),(c,d)])
used=np.zeros(len(xy),int); groups={}; names={}; claims=[]
def region(n,b): groups[n]=[round(float(x),3) for x in b]
def assign_box(n,b,reg):
 region(n,b); names[reg]=n
def station(reg,sources,targets,kind):
 sources=np.array(sources); targets=np.array(targets)
 ds=np.max(np.abs(xy[:,None,:]-sources[None,:,:]).sum(2),axis=1)
 dt=np.max(np.abs(xy[:,None,:]-targets[None,:,:]).sum(2),axis=1)
 cost=np.maximum(ds,dt); score=cost+used*.0001;score[used>=16]=np.inf
 i=int(np.argmin(score)); used[i]+=1; p=xy[i]; n='bay_%04d'%i
 region(n,(p[0]-2.16,p[1]-2.16,p[0]+2.16,p[1]+2.16)); names[reg]=n
 claims.append(dict(register=reg,kind=kind,point=p.tolist(),max_center_leg_um=round(float(cost[i]),3),box_leg_bound_um=round(float(cost[i])+4.32,3)))
 return p
for q,b in enumerate(ribbons): region('q%d'%q,b)
region('root',root)
def macro_points(q,kind):
 out=[]
 for m in range(3):
  mac=macros[q,m]
  keys=([f'wd_in[{bit}]' for bit in range(256 if m<2 else 80)] if kind=='wd' else ['r_ce_in','w_ce_in']+[f'{p}_addr_in[{bit}]' for p in ['r','w'] for bit in range(8)])
  for key in keys:
   for x0,y0,x1,y1 in ports[key]:
    x,y=(x0+x1)/2,(y0+y1)/2
    if mac['orient']=='MY':x=w-x
    out.append([mac['x']+x,mac['y']+y])
 return np.array(out)
# Capture controls do not belong to the quarter state region: IO is W-face.
for q,b in enumerate(ribbons):
 for field,n in [('op',4),('pass',2),('addr',8)]:
  for bit in range(n):
   p=pins[f'{field}[{bit}]'];targets=corners(b)
   if field=='op': targets=np.vstack([targets,macro_points(q,'wd'),macro_points(q,'control')])
   elif field=='addr':targets=np.vstack([targets,macro_points(q,'control')])
   station(f'u_fcore.grctrl[{q}].local_copy.{field}_q[{bit}]',[[p['x'],p['y']]],targets,'quarter_control')
 # Threshold D depends on ALL histogram quarters, so copies remain near root.
 x,y=[(276.48,211.68),(276.48,237.6),(319.68,211.68),(319.68,237.6)][q]
 region(f'threshold{q}',(x-4.32,y-4.32,x+4.32,y+4.32))
 # The second reset synchronizer must reach all quarter consumers AND raw async input.
rp=pins['rst_n']; raw=[rp['x'],rp['y']]; first=np.array([583.2,30.24]); region('reset_first',(578.88,25.92,587.52,34.56))
for reg in ['u_fcore.rst_sync[0]']+[f'u_fcore.grst[{q}].rs[0]' for q in range(4)]:names[reg]='reset_first'
station('u_fcore.rst_core_n',np.vstack([corners(groups['reset_first']),raw]),corners(root),'reset_global') # mapped alias for rst_sync[1]
for q,b in enumerate(ribbons):station(f'u_fcore.grst[{q}].rs[1]',np.vstack([corners(groups['reset_first']),raw]),corners(b),'reset_quarter')
for field,n in [('op',4),('pass',2),('addr',8),('k',10)]:
 for bit in range(n):
  p=pins[f'{field}[{bit}]'];station(f'u_fcore.{field}_r[{bit}]',[[p['x'],p['y']]],corners(root),'global_command')
# All 2368 native output bits, including valid predicates, receive a relay region
# bounded against EVERY source-quarter region corner. No valid mask.
for bit in range(2368):
 q=bit//592;p=pins[f'selected_line[{bit}]'];station(f'u_fcore.selected_line[{bit}]',corners(ribbons[q]),[[p['x'],p['y']]],'native_output')
for q in range(4):
 p=pins[f'selected_v[{q}]'];station(f'u_fcore.selected_v[{q}]',corners(ribbons[q]),[[p['x'],p['y']]],'native_valid_output')
p=pins['fault'];station('u_fcore.fault',corners(root),[[p['x'],p['y']]],'native_fault_output')
for r in sorted(v['rows'],key=lambda x:-x['direct_um']):station(f'u_fcore.in_r[{r["bit"]}]',[r['source_um']],[r['target_um']],'native_ingest')
# SRAM write-buffer placement intersection covers all meaningful WD endpoints.
bufbounds=[];rdbounds=[]
for q,b in enumerate(ribbons):
 lo,hi=b[1],b[3]
 for m in range(3):
  mac=macros[q,m]
  for bit in range(256 if m<2 else 80):
   for x0,y0,x1,y1 in ports[f'wd_in[{bit}]']:
    x,y=(x0+x1)/2,(y0+y1)/2
    if mac['orient']=='MY':x=w-x
    x+=mac['x'];y+=mac['y'];dx=max(abs(b[0]-x),abs(b[2]-x));margin=395-dx
    lo=max(lo,y-margin);hi=min(hi,y+margin)
   for x0,y0,x1,y1 in ports[f'rd_out[{bit}]']:
    x,y=(x0+x1)/2,(y0+y1)/2
    if mac['orient']=='MY':x=w-x
    x+=mac['x'];y+=mac['y'];rdbounds.append(float(np.max(np.abs(corners(b)-[x,y]).sum(1))))
 lo=math.ceil(lo/4.32)*4.32;hi=math.floor(hi/4.32)*4.32
 assert hi>lo,(q,lo,hi)
 bb=(b[0],lo,b[2],hi);region(f'buf{q}',bb);bufbounds.append(bb)
allhist=np.vstack([corners(b) for b in ribbons]);thresholdmax=max(float(np.max(np.abs(allhist[:,None,:]-corners(groups[f'threshold{q}'])[None,:,:]).sum(2))) for q in range(4))
summary=dict(status='PLACEMENT MODEL ONLY; no PNR/STA/SIGNED claim',added_ff_vs_existing_candidate=0,added_cycles=0,old_quarter_capture_hard_failure_um=517.464,quarter_ribbons=ribbons,buffer_ribbons=bufbounds,root_controller=root,groups=len(groups),max_station_bay_ff=16,station_counts={k:sum(r['kind']==k for r in claims) for k in sorted({r['kind'] for r in claims})},max_station_box_leg_bound_um=max(r['box_leg_bound_um'] for r in claims),station_box_bound_gt405=sum(r['box_leg_bound_um']>405 for r in claims),hist_to_threshold_copy_worst_um=thresholdmax,macro_rd_to_any_quarter_ff_bound_um=max(rdbounds),buffer_to_any_meaningful_macro_wd_bound_um=395,limitations=['existing outer face FF offset/name survival must be checked on actual placement','source-register endpoint bounds do not prove combinational logic RC/clock/PG/STA','all mapped FF role coverage and capacity must be checked before place','native wrapper face stages are inherited, not new free stages'])
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'groups.json').write_text(json.dumps(groups,indent=1)+'\n');(O/'register_groups.json').write_text(json.dumps(names,indent=1)+'\n');(O/'claims.json').write_text(json.dumps(claims,indent=1)+'\n')
print(json.dumps(summary,indent=2))
# Tcl array keys are literal hier names; one FF-only pass, no quadratic prefix scan.
lines=['set ::ot_sel_boxes {']+[' {%s} {%s}'%(n,' '.join(map(str,b))) for n,b in groups.items()]+['}','set ::ot_sel_roles {']+[' {%s} {%s}'%(reg,n) for reg,n in names.items()]+['}']
(O/'selector_roles_data.tcl').write_text('\n'.join(lines)+'\n')
