"""Same-outline BK_G macro-gap estimate. Input is immutable old placed census."""
import json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent
src=R/'bkg_e1_geom.tsv';cells=[]
for line in src.open():
 a=line.rstrip().split('\t')
 if a[0]=='C':cells.append(dict(kind=a[2],master=a[3],box=list(map(float,a[4:8])),name=a[8]))
old=[c for c in cells if c['kind']=='M'];shift=11.328
new=[]
for j,c in enumerate(sorted(old,key=lambda c:c['box'][1])):
 b=c['box'].copy();dy=-shift if j==0 else shift;b[1]+=dy;b[3]+=dy;new.append(dict(c,box=b,shift_y_um=dy))
def hit(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
affected=[c for c in cells if c['kind']!='M' and any(hit(c['box'],m['box']) for m in new)]
oldgap=old[1]['box'][1]-old[0]['box'][3];newgap=new[1]['box'][1]-new[0]['box'][3]
r=dict(status='STRUCTURAL_ESTIMATE_ONLY_NOT_LEGAL_PLACEMENT',source='intel1 s81ck/geom/s81ck2_bkg/geom.tsv',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),source_kit_rev='976208271a0',outline_um=[216,172.8],old_macros=old,candidate_macros=new,old_gap_um=oldgap,candidate_gap_um=newgap,shift_is_integer_0p192_um=round(shift/.192),old_horizontal_channel_ratio=1.85,same_demand_inverse_gap_ratio_estimate=1.85*oldgap/newgap,old_cells_newly_on_macros=len(affected),affected_dff=sum('DFF' in c['master'] for c in affected),changes=dict(external_pins=0,outline=0,RTL=0,cycles=0),limitations=['430+ existing cell locations need fresh legalization/GPL; no current placed fit claim','Channel ratio is a first-order capacity estimate; exact new routing census required','Current source/typed-memory ABI must be reconciled before fresh GEN','Full native clock with actual two SRAM clock pins required','Old GRT0 has50budget and converged8; proxy channel_h remains unresolved'])
(R/'estimate.json').write_text(json.dumps(r,indent=2)+'\n')
fig,axs=plt.subplots(1,2,figsize=(12,6),sharex=True,sharey=True)
for ax,ms,title in zip(axs,[old,new],['Original placed snapshot: channel_h1.85','Candidate macro move: NOT legal std placement']):
 ax.scatter([(c['box'][0]+c['box'][2])/2 for c in cells if c['kind']!='M'],[(c['box'][1]+c['box'][3])/2 for c in cells if c['kind']!='M'],s=.2,c='gray')
 if ms is new:ax.scatter([(c['box'][0]+c['box'][2])/2 for c in affected],[(c['box'][1]+c['box'][3])/2 for c in affected],s=2,c='red',label=f'{len(affected)}cells need relocation')
 for m in ms:
  b=m['box'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc='steelblue',alpha=.65,ec='black'));ax.text(b[0]+2,b[1]+5,m['name'],fontsize=8)
 ax.set_xlim(0,216);ax.set_ylim(0,172.8);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('um');ax.legend(loc='upper left') if ms is new else None
axs[0].set_ylabel('um');fig.suptitle('BK_G same-outline geometric proposal; source976208271a0, no source/physical adoption');fig.tight_layout();fig.savefig(R/'estimate.png',dpi=150)
print({k:r[k] for k in ['candidate_gap_um','same_demand_inverse_gap_ratio_estimate','old_cells_newly_on_macros','affected_dff']})
