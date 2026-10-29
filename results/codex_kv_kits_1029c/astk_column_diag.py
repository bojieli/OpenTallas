import sys,json
from pathlib import Path
from collections import Counter
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(__file__).parent/'astk_actual';D=G.Design(p/'geom.tsv');rec=[]
def name(r):
 if r[0]=='p':return D.pin_by_k[r[1]]['name']
 return D.cells[r[1]][6]
for sig,dr,ss in D.nets:
 if sig=='CLOCK':continue
 refs=([dr] if dr else [])+ss;xy=[]
 for r in refs:
  if r[0]=='p':q=D.pin_by_k[r[1]];xy.append((q['x'],q['y']))
  else:xy.append(G.ctr(D.cells[r[1]]))
 if len(xy)<2:continue
 x,xx=min(q[0] for q in xy),max(q[0] for q in xy);y,yy=min(q[1] for q in xy),max(q[1] for q in xy)
 if y<47.5<yy and xx>180:
  overlap=max(0,min(xx,190.08)-max(x,180));w=overlap/max(1,xx-x)
  rec.append(dict(w=w,driver=name(dr) if dr else None,sinks=[name(r) for r in ss],bbox=[x,y,xx,yy]))
c=Counter()
for q in rec:
 n=q['driver'] or ''
 for key in ('g_zn_0','g_zn_1','g_zn_2','g_zn_3','u_ctl'):
  if key in n:c[key]+=q['w'];break
 else:c['anonymous']+=q['w']
print('ASTK_COLUMN',len(rec),'nets','weighted',sum(q['w'] for q in rec),'driver_groups',c)
print('TOP',json.dumps(sorted(rec,key=lambda q:-q['w'])[:6])[:3000]);(p/'column_contributors.json').write_text(json.dumps({'cut':[180,190.08,47.5],'driver_groups':dict(c),'nets':sorted(rec,key=lambda q:-q['w'])},indent=1)+'\n')
