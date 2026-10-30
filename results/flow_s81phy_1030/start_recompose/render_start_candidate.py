from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;G=json.load(open(R/'start_graph_estimate.json'));B=json.load(open(R/'relay_bay_estimate.json'));P=json.load(open(R/'input.json'));parts={p['name']:p for p in P['partitions']}
def glob(p,q):return [p['origin_um'][0]+2885.76-q[0],p['origin_um'][1]+q[1]]
fig,ax=plt.subplots(figsize=(17,5))
for pn,p in parts.items():
 x,y=p['origin_um'];ax.add_patch(Rectangle((x,y),2885.76,1226.88,fill=False,ec='black',lw=1.5));a,b=glob(p,[52.84,75.6]),glob(p,[2682.92,1021.68]);ax.add_patch(Rectangle((min(a[0],b[0]),min(a[1],b[1])),abs(a[0]-b[0]),abs(a[1]-b[1]),fc='#eadfc9',ec='#ad8955',alpha=.8));ax.text(x+100,y+1050,pn+' PHY + PG guard10.8',fontsize=10)
for l in G['legs']:
 for pn in (parts if l['label'].startswith('dme_') else [None]):
  q=[glob(parts[pn],v) if pn else v for v in l['chain']];ax.plot([a[0] for a in q],[a[1] for a in q],lw=.6,c='#277da8',alpha=.65)
for z in B['placements']:
 b=z['bay'];ax.plot((b[0]+b[2])/2,(b[1]+b[3])/2,'.',c='#d94828',ms=3)
ax.plot(22976.082,699.3,'*',ms=12,c='green');ax.text(22976.082,740,'unchanged START b705, origin8',fontsize=9)
ax.set_xlim(22820,29050);ax.set_ylim(50,1430);ax.set_aspect('equal');ax.set_xlabel('die X (um), MY transforms retained');ax.set_ylabel('die Y (um)');ax.set_title('Candidate A clock + START/reset bays: 189/189 known-obstacle bays fit; max INV segment148.77um\nMODEL ONLY — release ES0 origin71..74 / ES1 134..137; full CA/RTL contract and physical qualification held',fontsize=12)
fig.tight_layout();fig.savefig(R/'start_candidate_A.png',dpi=150)
