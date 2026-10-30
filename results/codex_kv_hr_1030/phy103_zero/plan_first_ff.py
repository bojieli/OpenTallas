from pathlib import Path
import json,re,math,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;C=P.parent;raw=(P/'inputs/old_geom.tsv').read_text().splitlines();cells={a[8]:a for line in raw if (a:=line.split('\t'))[0]=='C'}
pins=json.load(open(P/'pins.json'));widths=collections.Counter(p['bus'] for p in pins);pm={p['bus']+(f'[{p["bit"]}]' if widths[p['bus']]>1 else ''):p for p in pins};old=[l.split('\t') for l in (P/'inputs/old_face_flops.txt').read_text().splitlines()]
core=(4.32,4.32,99.36,90.72);macro=(30.24,12.972,88.152,82.644);halo=(28.08,10.812,90.312,84.804);placed=[];occ=collections.defaultdict(list)
def overlaps(x,y,w,h):
 if x<core[0]-1e-6 or y<core[1]-1e-6 or x+w>core[2]+1e-6 or y+h>core[3]+1e-6:return True
 if x<halo[2] and x+w>halo[0] and y<halo[3] and y+h>halo[1]:return True
 row=round(y/.27)
 return any(x<r-1e-5 and x+w>l+1e-5 for l,r in occ[row])
def alloc(name,role,px,py,face):
 a=cells[name];w=round(float(a[6])-float(a[4]),6);h=round(float(a[7])-float(a[5]),6);candidates=[]
 if face=='W':
  rr=max(16,min(335,math.floor(py/.27)))
  for col in range(11):
   x=4.32+col*2.16
   for dr in range(-12,13):
    y=(rr+dr)*.27
    if not overlaps(x,y,w,h):candidates.append((abs(x+w/2-px)+abs(y+h/2-py),x,y))
 elif face=='N':
  for rr in range(0,16):
   y=90.72-(rr+1)*.27
   for dc in range(-80,81):
    x=round(px/.054+dc)*.054
    if not overlaps(x,y,w,h):candidates.append((abs(x+w/2-px)+abs(y+h/2-py),x,y))
 else:
  for col in range(11):
   x=26.46-col*2.16
   for rr in range(-12,13):
    y=round(py/.27+rr)*.27
    if not overlaps(x,y,w,h):candidates.append((abs(x+w/2-px)+abs(y+h/2-py),x,y))
 if not candidates:raise ValueError((name,role,px,py))
 _,x,y=min(candidates);x,y=round(x,6),round(y,6);occ[round(y/.27)].append((x,x+w));r={'cell':name,'role':role,'master':a[3],'bbox':[x,y,x+w,y+h],'target':[px,py],'estimated_bbox_L1_um':round(max(x-px,0,px-x-w)+max(y-py,0,py-y-h),6)};placed.append(r);return r
for name,face,ox,oy,port in old:
 pin=pm[port if port in pm else port[:-3] if port.endswith('[0]') else port];alloc(name,port,pin['x'],pin['y'],pin['face'])
lef=(P/'macro_views/ot_sram_1r1w_512x128_m1_r2c2/ot_sram_1r1w_512x128_m1_r2c2.lef').read_text();mp={}
for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1',lef,re.S):
 r=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2])
 if r:
  x,y,xx,yy=map(float,r.groups());mp[m[1]]=[30.24+(x+xx)/2,12.972+(y+yy)/2]
rr={}
for name,a in cells.items():
 if 'rr_d' in name and 'DFF' in a[3]:
  bit=int(re.search(r'\[(\d+)\\?\]',name)[1]);px,py=mp[f'rd_out[{bit}]'];rr[bit]=alloc(name,f'SRAM rd_out[{bit}] -> existing rr_d[{bit}]',px,py,'MACRO')
assert len(rr)==128
for r in placed:
 if r['role']=='r_cr[0]':r['cell']='hr_credit_capture_q$_DFF_PN0_'
