from pathlib import Path
import sys,json,math
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;D=g.Design(str(P/'geom.tsv'));old=json.load(open('/srv/opentallas-scratch/claude/codex-kv-hroot-band-prep-2140/existing_r2r_failures.json'));byname={c[6]:c for c in D.cells.values()};out=[]
for z in old['captures']:
 a,b=g.ctr(byname[z['launch']]),g.ctr(byname[z['capture']]);dist=abs(a[0]-b[0])+abs(a[1]-b[1]);out.append(dict(z,final_distance_um=round(dist,4),delta_um=round(dist-z['distance_um'],4)))
(P/'all19_final_comparison.json').write_text(json.dumps(out,indent=1)+'\n');assert all(x['delta_um']==0 for x in out)
fig,ax=plt.subplots(figsize=(11,6))
for c in D.cells.values():
 if c[4]<1280 or c[2]>1450 or c[5]<0 or c[3]>130:continue
 target='u_cland_i_kvpc_Q_N_o_next/' in c[6];color='#ca2860'if target and c[0]=='S'else'#e4a346'if target else'#91a2a8'
 ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor=color,edgecolor='none',alpha=.85if target else.35))
ax.add_patch(Rectangle((1326.24,86.4),86.4,34.56,fill=False,edgecolor='#187fb8',lw=2))
for p in D.pins:
 if p['name'].startswith('i_kvpc_Q_N_o_next['):ax.plot(p['x'],p['y'],'k.',ms=2)
ax.set(xlim=(1280,1450),ylim=(-5,130),xlabel='x(um)',ylabel='y(um)',title='ACTUAL native HROOT completed FF-only PLACE\n1585 target FFs packed; all unrelated FF endpoints frozen; all19 residual path distances unchanged\nOrange combinational cells redistributed by GPL/DPL; GRT remains blocked')
ax.grid(alpha=.15);fig.tight_layout();fig.savefig(P/'final_target.png',dpi=160)
print('all19 exact unchanged')
