"""PATH-QC-N59-4: joint zero-cycle anchor model from the COMPLETE post-DPL FF cone graph (current3 3_place).
Every register on a >405 um arc (plus Codex's 2227 reach405 anchors) moves to the L1 minimax centre of its fanin+fanout
registers / macro pins / ports; face pin registers (u_bin_/u_bout_/u_ft*), ports and macro pins are fixed.
Output: anchors TSV + Tcl entries in n59_reach405.tcl format + summary JSON.  Model only: post-DPL census is the gate."""
import json,re,sys
from collections import Counter,defaultdict
geo,old_tcl,out=sys.argv[1],sys.argv[2],sys.argv[3]
p=json.load(open(geo));pos={k:list(v) for k,v in p['positions'].items()};T=p['targets'];M=p['macros']
norm=lambda n:n.replace('\\','')
old={}
for l in open(old_tcl):
    m=re.match(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}',l)
    if m:old[m[1]]=(float(m[2]),float(m[3]))
byn={norm(n):n for n in T}
oldn=set(byn[norm(k)] for k in old if norm(k) in byn)
fixed=lambda r:bool(re.search(r'u_bound\.u_(bin|bout|ft)',norm(r))) or r.startswith('PORT:') or r not in T
nb=defaultdict(set)
for s,t in T.items():
    for a in t['src']:nb[s].add(a);nb[a].add(s)
    for b in t['dst']:nb[s].add(b)
d=lambda a,b:abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
bad=lambda:[(a,s) for s,t in T.items() for a in t['src'] if a in pos and d(s,a)>405]
inmac=lambda x,y:any(x0-2<x<x1+2 and y0-2<y<y1+2 for x0,y0,x1,y1 in M)
B=bad();before=len(B);mov=set(oldn)|set(r for e in B for r in e if not fixed(r))
orig={r:tuple(pos[r]) for r in mov}
hist=[]
for it in range(10):
    for r in sorted(mov):
        ns=[x for x in nb[r] if x in pos and x!=r]
        if not ns:continue
        u=[pos[x][0]+pos[x][1] for x in ns];v=[pos[x][0]-pos[x][1] for x in ns]
        uc=(max(u)+min(u))/2;vc=(max(v)+min(v))/2;x,y=(uc+vc)/2,(uc-vc)/2
        x=min(max(x,5.0),772.0);y=min(max(y,1.0),517.0)
        if inmac(x,y):continue
        pos[r]=[x,y]
    B=bad();hist.append(len(B))
    newbad=set(r for e in B for r in e if not fixed(r))-mov
    if not newbad and it>2:break
    mov|=newbad;orig.update({r:tuple(p['positions'][r]) for r in newbad})
fam=lambda n:re.sub(r'\$_.*','',re.sub(r'\[\d+\]','[]',norm(n)))
bins=Counter((int(pos[r][0]//10),int(pos[r][1]//10)) for r in mov)
rem=Counter((fam(a),fam(s)) for a,s in B)
summ=dict(scope='MODEL ONLY (neighbours at current3 post-DPL sites); post-DPL full census is the gate',source='codex/n59-2145@2df5f26ff current3 3_place',
 before_over405=before,after_over405=len(B),iters=hist,anchors=len(mov),from_codex_reach405=len(oldn),new=len(mov-oldn),
 max_anchors_per_10um_bin=max(bins.values()),bins_over_150=sum(v>150 for v in bins.values()),
 max_move_um=round(max(abs(pos[r][0]-orig[r][0])+abs(pos[r][1]-orig[r][1]) for r in mov),1),
 remaining=[dict(n=n,src=k[0],snk=k[1]) for k,n in rem.most_common()],families=Counter(fam(r) for r in mov).most_common())
json.dump(summ,open(out+'.summary.json','w'),indent=1)
with open(out+'.tcl','w') as f:
    for r in sorted(mov):f.write(' {{%s} %.6f %.6f}\n'%(r,pos[r][0],pos[r][1]))
print(json.dumps({k:v for k,v in summ.items() if k!='families'},indent=0)[:2500])
