from pathlib import Path
import json,importlib.util
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
p=Path('/home/ubuntu/coord/tmp/codex-ves-grt-look-0818');a=json.load(open(p/'audit.json'));spec=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G);d=G.Design(p/'geom.tsv');new=set(json.load(open(p/'new_cell_ids.json')));by={c[6].replace('\\',''):i for i,c in d.cells.items()};cap=by['chunk_kk.term[6].add.u.x_bexp[1]$_DFF_P_'];chain=[cap];seen=set();cid=cap
while len(chain)<20:
 ins=[n for n,ck in d.cell_in.get(cid,[]) if not ck]
 if len(ins)!=1:break
 dr=d.nets[ins[0]][1]
 if not dr or dr[0]!='i' or dr[1] in seen:break
 cid=dr[1];seen.add(cid);chain.append(cid)
 if d.kind(cid)=='S':break
(p/'actual_original_worst_path_chain.json').write_text(json.dumps([dict(name=d.cells[i][6],master=d.cells[i][1],bbox=d.cells[i][2:6]) for i in reversed(chain)],indent=2))
pg=[]
for line in (p/'PG_upper.tsv').open():
 t=line.split()
 if len(t)==7 and t[2] in ['M4','M5']:pg.append((t[2],[int(v)/1000 for v in t[3:]]))
fig,axs=plt.subplots(1,2,figsize=(13,12),gridspec_kw={'width_ratios':[.85,1.15]});ax=axs[0];cs=list(d.cells.values());ax.scatter([G.ctr(c)[0] for c in cs],[G.ctr(c)[1] for c in cs],s=.12,c='slategray',alpha=.23,rasterized=True)
nc=[d.cells[i] for i in new];ax.scatter([G.ctr(c)[0] for c in nc],[G.ctr(c)[1] for c in nc],s=2,c='crimson',alpha=.75,label='1467 new HB4xp67 DATA hold cells')
for ly,r in pg:
 if ly=='M5':ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='goldenrod',alpha=.15,lw=0))
ax.scatter([82.092],[172.8],marker='*',c='darkorange',s=45);ax.add_patch(Rectangle((35,195),23,16,fill=False,ec='red'));ax.set(xlim=(0,172.8),ylim=(0,345.6),title='Actual saved GRT: 30810 FF, all rooted / depth8\n385.51um reach; 0>405; all337566PG0');ax.legend(loc='upper left',fontsize=7)
ax=axs[1];region=(35,57,195,211);cs=[c for c in cs if c[2]<57 and c[4]>35 and c[3]<211 and c[5]>195];ax.add_collection(PatchCollection([Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3]) for c in cs],facecolor='lightgray',edgecolor='none',alpha=.65))
for ly,r in pg:
 if r[0]<57 and r[2]>35 and r[1]<211 and r[3]>195:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc={'M4':'#756bb1','M5':'#d9a52b'}[ly],alpha=.15,lw=0))
for i in new:
 c=d.cells[i]
 if c[2]<57 and c[4]>35 and c[3]<211 and c[5]>195:ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc='crimson',ec='none',alpha=.7))
seq=list(reversed(chain))
for j,i in enumerate(seq):
 c=d.cells[i];x,y=G.ctr(c);ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc='crimson' if i in new else '#31a354',ec='black',lw=.5));label='NEW '+c[1].split('_')[0] if i in new else ('Launch q[24]' if j==0 else 'Capture x_bexp[1]' if j==len(seq)-1 else c[1].split('_')[0]);ax.annotate(label,(x,y),xytext=(5,10+8*(j%2)),textcoords='offset points',fontsize=8)
 if j:xx,yy=G.ctr(d.cells[seq[j-1]]);ax.plot([xx,x],[yy,y],c='red',lw=1)
ax.set(xlim=(35,57),ylim=(195,211),title='Actual original failing DATA cone after hold12\nClock/reset wires, FF poses/masters and source remain frozen')
for ax in axs:ax.set_aspect('equal');ax.set(xlabel='um',ylabel='um');ax.grid(alpha=.08)
fig.suptitle('VEs qualified native-PG GRT checkpoint: 1467 retained HB4 cells, 11 transient creation events\nActual geometry/PG LOOK only; repair-session FF+2.64ps is provisional; DRT/fill/finish/signoff held',fontsize=11);fig.tight_layout();fig.savefig(p/'actual_GRT_hold1467_LOOK.png',dpi=160)
