from pathlib import Path
from collections import Counter
import sys,json,numpy as np
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');byname={c[6]:k for k,c in D.cells.items()}
for cid,c in list(D.cells.items()):
 cc=list(c)
 if 'u_cland_i_seq__g_fan_N__u_fan_kc/' in c[6]:cc[3]-=146.88;cc[5]-=146.88
 elif 'u_cland_i_fch_pc_Q_N_q/' in c[6] or 'u_cland_i_kvpc_Q_N_pc__fo/' in c[6]:cc[2]+=172.8;cc[4]+=172.8
 D.cells[cid]=tuple(cc)
for z in json.load(open(P/'current_graph_lp_margin391.json'))[0]['targets']:
 cid=byname[z['name']];c=list(D.cells[cid]);x,y=g.ctr(c);dx,dy=z['new'][0]-x,z['new'][1]-y;c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[cid]=tuple(c)
taps=[p for p in D.pins if g.GRID_TAP_RE.match(p['name'])and p['io']=='INPUT'];names=[t['name']for t in taps];base=np.array([[t['x'],t['y']]for t in taps]);xy=[];sn=[]
for c in D.cells.values():
 if c[0]!='S':continue
 cid=byname[c[6]];ns=[n for n,ck in D.cell_in.get(cid,[])if ck]
 if not ns:continue
 dr=D.nets[ns[0]][1]
 if dr and dr[0]=='p'and g.GRID_TAP_RE.match(D.pin_by_k[dr[1]]['name']):xy.append(g.ctr(c));sn.append(c[6])
xy=np.array(xy);index={n:i for i,n in enumerate(names)};out=[]
for dx20 in [0,-8.64,-17.28,-25.92,-34.56,-43.2,-51.84]:
 for dy20 in [34.56,43.2,51.84,60.48,69.12]:
  b=base.copy();b[index['clk_t19'],1]-=51.84;b[index['clk_t20']]+=np.array([dx20,dy20]);b[index['clk_t10'],0]+=8.64;b[index['clk_t36'],0]+=8.64
  a=np.abs(xy[:,None,:]-b[None,:,:]).sum(axis=2);near=a.argmin(axis=1);dist=a[np.arange(len(xy)),near];load=np.bincount(near,minlength=len(taps));bad=np.flatnonzero(dist>220)
  out.append(dict(offsets={'clk_t19':[0,-51.84],'clk_t20':[dx20,dy20],'clk_t10':[8.64,0],'clk_t36':[8.64,0]},max_um=float(dist.max()),over220=len(bad),maxload=int(load.max()),empty=int((load==0).sum()),loads=dict(zip(names,map(int,load))),worst=[dict(name=sn[k],xy=xy[k].tolist(),tap=names[near[k]],distance_um=float(dist[k]))for k in bad],contacts=[dict(name=n,old=base[index[n]].tolist(),new=b[index[n]].tolist())for n in ['clk_t19','clk_t20','clk_t10','clk_t36']]))
out.sort(key=lambda r:(r['over220']+max(0,r['maxload']-1500)+r['empty']*100,r['max_um'],sum(abs(v)for o in r['offsets'].values()for v in o)))
res=dict(scope='STATIC nearest plannedgrid contact sensitivity on current391FF endpoint witness; no native builtclock/PG/parent/source adoption',grid_sinks=len(xy),candidate_count=len(out),best=out[0],feasible_count=sum(not r['over220']and r['maxload']<=1500and not r['empty']for r in out),top5=out[:5]);(P/'clock_contact_search.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['best','top5']});print({k:v for k,v in out[0].items()if k not in['loads','worst','contacts']})
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=res['best'];fig,ax=plt.subplots(figsize=(15,7));ax.scatter(xy[:,0],xy[:,1],s=.25,color='steelblue',alpha=.5)
ax.scatter(base[:,0],base[:,1],marker='*',s=90,facecolor='none',edgecolor='grey',label='Original same-name planned contacts')
for z in r['contacts']:
 x,y=z['new'];ox,oy=z['old'];ax.plot([ox,x],[oy,y],color='darkorange');ax.scatter([x],[y],marker='*',s=150,color='darkorange');ax.text(x+6,y+6,z['name'],fontsize=8)
ax.set(xlim=(0,1900.8),ylim=(0,838.08),aspect='equal',xlabel='um',ylabel='um',title='Hroot STATIC 391um endpoint witness + four same-name grid contact moves\n13185 grid sinks: nearest max216.055um / load1496 / 39 nonempty; 0 actualclockcells, special roots remain separate')
ax.legend(loc='upper left');fig.tight_layout();fig.savefig(P/'clock_contact_search.png',dpi=145)
