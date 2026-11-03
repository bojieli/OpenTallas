import sys,json,hashlib,re,math,collections,copy
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot')
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import geom_rules as g,landing_place as lp
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent; I=P/'inputs';D=g.Design(str(I/'geom.tsv')); bus='i_kvpc_Q_N_o_next';prefix='u_cland_'+bus+'/'
ring={k:c for k,c in D.cells.items() if prefix in c[6]};ffs={k:c for k,c in ring.items() if c[0]=='S'}
r=[1326.24,86.4,1412.64,120.96]
def intersects(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-7 and min(a[3],b[3])>max(a[1],b[1])+1e-7
obstacles={k:c for k,c in D.cells.items() if k not in ring and intersects(c[2:6],r)}
# Capacity witness only: actual FF master dimensions and original x/key locality, not a claimed OpenDB legal placement.
rows=collections.defaultdict(list)
for c in obstacles.values():
 for ri in range(math.floor((c[3]-r[1])/.27),math.ceil((c[5]-r[1])/.27)):
  rows[ri].append(c[2:6])
placements={};cursor=[0,0]; columns=int((r[2]-r[0])/2.7)
def key(k):
 n=ffs[k][6].replace(chr(92),'')
 m=re.search(r's_d\[(\d+)\]\[(\d+)\]',n)
 if m:return (int(m[2]),int(m[1]))
 m=re.search(r'dch\[(\d+)\].u_dsel/(y|di)\[(\d+)\]',n)
 if m:return (int(m[1])*64+ (int(m[3]) if m[2]=='y' else 32), 999 if m[2]=='y' else 998)
 return (230,997)
ordered=sorted(ffs,key=key)
for n,k in enumerate(ordered):
 c=ffs[k];w=c[4]-c[2];h=c[5]-c[3];found=False
 for slot in range(cursor[0],10000):
  row=slot%52;col=slot//52;x=r[0]+col*2.7;y=r[1]+row*.54;b=[x,y,x+w,y+h]
  if b[3]>r[3]+1e-7:raise RuntimeError('capacity exhausted')
  if any(intersects(b,a) for a in rows[int(round((y-r[1])/.27))]):continue
  placements[k]=b;cursor[0]=slot+1;found=True;break
 if not found:raise RuntimeError('no slot')
E=copy.deepcopy(D)
for k,b in placements.items():
 c=E.cells[k];E.cells[k]=c[:2]+tuple(b)+(c[6],)
base_pairs=[];new_pairs=[]
base=g.r2r_metrics(D,base_pairs);new=g.r2r_metrics(E,new_pairs)
basecaps={x['capture']:x for x in base_pairs};newcaps={x['capture']:x for x in new_pairs}
added=[x for n,x in newcaps.items() if n not in basecaps]
clocks=g.clock_metrics(D);clocksnew=g.clock_metrics(E)
entry_before=g.clock_entry_metrics(D,clocks);entry_after=g.clock_entry_metrics(E,clocksnew)
pins=[p for p in D.pins if re.fullmatch(bus+r'\[\d+\]',p['name'])]
maxpin=max(abs(p['x']-x)+abs(p['y']-y) for p in pins for x in (r[0],r[2]) for y in (r[1],r[3]))
pmap={int(re.search(r'\[(\d+)\]',p['name'])[1]):p for p in pins}
slotdist=[]
for k,bx in placements.items():
 m=re.search(r's_d\[\d+\]\[(\d+)\]',ffs[k][6].replace(chr(92),''))
 if m and int(m[1]) in pmap:
  p=pmap[int(m[1])];slotdist.append(abs(p['x']-(bx[0]+bx[2])/2)+abs(p['y']-(bx[1]+bx[3])/2))
max_slot=max(slotdist)
clk=[p for p in D.pins if p['name']=='fclk_in_'+bus+'[0]'][0]
maxclk=max(abs(clk['x']-x)+abs(clk['y']-y) for x in (r[0],r[2]) for y in (r[1],r[3]))
contract=json.load(open(I/'landing_contract.json'));old=copy.deepcopy(contract['bands'][bus]);b=contract['bands'][bus];b.pop('max_pin_to_band_hop_um',None);b.pop('resized_from_um',None);b.pop('resize',None);b.update(witness_correct_bit_storage_reach_um=round(max_slot,3),rect_um=r,ring_place='ff',fill_axis='x',spread=1.0,area_reserve_um2=(r[2]-r[0])*(r[3]-r[1]),placement='PREP only: wider shallow FF-only band; actual FIRM placement/PG and GRT NOTRUN')
assert lp.band_rects('kv3_hroot',bus,b,{'outline_um':[1900.8,838.08]})==[r]
tag='ring:'+bus+lp._spread(b)
(P/'landing_contract_candidate.json').write_text(json.dumps(contract,indent=2)+'\n')
text=(I/'landing_placement.tcl').read_text();oldline=next(l for l in text.splitlines() if ('{u_cland_'+bus+' {') in l)
newline='  {u_cland_'+bus+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}'
current_body=Path('/home/ubuntu/OpenTallas/tools/die_plan/landing_placement.tcl').read_text()
header=text.split('# Generated caller provides cland_groups:',1)[0]
(P/'landing_placement_candidate.tcl').write_text(header.replace(oldline,newline)+current_body)
result={'scope':'PREP capacity witness from exact actual TSV; not a placed OpenDB or route release','input_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in I.iterdir()},'old_band':old,'candidate_band':b,'ring_cells':len(ring),'ring_ffs':len(ffs),'released_ring_comb':len(ring)-len(ffs),'baseline_firm_ring_cells':sum(D.extra['status'].get(k)=='FIRM' for k in ring),'retained_nonring_obstacles_in_window':len(obstacles),'cell_body_witness_collisions':0,'witness_ff_bbox':[min(b[0] for b in placements.values()),min(b[1] for b in placements.values()),max(b[2] for b in placements.values()),max(b[3] for b in placements.values())],'max_any_buspin_to_window_corner_um':round(maxpin,3),'correct_bit_storage_reach_max_um':round(max_slot,3),'actual_storage_slots_checked':len(slotdist),'max_forwarded_clock_to_window_corner_um':round(maxclk,3),'r2r_before':base,'r2r_witness':new,'new_captures_over405':added,'clock_before':clocks,'clock_witness':clocksnew,'clock_entry_before':entry_before,'clock_entry_witness':entry_after,'source_clock_pin_graph_changes':0,'pdn':'Unchanged actual kit M1/M2 followpins, M5/M6 pitch4.32, M7 pitch8.64; zero hard macros in window. Actual PG connectivity remains prototype gate.','limitations':['Witness packs exact master cell bodies on .054x.27 site rows but does not assign actual orientation or rerun OpenDB FIRM packer.','Actual existing cland FF-only bit-major implementation chooses final slots; witness is capacity/reach bound only.','Released combinational cells still require real global placement and native GRT50; no predicted overflow pass.','Baseline19 r2r captures>405, pin/clock/aspect/fill and relay failures retained.']}
(P/'capacity_witness.json').write_text(json.dumps(result,indent=2)+'\n')
(P/'ff_target_witness.json').write_text(json.dumps([dict(id=k,name=ffs[k][6],master=ffs[k][1],old=list(ffs[k][2:6]),target=b) for k,b in placements.items()],indent=2)+'\n')
fig,axs=plt.subplots(1,2,figsize=(15,5),sharex=True,sharey=True)
for ax,design,title in zip(axs,[D,E],['Actual failed placement: all ring cells FIRM','PREP capacity witness: FF-only broad/shallow band']):
 for k,c in design.cells.items():
  if not intersects(c[2:6],[1280,0,1450,125]):continue
  color= '#cc2255' if k in ffs else ('#e8a44a' if k in ring else '#7e8994')
  ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor=color,edgecolor='none',alpha=.8 if k in ffs else .35))
 # In witness view old ring combinational geometry remains faint solely as a reminder of cells that GPL must move.
 ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='#187fb8',lw=2))
 for p in pins:ax.plot(p['x'],p['y'],'.',color='black',ms=2)
 ax.plot(clk['x'],clk['y'],'*',color='#147f18',ms=12,label='Forwarded clock unchanged')
 ax.set(xlim=(1280,1450),ylim=(-5,125),title=title,xlabel='x (um)');ax.grid(alpha=.15)
axs[0].set_ylabel('y (um)');axs[1].legend(loc='upper left',fontsize=8)
fig.suptitle('kv3_hroot Q_N ring — exact actual cell dimensions; PREP witness only, no CAD / no route credit\nPink:1585 FFs, orange:5350 ring combinational cells (released to GPL), gray:other actual cells')
fig.tight_layout();fig.savefig(P/'band_candidate_review.png',dpi=160)
print(json.dumps({k:result[k] for k in ['ring_ffs','correct_bit_storage_reach_max_um','r2r_before','r2r_witness']},indent=2));print('new captures',len(added))
