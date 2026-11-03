from pathlib import Path
import sys,json,csv
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design(str(P/'sc_batch_buffer_geometry.tsv'));by={c[6].replace(chr(92),''):c for c in D.cells.values()};T=json.load(open('/srv/opentallas-scratch/claude/codex-qc-sc-red-1101/sc_collapsed_batch_prep/targets.json'));err=[]
for m in T['moves']:
 c=by[m['instance']]
 if c[1]!=m['master']or max(abs(a-b)for a,b in zip(c[2:6],m['new_bbox']))>1e-5:err.append(m['instance'])
rows=[]
for z in T['chains']:
 ns=[z['source_ff']]+[e['sink']for e in z['edges']];pts=[list(g.ctr(by[n]))for n in ns];hops=[abs(b[0]-a[0])+abs(b[1]-a[1])for a,b in zip(pts,pts[1:])];rows.append(dict(source=z['source_ff'],endpoint=z['endpoint'],public=z['public_input_candidates'],points=pts,actual_centre_hops=hops,max_centre_hop=max(hops),old_first_hop=z['old_first_hop_um']))
native=list(csv.DictReader(open(P/'actual_chain.tsv'),delimiter='\t'));out=dict(scope='Actual closed native SC49 DATA geometry import only; no route/RC/timing credit',actual_selected_bodies=49,exact_target_body_mismatches=err,chain_count=len(rows),native_edges=len(native),max_actual_pin_hop_um=max(float(z['actual_pin_l1_um'])for z in native),max_actual_centre_hop_um=max(z['max_centre_hop']for z in rows),chains=rows);(P/'actual_tails.json').write_text(json.dumps(out,indent=1)+'\n')
choices=[0,1]+[i for i,z in sorted(enumerate(rows),key=lambda q:-q[1]['old_first_hop'])if not z['public']][:2]
fig,axs=plt.subplots(2,2,figsize=(10,12))
for ax,idx in zip(axs.flat,choices):
 z=rows[idx];pts=z['points'];xs=[a[0]for a in pts];ys=[a[1]for a in pts];x0,x1=max(0,min(xs)-8),min(244.56,max(xs)+8);y0,y1=max(0,min(ys)-8),min(514.08,max(ys)+8)
 context=[g.ctr(c)for c in D.cells.values()if c[4]>=x0 and c[2]<=x1 and c[5]>=y0 and c[3]<=y1]
 ax.scatter([c[0]for c in context],[c[1]for c in context],s=.3,color='.77',alpha=.4,rasterized=True)
 ax.plot(xs,ys,'o-',color='darkorange',ms=4,lw=1.2)
 for j,(x,y)in enumerate(pts):ax.text(x+1,y+1,str(j),fontsize=7)
 ax.set(xlim=(x0,x1),ylim=(y0,y1),aspect='equal',xlabel='um',ylabel='um',title=(str(z['public'])if z['public']else z['source'])+'\ncentre hops '+','.join(f'{h:.2f}'for h in z['actual_centre_hops']))
fig.suptitle('SC49 actual closed native DATA buffer import: selected chain tails\nAll FF/clock/pins/source unchanged; actual native pin hops ≤148.8965µm; no timing or route credit');fig.tight_layout(rect=(0,0,1,.94));fig.savefig(P/'actual_tails.png',dpi=150)
print({k:v for k,v in out.items()if k!='chains'})
