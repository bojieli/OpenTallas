from pathlib import Path
import sys,json,re,collections
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
p=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-pslice-placed-look-0910/out/geom.tsv');norm=lambda s:s.replace(chr(92),'')
target='u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[1][35]$_DFF_P_'
i=next(i for i,c in D.cells.items()if norm(c[6])==target);c=D.cells[i];x,y=g.ctr(c);q=collections.deque(D.drives.get(i,[]));seen=set();comb=set();caps=set()
while q:
 n=q.popleft()
 if n in seen:continue
 seen.add(n)
 for s in D.nets[n][2]:
  if s[0]!='i'or s[2]:continue
  k=s[1];cell=D.cells[k]
  if cell[0]in'SM':caps.add(k)
  elif k not in comb:comb.add(k);q.extend(D.drives.get(k,[]))
ms=[]
for k in caps:
 z=D.cells[k]
 if z[0]!='M':continue
 a,b,cc,d=z[2:6];near=max(a-x,0,x-cc)+max(b-y,0,y-d);far=max(abs(x-a),abs(x-cc))+max(abs(y-b),abs(y-d));ms.append(dict(name=z[6],box=list(z[2:6]),nearest_body_lower_bound_um=near,farthest_body_corner_um=far))
ms.sort(key=lambda z:-z['nearest_body_lower_bound_um']);corners=[(a,b)for z in ms for a in(z['box'][0],z['box'][2])for b in(z['box'][1],z['box'][3])];us=[a+b for a,b in corners];vs=[a-b for a,b in corners]
out=dict(scope='Bounded existing geom.tsv worst DATA launch fanout diagnosis; no EDA/readDB/route/layout variant',launch=dict(name=c[6],master=c[1],centre=[x,y]),first_sequential_FFs=sum(D.cells[k][0]=='S'for k in caps),first_sequential_macros=len(ms),comb_visited=len(comb),macro_endpoints=ms,conservative_common_launch_radius_body_envelope_um=max(max(us)-min(us),max(vs)-min(vs))/2,macro_groups=dict(collections.Counter(re.search(r'g_c\[(\d+)\]',norm(z[6])).group(1)for z in D.cells.values()if z[0]=='M')),interpretation='Current worst reach is conservative macroBODY corner metric, not actual inputpin metal. Nearestbody >405 proves failure even without exact transformed data pin; fullbody common radius is a conservative source-layout bound only.')
(p/'worst_write_fanout.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in['macro_endpoints']},indent=1));print('worst_nearest',ms[:2])
