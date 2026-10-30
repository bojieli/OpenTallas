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
station_ok=np.ones(len(xy),bool)
def region(n,b): groups[n]=[round(float(x),3) for x in b]
def assign_box(n,b,reg):
 region(n,b); names[reg]=n
def station(reg,sources,targets,kind):
 sources=np.array(sources); targets=np.array(targets)
 ds=np.max(np.abs(xy[:,None,:]-sources[None,:,:]).sum(2),axis=1)
 dt=np.max(np.abs(xy[:,None,:]-targets[None,:,:]).sum(2),axis=1)
 cost=np.maximum(ds,dt); score=cost+used*.0001;score[(used>=16)|~station_ok]=np.inf
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
# One reduced-Y region contains all quarter state, including the direct WD cone.
# Relay bays are entirely outside these bodies, root, first-reset box and halos.
active=[]
for q,b in enumerate(ribbons):
 pts=macro_points(q,'wd');dx=np.maximum(abs(pts[:,0]-b[0]),abs(pts[:,0]-b[2]));margin=395-dx
 lo=max(b[1],float(np.max(pts[:,1]-margin)));hi=min(b[3],float(np.min(pts[:,1]+margin)))
 lo=math.ceil(lo/4.32)*4.32;hi=math.floor(hi/4.32)*4.32;assert hi>lo
 active.append((b[0],lo,b[2],hi))
ribbons=active
for q,b in enumerate(ribbons):region(f'q{q}',b)
reserved=[*ribbons,root,(578.88,25.92,587.52,34.56),*v['blocked']]
for b in reserved:
 station_ok &= ~((xy[:,0]+2.16>b[0]+1e-8)&(xy[:,0]-2.16<b[2]-1e-8)&(xy[:,1]+2.16>b[1]+1e-8)&(xy[:,1]-2.16<b[3]-1e-8))
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
for r in sorted(v['rows'],key=lambda x:-x['direct_um']):
 # op2 has two direct consumers: SRAM WD AND every own-quarter histogram bin.
 station(f'u_fcore.in_r[{r["bit"]}]',[r['source_um']],np.vstack([r['target_um'],corners(ribbons[r['quarter']])]),'native_ingest')
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
 bb=(b[0],lo,b[2],hi);bufbounds.append(bb)
allhist=np.vstack([corners(b) for b in ribbons]);thresholdmax=max(float(np.max(np.abs(allhist[:,None,:]-corners(groups[f'threshold{q}'])[None,:,:]).sum(2))) for q in range(4))
macro_rdrd=[]
for q in range(4):
 rd=[]
 for m in range(3):
  mac=macros[q,m]
  for bit in range(256 if m<2 else 80):
   for x0,y0,x1,y1 in ports[f'rd_out[{bit}]']:
    x,y=(x0+x1)/2,(y0+y1)/2
    if mac['orient']=='MY':x=w-x
    rd.append([mac['x']+x,mac['y']+y])
 macro_rdrd.append(float(np.max(np.abs(np.array(rd)[:,None,:]-macro_points(q,'wd')[None,:,:]).sum(2))))
islands={tuple(c['rect_um']) for c in json.load(open(K/'core_infra_plan.json'))['cells']};collisions=[]
for (q,m),b in macros.items():
 halo=(b['x']-4.32,b['y']-4.32,b['x']+w+4.32,b['y']+v['h']+4.32)
 for rect in islands:
  if min(halo[2],rect[2])>max(halo[0],rect[0]) and min(halo[3],rect[3])>max(halo[1],rect[1]):collisions.append(dict(quarter=q,macro=m,halo=halo,island=rect))
