import json,math,collections
from pathlib import Path
p=Path(__file__).parent
m=json.load(open(p/'prog_readmux.json'));w=json.load(open(p/'prog_Ewrite_cohort.json'));r=json.load(open(p/'prog_rows.json'))
core={c['name']:c for c in m['comb'] if c['master'].startswith(('NAND2x1_','OA21x2_','INVx1_'))}
writers={c['name'] for b in w['cohort'] for c in b['chain']}
moving=set(core)|writers
cells={c['name']:c for c in m['candidate_cells']+w['local_cells']+r['cells']}
fixed=[c for c in cells.values() if c['name'] not in moving]
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
placed=[]
index=collections.defaultdict(list)
def index_add(c):
 for yy in range(math.floor(c['box'][1]/.27),math.ceil(c['box'][3]/.27)):
  index[yy].append(c)
for c in fixed:index_add(c)
def free(box):
 return not any(overlap(box,c['box']) for yy in range(math.floor(box[1]/.27),math.ceil(box[3]/.27)) for c in index[yy])
def record(c,x,y,o,role):
 box=[round(x,6),round(y,6),round(x+c['box'][2]-c['box'][0],6),round(y+.27,6)]
 assert free(box),(c['name'],box)
 placed.append(dict(name=c['name'],master=c['master'],old_box=c['box'],box=box,orient=o,role=role));index_add(placed[-1])
# Pin-ordered four-column writer cells. Every candidate uses an actual row.
slots=[]
for row in r['rows']:
 y=row['origin'][1]
 if y<113.4-1e-6 or y>126.36+1e-6:continue
 for col in range(4):
  x=270.648+1.62*col
  box=[x,y,x+1.35,y+.27]
  if free(box):slots.append((y,col,x,row['orient']))
used=set();writer_report=[]
for b in sorted(w['cohort'],key=lambda z:z['piny']):
 inv,ff=b['chain'];opts=[]
 for i,(y,col,x,o) in enumerate(slots):
  if i in used:continue
  # The entire two-cell body must remain free after earlier placements.
  if not free([x,y,x+1.35,y+.27]):continue
  opts.append((abs(y+.135-b['piny']),i))
 assert opts,('writer capacity',b['bit'])
 _,i=min(opts);used.add(i);y,col,x,o=slots[i]
 o='MY' if o=='R0' else 'R180'
 record(inv,x,y,o,'write_restore');record(ff,x+.27,y,o,'write_capture')
 writer_report.append(dict(bit=b['bit'],pin_y=b['piny'],row_y=y,column=col,pin_to_pair_y=abs(y+.135-b['piny'])))
# Pack unique 3-gate read mux groups into the empty producer->output corridor.
rows={round(z['origin'][1],6):z for z in m['candidate_rows']}
for oi,out in enumerate(sorted(m['outputs'],key=lambda z:(z['ff']['box'][1],z['ff']['name']))):
 gates=sorted([core[n] for n in out['comb'] if n in core],key=lambda c:c['master'])
 assert len(gates)==3
 width=sum(c['box'][2]-c['box'][0] for c in gates)+.108
 opts=[]
 for y,row in rows.items():
  if abs(y-out['ff']['box'][1])>4.32:continue
  for xi in range(math.ceil(300/.054),math.floor((320-width)/.054)+1,2):
   x=round(xi*.054,6)
   if free([x,y,x+width,y+.27]):opts.append((abs(y-out['ff']['box'][1])*10+abs(x-(300+2.16*(oi%9))),x,y,row['orient']))
 assert opts,('mux capacity',out['ff']['name'])
 _,x,y,o=min(opts)
 for c in gates:
  record(c,x,y,o,'readmux_core');x+=c['box'][2]-c['box'][0]+.054
summary=dict(writer_pairs=len(writer_report),write_slots_available=len(slots),readmux_gates=len(core),moved_cells=len(placed),max_writer_y_error=max(x['pin_to_pair_y'] for x in writer_report),writer_columns=collections.Counter(x['column'] for x in writer_report),max_readmux_dy=max(abs(c['box'][1]-c['old_box'][1]) for c in placed if c['role']=='readmux_core'),actual_obstacle_cells=len(fixed),no_pnr_or_timing=True)
json.dump(dict(summary=summary,writer_report=writer_report,placements=placed,obstacles=fixed),open(p/'prog_static_proposal.json','w'),indent=2)
print(json.dumps(summary,indent=2))
