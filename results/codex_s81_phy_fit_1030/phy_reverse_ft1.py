"""Packing estimate for existing reverse8-stage FT1; no source or cycle edits."""
import json, math
from pathlib import Path
from collections import defaultdict
R=Path(__file__).resolve().parent
base=json.loads((R/'phy_perbit_v3.json').read_text())
pins=json.loads((R/'ft1_native_pins.json').read_text())
W=2885.76; SX=.054; SY=.270
cells=[];chains=[];rows={}
for bit,layer,py in pins:
 width=1.404 if bit==514 else 1.08
 row=round((py-SY/2)/SY); ey=(row+.5)*SY;col=rows.get(row,0);rows[row]=col+1
 edge=4.32+width/2+col*1.62
 ch=[]
 for j in range(8):
  if j==7:x,y=W-edge,ey
  else:
   x=210+390*j+(bit//12)*1.62
   x=round((x-width/2)/SX)*SX+width/2
   y=(round(50/SY)+(bit%12)+.5)*SY
  box=[x-width/2,y-SY/2,x+width/2,y+SY/2]
  cells.append(dict(bus='ft1',stage=j,bit=bit,centre_um=[x,y],bbox_um=box));ch.append([x,y])
 hops=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(ch,ch[1:])]
 chains.append(dict(bit=bit,hops_um=hops,max_hop_um=max(hops),ring_band_to_first_ff_conservative_um=max(abs(ch[0][0]-x)+abs(ch[0][1]-y) for x in [17.28,41.04] for y in [17.28,128.988])))
allcells=[dict(r,bus='ft0',stage=int(j)) for j,rs in base['bit_stations'].items() for r in rs]+cells
bins=defaultdict(list);hits=[];pg=[]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-7 and min(a[3],b[3])>max(a[1],b[1])+1e-7
for n,c in enumerate(allcells):
 b=c['bbox_um'];ks=[(x,y) for x in range(math.floor(b[0]/2),math.floor(b[2]/2)+1) for y in range(math.floor(b[1]/2),math.floor(b[3]/2)+1)]
 for old in {i for k in ks for i in bins[k]}:
  if overlap(b,allcells[old]['bbox_um']):hits.append([old,n])
 for k in ks:bins[k].append(n)
 if any(overlap(b,d) for d in [[52.84,75.6,2682.92,1021.68],[127.44,75.6,2757.52,1021.68]]):pg.append(n)
r=dict(status='ESTIMATE_ONLY_NOT_PLACED',existing_reverse_stages=8,extra_reverse_cycles=0,combined_cells=len(allcells),reverse_cells=len(cells),max_reverse_hop_um=max(c['max_hop_um'] for c in chains),max_ring_band_to_first_ff_conservative_um=max(c['ring_band_to_first_ff_conservative_um'] for c in chains),combined_cell_overlaps=hits,combined_A_or_B_pg_clashes=pg,chains=chains,reverse_cells_allocated=cells,limitations=['Ring cell allocation not performed; band-to-first-FF reach conservative only','PG tapcell/via/clockcell obstacles and DPL/STA not qualified','Actual RTL FT1 chain unchanged; forward nine-stage remains candidate only'])
(R/'phy_reverse_ft1.json').write_text(json.dumps(r,indent=1)+'\n')
print({k:r[k] for k in r if k not in ['chains','reverse_cells_allocated','limitations']})
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(18,5))
for j in range(8):
 rs=[c for c in cells if c['stage']==j];ax.scatter([c['centre_um'][0] for c in rs],[c['centre_um'][1] for c in rs],s=2,label=f'FT1 {j}')
for j,rs in base['bit_stations'].items():ax.scatter([c['centre_um'][0] for c in rs],[c['centre_um'][1] for c in rs],s=.5,c='gray')
ax.axhline(75.6,c='r',ls='--',label='PG bottom (interior x only)');ax.set_xlim(0,W);ax.set_ylim(0,240);ax.set_title('PHY forward9 / reverse8 actual-sized bit stations: ESTIMATE ONLY');ax.set_xlabel('Local x um');ax.set_ylabel('Local y um');ax.legend(ncol=5);fig.tight_layout();fig.savefig(R/'phy_reverse_ft1.png',dpi=150)
