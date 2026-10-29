#!/usr/bin/env python3
import json,sys,re,itertools,math
from pathlib import Path
W=Path(sys.argv[1]);P=Path(sys.argv[2]);O=Path(sys.argv[3]);O.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(W/'physical/die_plan/hbm_arch_cores'),str(W/'tools/die_plan')]
import types,master_plan as MP
# Execute the two unchanged pure geometry helpers only (host Python3.10 cannot parse unrelated Python3.12 SDC code).
_gsrc=(W/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py').read_text()
_ns={'re':re};exec(_gsrc[_gsrc.index('def macro_reg_guide_spec('):_gsrc.index('\ndef sdc(')],_ns)
G=types.SimpleNamespace(macro_reg_guide_spec=_ns['macro_reg_guide_spec'],relay_reg_guide_spec=_ns['relay_reg_guide_spec'])
M='ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77';macro='ot_sram_1r1w_128x256_m1_r2c2'
ps=json.load(open(P/'cores'/f'{M}__760.32x725.76__canon.json'));mw,mh=94.824,41.064
xy={0:[(55.008,408.144),(163.008,356.112),(163.008,408.144),(379.008,260.688),(540.000,120.000),(487.008,187.056)],1:[(271.008,304.080),(266.688,460.320),(271.008,386.352),(379.008,312.720),(487.008,239.088),(271.008,200.016)],2:[(55.008,200.016),(163.008,512.640),(55.008,304.080),(55.008,356.112),(163.008,200.016),(163.008,252.048)],3:[(163.008,304.080),(271.008,512.352),(487.008,408.144),(379.008,408.144),(487.008,356.112),(487.008,304.080)]}
placements=[];read=[];spacing=[]
for b,rows in xy.items():
 for r,(x,y) in enumerate(rows):
  placements.append(dict(inst=f'u_fcore.u_core.u_bank{b}.u_data.g_read[{r}].u_m',macro=macro,xy_um=[x,y],orient='R0'))
  if r<4:pp=[q for q in ps if q['name'].startswith(f'g_bank_k{b}_u_bank_read_data[') and r*32<=int(q['name'].split('[')[1][:-1])<(r+1)*32]
  elif r==5:pp=[q for q in ps if q['name'].startswith('inj_q[') and b*32<=int(q['name'].split('[')[1][:-1])<(b+1)*32]
  else:pp=[]
  if pp:
   span=max(abs(q['x']-(x+.012))+abs(q['y']-(y+ly)) for q in pp for ly in (1.632,26.136))
   read.append(dict(bank=b,reader=r,span_um=round(span,3),existing_capture_hops=2,minimax_lower_bound_um=round(span/2,3)))
for a,b in itertools.combinations(placements,2):
 x,y=a['xy_um'];u,v=b['xy_um'];gx=max(u-(x+mw),x-(u+mw));gy=max(v-(y+mh),y-(v+mh))
 if gx<10.8 and gy<10.8:spacing.append([a['inst'],b['inst'],gx,gy])
mg=G.macro_reg_guide_spec(placements,lambda m:(94824,41064),'g_wcopy',10,[4.32,4.32,756,721.44])
relays=json.load(open(sys.argv[4]));rg=G.relay_reg_guide_spec(relays['relays'],[(q['name'],q['x'],q['y']) for q in ps],mg,[4.32,4.32,756,721.44])
isl=[dict(name='entry',centre_um=[380.16,362.88])]+MP.restructure_islands(760.32,725.76,200)['islands']
drs=[]
for i,q in enumerate(isl):
 c=q['centre_um'];chosen=None
 for dx,dy in sorted(itertools.product(range(-20,21),repeat=2),key=lambda z:(abs(z[0])+abs(z[1]),z)):
  x,y=c[0]+dx*4.32,c[1]+dy*4.32;bb=[x-1.08,y-1.08,x+1.08,y+1.08]
  if bb[0]<4.32 or bb[1]<4.32 or bb[2]>756 or bb[3]>721.44:continue
  if any(bb[0]<a['xy_um'][0]+mw+2.16 and bb[2]>a['xy_um'][0]-2.16 and bb[1]<a['xy_um'][1]+mh+2.16 and bb[3]>a['xy_um'][1]-2.16 for a in placements):continue
  chosen=bb;break
 if chosen is None:raise ValueError('no driver site')
 drs.append(dict(island=i,original_centre_um=c,driver_rect_um=[round(v,3) for v in chosen],detour_um=round(abs((chosen[0]+chosen[2])/2-c[0])+abs((chosen[1]+chosen[3])/2-c[1]),3)))
# Existing read_data register banks bridge SRAM return to the face shell. Plan those flops before placement.
read_guides=[]
for rd in read:
 b,r=rd['bank'],rd['reader'];inst=f'u_fcore.u_core.u_bank{b}.u_data.g_read[{r}].u_m';x,y=xy[b][r]
 if r<4:pinre='^g_bank_k'+str(b)+'_u_bank_read_data\\[(?:'+'|'.join(str(n) for n in range(32*r,32*r+32))+')\\]$'
 else:pinre='^inj_q\\[(?:'+'|'.join(str(n) for n in range(32*b,32*b+32))+')\\]$'
 mm=[]
 for q in mg:
  if q['macro']==inst:
   for suffix,yy in [('',1.632),('.rawhi',26.136)]:
    t=dict(q);t['macro']=inst+suffix;t['macro_um']=[x+.012,y+yy,x+.012,y+yy];mm.append(t)
  else:mm.append(q)
 for q in rg+read_guides:mm.append(dict(macro='reserved_'+q['name'],macro_um=[0,0,0,0],box_um=q['box_um']))
 for q in drs:mm.append(dict(macro='driver_'+str(q['island']),macro_um=[0,0,0,0],box_um=q['driver_rect_um']))
 rs=dict(name=f'readbank{b}r{r}',members=[f'u_fcore.u_core.u_bank{b}.read_data[{n}]' for n in range(32*r,32*r+32)],pins=pinre,sinks=inst,half_um=4.32)
 rr=G.relay_reg_guide_spec([rs],[(q['name'],q['x'],q['y']) for q in ps],mm,[4.32,4.32,756,721.44])[0]
 read_guides.append(rr)
json.dump(read_guides,open(O/'read_guides.json','w'),indent=1)
maxhop=max(max(q['hop_pins_um'],q['hop_sinks_um']) for q in rg)
readhop=max(max(q['hop_pins_um'],q['hop_sinks_um']) for q in read_guides)
report=dict(module=M,outline_um=[760.32,725.76],profile=dict(MLAT=5,ALAT=4,WCOPY=1),inventory=dict(macros=len(placements),master=macro,readers=6,banks=4),spacing_failures=spacing,read_return=read,max_read_hop_lower_bound_um=max(q['minimax_lower_bound_um'] for q in read),write_relays=rg,max_write_centre_hop_um=maxhop,read_relay_guides=read_guides,max_read_relay_hop_um=readhop,drivers=drs,max_driver_detour_um=max(q['detour_um'] for q in drs),clock_contract_candidate='scalar clk_bank at current planned centre380.16,362.88, replacing76aliases; nonclockpins unchanged; die owner adoption pending',ft_pin_dx_um=1.08,verdict='PASS-ESTIMATE' if not spacing and maxhop<=405 and max(q['minimax_lower_bound_um'] for q in read)<=405 and readhop<=405 else 'FAIL-ESTIMATE',limits='Read value is lower bound from existing macro->read_dataFF->faceFF two hops, not actualplaced reach. Write guides use actual sourcepins, macrocentres and legal disjoint guide boxes; fullr2r census required afterplace. Clock parentisland metadata adoption pending.')
json.dump(dict(schema='opentallas.macro_placement.v1',placements=[dict(inst=q['inst'].removeprefix('u_fcore.'),macro=q['macro'],xy_um=q['xy_um'],orient=q['orient']) for q in placements]),open(O/'macros.json','w'),indent=1)
json.dump(report,open(O/'estimate.json','w'),indent=1)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
f,ax=plt.subplots(figsize=(10,10));cols=['#3478b8','#e89035','#4a9e68','#a36fb8']
for q in placements:
 b=int(re.search(r'u_bank(\d)',q['inst']).group(1));r=int(re.search(r'g_read\[(\d)',q['inst']).group(1));x,y=q['xy_um'];ax.add_patch(Rectangle((x,y),mw,mh,facecolor=cols[b],alpha=.7,edgecolor='black'));ax.text(x+mw/2,y+mh/2,f'B{b} R{r}',ha='center',va='center',fontsize=8)
for q in rg:
 x,y=q['point_um'];ax.plot(x,y,'kx');ax.text(x,y,q['name'],fontsize=6)
for q in drs:
 a,b,c,d=q['driver_rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='red'));x,y=q['original_centre_um'];ax.plot(x,y,'r.',markersize=3)
ax.set(xlim=(0,760.32),ylim=(0,725.76),aspect='equal',title=f'C25 fullcanon5/4/WCOPY1 candidate: {report["verdict"]}\n24 SRAMs, current outline, scalar centre entry candidate, clock/reset driver boxes red');ax.grid(alpha=.2);f.savefig(O/'candidate.png',dpi=140);print(json.dumps({k:report[k] for k in ['verdict','max_write_centre_hop_um','max_read_hop_lower_bound_um','max_driver_detour_um','spacing_failures','max_read_relay_hop_um']}))
