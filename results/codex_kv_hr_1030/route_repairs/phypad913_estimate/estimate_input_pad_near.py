from pathlib import Path
import re,json,collections,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;normalize=lambda x:x.replace('\\','')
v=(P/'3_place.v').read_text();cells={}
for m in re.finditer(r'(?m)^\s*(\S+_ASAP7_75t_R)\s+(\S+)\s*\((.*?)\);',v,re.S):
 master,name,body=m.groups();ports={a:normalize(b.strip()) for a,b in re.findall(r'\.(\w+)\s*\(([^)]+)\)',body)};cells[normalize(name)]=(master,ports)
loads=collections.defaultdict(list);drivers={}
for n,(m,ports) in cells.items():
 if m.startswith(('BUF','HB','INV')) and 'Y' in ports and 'A' in ports:
  loads[ports['A']].append(n);drivers[ports['Y']]=n
rows=[l.split('\t') for l in(P/'negative_hold_endpoints.tsv').read_text().splitlines()];rows=[r for r in rows if r[0]!='rst_n[0]'];assert len(rows)==len({r[1]for r in rows})==886
raw=(P.parent/'geom_phypadhb100/geom.tsv').read_text().splitlines();boxes={};occ=collections.defaultdict(list)
for line in raw:
 a=line.split('\t')
 if a[0]!='C':continue
 name=normalize(a[8]);box=list(map(float,a[4:8]));boxes[name]=box
 for rr in range(math.floor(box[1]/.27+1e-5),math.ceil(box[3]/.27-1e-5)):occ[rr].append((box[0],box[2]))
for rr in occ:occ[rr].sort()
def count_hb(sp,target):
 todo=[(sp,0,[])];seen=set()
 while todo:
  net,count,path=todo.pop()
  if net in seen:continue
  seen.add(net)
  if cells[target][1]['D']==net:return count,path
  for n in loads[net]:todo.append((cells[n][1]['Y'],count+int(cells[n][0].startswith('HB4')),path+[n]))
 raise ValueError((sp,target))
def place(py,anchor=64.8):
 rr=round(py/.27);points=[]
 for dr in range(-16,17):
  row=rr+dr;y=row*.27
  if y<4.32 or y+.27>90.72:continue
  cur=4.32 if anchor<50 else 50.004
  for lo,hi in sorted(occ[row])+[(50 if anchor<50 else 72.9,50 if anchor<50 else 72.9)]:
   end=min(lo,50 if anchor<50 else 72.9);low=math.ceil(cur/.054-1e-7)*.054;high=math.floor((end-.378)/.054+1e-7)*.054
   if high>=low:
    x=max(low,min(high,round(anchor/.054)*.054))
    if 65<=y<=89 and x+.378>70.2:continue
    points.append((abs(x-anchor)+abs(y-py),x,y,row))
   cur=max(cur,hi)
 if not points:raise ValueError(('no footprint',py))
 _,x,y,row=min(points);occ[row].append((x,x+.378));return [round(x,6),round(y,6)]
plan=[];total_added=0;max_total=0;wire=0
for sp,ep,slack in sorted(rows,key=lambda r:float(r[2])):
 target=normalize(ep.rsplit('/',1)[0]);n=math.ceil((-float(slack)+5)/33.8167);old,path=count_hb(sp,target);max_total=max(max_total,old+n);lastnet=cells[target][1]['D'];drv=drivers[lastnet]
 sb=boxes[drv];tb=boxes[target];src=[(sb[0]+sb[2])/2,(sb[1]+sb[3])/2];dst=[(tb[0]+tb[2])/2,(tb[1]+tb[3])/2];new=[place(dst[1],min(72.5,dst[0]-1.08)-j*.54)for j in range(n)];centres=[[x+.189,y+.135]for x,y in new];points=[src]+centres+[dst]
 extra=sum(abs(b[0]-a[0])+abs(b[1]-a[1])for a,b in zip(points,points[1:]))-(abs(dst[0]-src[0])+abs(dst[1]-src[1]));wire+=extra;total_added+=n
 plan.append({'startpoint':sp,'endpoint':ep,'hold_slack_ps':float(slack),'existing_hb4':old,'added_hb4':n,'sites':new,'old_final_driver':drv,'estimated_extra_L1_wire_um':round(extra,6),'points':points})
counts=collections.Counter(p['added_hb4']for p in plan);report={'status':'ESTIMATE_ONLY_NOT_BUILT','negative_raw_paths':900,'negative_unique_endpoints':900,'negative_unique_input_ports':887,'data_endpoints':886,'async_reset_endpoints_separate':14,'new_hb4_count':total_added,'new_hb4_area_um2':total_added*.10206,'existing_plus_new_hb4_max':max_total,'approved_helper_default_max':4,'ff_min_table_delay_ps':33.8167,'margin_ps':5,'per_capture_new_counts':dict(counts),'total_extra_L1_wire_estimate_um':round(wire,6),'max_extra_L1_wire_estimate_um':max(p['estimated_extra_L1_wire_um']for p in plan),'strict_fixed_old_cells_estimate':'all913newfootprintsfitrelativecapturebay<=72.9; NEy65..89 excludesx>70.2;rowdelta<=4.32;controlsplacedlocally; actualPG/tap/detailedplacementNOTRUN','clock_neighbor_coupling':'NOT_QUALIFIED; oldfixedclockRC maychange due new DATA context; noSTA/DRTqualificationclaim','pad_source_and_target':'insertonlyonexistingcaptureD nets; allFF/pins/clocks same; preserve61shorteningchainstructures','captures':plan}
(P/'input_pad_near_estimate.json').write_text(json.dumps(report,indent=1)+'\n');print({k:v for k,v in report.items()if k!='captures'})
fig,ax=plt.subplots(figsize=(9,10));ax.add_patch(Rectangle((0,0),86.4,95.04,fill=False,lw=2));ax.add_patch(Rectangle((71.229,66.588),8.835,20.336,fill=False,ec='red',lw=1.5))
for box in boxes.values():
 if box[0]>=48:ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fc='lightgrey',ec='none'))
for p in plan:
 for x,y in p['sites']:ax.add_patch(Rectangle((x,y),.378,.27,fc='purple',ec='none'))
 pts=p['points'];ax.plot([q[0]for q in pts],[q[1]for q in pts],color='orange',lw=.2,alpha=.1)
ax.set(xlim=(47,88),ylim=(0,96),aspect='equal',xlabel='um',ylabel='um');ax.set_title(f'913 additional HB4 footprint estimate only\nExisting cells fixed; extra L1wire{wire/1000:.1f}mm; clockcouplingUNQUALIFIED')
fig.tight_layout();fig.savefig(P/'input_pad_near_estimate.png',dpi=160)