byrole={r['role']:r for r in placed};paths=[]
for i in range(128):
 cap=byrole[f'rx_flit[{i+18}]'];x,y=cap['bbox'][:2];mx,my=mp[f'wd_in[{i}]'];face='W' if i<72 else'E'
 if face=='W':points=[[x,y],[24.30,y],[24.30,my],[mx,my]]
 else:points=[[x,y],[18.36,y],[18.36,6.48],[93.96,6.48],[93.96,my],[mx,my]]
 length=sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(points,points[1:]));paths.append({'source_port':f'rx_flit[{i+18}]','capture_ff':cap['cell'],'macro_pin':f'wd_in[{i}]','macro_face':face,'points':points,'estimated_L1_um':round(length,6)})
maxpin=max(r['estimated_bbox_L1_um'] for r in placed[:558]);maxwr=max(p['estimated_L1_um'] for p in paths)
summary={'status':'SOURCE_TIED_PLAN_ESTIMATE_NOT_PLACED','frozen_outline':[103.68,95.04],'core_inset':4.32,'macro_bbox':macro,'halo_bbox':halo,'public_first_ff_count':558,'existing_macro_read_capture_ff_count':128,'max_public_pin_to_capture_bbox_estimate_um':maxpin,'max_capture_to_write_macro_path_estimate_um':maxwr,'write_west_timed_bits':72,'write_east_timed_bits':56,'read_west_timed_bits':128,'east_mask_and_repair':'allmask128ones; rr_en/cr_en0; rr_addr18(newinternalwidth)/cr_sel14zeros','south_horizontal_cut_capacity_estimate':{'height_after_core_and_halo_um':6.492,'M2_pitch_um':.036,'M4_pitch_um':.048,'derating':.75,'tracks_before_PG_and_access':6.492*(1/.036+1/.048)*.75,'timed_write_cut':56},'macro_clkq_tt_ps':488.346542,'macro_clkq_delta_vs_mux2_ps':77.307961,'added_macro_cycles':0,'source_credit_capture_candidate_added_cycles':0,'binding_source':'qkd_hr_phy_adp.v:1030-1033 RX146:0 capture; RX145:18->write127:0; 1485-1497 RAM with mask/repair ties; existing rr_d andr_d stages preserved','cells':placed,'write_paths':paths}
(P/'mux1_ff_plan.json').write_text(json.dumps(summary,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(11,10));ax.add_patch(Rectangle((0,0),103.68,95.04,fill=False,lw=2));ax.add_patch(Rectangle((4.32,4.32),95.04,86.4,fill=False,ls='--',color='grey'));ax.add_patch(Rectangle((30.24,12.972),57.912,69.672,fc='lightsteelblue',ec='navy'));ax.add_patch(Rectangle((28.08,10.812),62.232,73.992,fill=False,ls=':',ec='navy'))
for pin in pins:ax.plot(pin['x'],pin['y'],'.',ms=1.8,color='black')
for r in placed:
 x,y,xx,yy=r['bbox'];color='darkorange' if r['role'].startswith('SRAM') else'green' if r['role'].startswith('tx') else'purple';ax.add_patch(Rectangle((x,y),xx-x,yy-y,fc=color,ec='none',alpha=.8))
for p in paths:
 pts=p['points'];ax.plot([p[0] for p in pts],[p[1] for p in pts],lw=.3,alpha=.25,color='crimson' if p['macro_face']=='E' else'purple')
ax.text(59.2,50,'512x128 mux1\nread128 W / write72 W +56 E\nmask/repair ties local',ha='center');ax.text(56,6.48,'56 timed WD bits through S access bay',ha='center',fontsize=8,backgroundcolor='white');ax.text(8,48,'W capture/logic band',rotation=90,ha='center');ax.text(59,88,'TX face registers',ha='center')
ax.set(xlim=(-4,108),ylim=(-4,100),aspect='equal',xlabel='um',ylabel='um');ax.set_title(f'Frozen PHY mux1:558 public first FFs +128 existing read captures\nPin→capture max{maxpin:.2f}um; capture→write path max{maxwr:.2f}um; estimate only')
fig.tight_layout();fig.savefig(P/'mux1_first_ff_plan.png',dpi=150)
print({k:v for k,v in summary.items() if k not in ['cells','write_paths']})