column_ys=sorted(b['y'] for (q,m),b in macros.items() if q<2)
min_channel=min(b-a-v['h'] for a,b in zip(column_ys,column_ys[1:]))
summary=dict(status='PLACEMENT MODEL ONLY; no PNR/STA/SIGNED claim',added_ff_vs_existing_candidate=0,added_cycles=0,old_quarter_capture_hard_failure_um=517.464,quarter_ribbons=ribbons,buffer_ribbons=bufbounds,root_controller=root,groups=len(groups),max_station_bay_ff=16,station_counts={k:sum(r['kind']==k for r in claims) for k in sorted({r['kind'] for r in claims})},max_station_box_leg_bound_um=max(r['box_leg_bound_um'] for r in claims),station_box_bound_gt405=sum(r['box_leg_bound_um']>405 for r in claims),hist_to_threshold_copy_worst_um=thresholdmax,macro_rd_to_any_quarter_ff_bound_um=max(rdbounds),buffer_to_any_meaningful_macro_wd_bound_um=395,limitations=['existing outer face FF offset/name survival must be checked on actual placement','source-register endpoint bounds do not prove combinational logic RC/clock/PG/STA','all mapped FF role coverage and capacity must be checked before place','native wrapper face stages are inherited, not new free stages'])
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(O/'groups.json').write_text(json.dumps(groups,indent=1)+'\n');(O/'register_groups.json').write_text(json.dumps(names,indent=1)+'\n');(O/'claims.json').write_text(json.dumps(claims,indent=1)+'\n')
south=[p for p in json.load(open(K/'pins.json')) if p.get('face')=='S' and not p['bus'].startswith('clk')]
summary.update(direct_same_quarter_sram_rd_to_wd_bound_um=max(macro_rdrd),macro_halo_island_collisions=collisions,min_same_column_macro_channel_um=min_channel,south_nonclock_ports=south)
def subtract(base,holes):
 holes=[(max(base[0],h[0]),max(base[1],h[1]),min(base[2],h[2]),min(base[3],h[3])) for h in holes if min(base[2],h[2])>max(base[0],h[0])+1e-8 and min(base[3],h[3])>max(base[1],h[1])+1e-8]
 ys=sorted({base[1],base[3],*(y for h in holes for y in [h[1],h[3]])});out=[]
 for y0,y1 in zip(ys,ys[1:]):
  merged=[]
  for x0,x1 in sorted((h[0],h[2]) for h in holes if h[1]<y1-1e-8 and h[3]>y0+1e-8):
   if merged and x0<=merged[-1][1]+1e-8:merged[-1][1]=max(merged[-1][1],x1)
   else:merged.append([x0,x1])
  x=base[0]
  for x0,x1 in merged:
   if x0>x+1e-8:out.append([x,y0,x0,y1])
   x=x1
  if base[2]>x+1e-8:out.append([x,y0,base[2],y1])
 return out
regions={n:[b] for n,b in groups.items()}
for q in range(4):regions[f'q{q}']=subtract(groups[f'q{q}'],[root])
regions['root']=subtract(root,[groups[f'threshold{q}'] for q in range(4)])
# Reservations exclude bay intersections by construction; root and quarter
# unions are punched exactly. Assert every pair of distinct region unions.
overlaps=[];flat=[(n,b) for n,bs in regions.items() for b in bs]
for i,(n,b) in enumerate(flat):
 for nn,bb in flat[i+1:]:
  if n!=nn and min(b[2],bb[2])>max(b[0],bb[0])+1e-7 and min(b[3],bb[3])>max(b[1],bb[1])+1e-7:overlaps.append((n,nn))
summary.update(region_overlap_pairs=overlaps,region_union_area_um2={n:round(sum((b[2]-b[0])*(b[3]-b[1]) for b in bs),3) for n,bs in regions.items() if not n.startswith('bay')},legal_station_bays=int(sum(station_ok)))
(O/'regions.json').write_text(json.dumps(regions,indent=1)+'\n')
(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
# Tcl array keys are literal hier names; one FF-only pass, no quadratic prefix scan.
lines=['set ::ot_sel_boxes {']+[' {%s} {%s}'%(n,' '.join(map(str,b))) for n,b in groups.items()]+['}','set ::ot_sel_roles {']+[' {%s} {%s}'%(reg,n) for reg,n in names.items()]+['}']
lines+=['set ::ot_sel_regions {']+[' {%s} {%s}'%(n,' '.join('{'+ ' '.join(map(str,b))+'}' for b in bs)) for n,bs in regions.items()]+['}']
(O/'selector_roles_data.tcl').write_text('\n'.join(lines)+'\n')
