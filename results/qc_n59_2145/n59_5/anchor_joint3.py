"""PATH-QC-N59-5 joint zero-cycle anchor model v3 on the COMPLETE post-DPL FF cone graph of the kit's OWN netlist
(names come from that netlist, so no rename/alias mapping).  v2 (PATH-QC-N59-4) + two fixes:
 - macro-pin flops (OT_MPF list) stay at their placed OT_MPF sites (v2; anchA regression: F6 731 pins);
 - a minimax centre that lands on a macro is PROJECTED to the best free point (min of max L1 to the neighbours) on a
   2-um ring search, instead of being skipped (v2 left u_codec.tx_payload at stale sites: residue 575 arcs).
Face pin registers (u_bin_/u_bout_/u_ft*), ports and macro pins are fixed.  Model only: post-DPL census is the gate.
Reset (v3): every reset pin arc (load register <-> its reset driver register, geometry 'reset_cones') joins the graph and
the 405-um census, so the split rst_cp_* copies (ot_rst_copies) sit at the minimax centre of their own loads + tap relay.
Usage: anchor_joint3.py all_geometry.json ot_macro_pin_flops.txt OUT_PREFIX [old_reach405.tcl]"""
import json,re,sys
from collections import Counter,defaultdict
geo,mpf_file,out=sys.argv[1:4];old_tcl=sys.argv[4] if len(sys.argv)>4 else None
p=json.load(open(geo));pos={k:list(v) for k,v in p['positions'].items()};P0=p['positions'];T=p['targets'];M=p['macros']
norm=lambda n:n.replace('\\','')
MPF=set(norm(l.split()[0]) for l in open(mpf_file) if l.strip())
byn={norm(n):n for n in T}
oldn=set()
if old_tcl:
    for l in open(old_tcl):
        m=re.match(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}',l)
        if m and norm(m[1]) in byn:oldn.add(byn[norm(m[1])])
RA=[]
import os
for pin,c in (p.get('reset_cones',{}) if os.environ.get('N59_RESET','1')!='0' else {}).items():
    ld=pin.rsplit('/',1)[0]
    for e in c.get('ends',[]):
        if ld in pos and e in pos:RA.append((e,ld))
RST=set(e for e,_ in RA if re.search(r'rst_cp_',norm(e)))
fixed=lambda r:norm(r) in MPF or bool(re.search(r'u_bound\.u_(bin|bout|ft)',norm(r))) or r.startswith('PORT:') or (r not in T and r not in RST)
nb=defaultdict(set)
for s,t in T.items():
    for a in t['src']:nb[s].add(a);nb[a].add(s)
    for b in t['dst']:nb[s].add(b)
for e,ld in RA:nb[e].add(ld);nb[ld].add(e)
d=lambda a,b:abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
bad=lambda:[(a,s) for s,t in T.items() for a in t['src'] if a in pos and d(s,a)>405]+[(e,ld) for e,ld in RA if d(e,ld)>405]
inmac=lambda x,y:any(x0-2<x<x1+2 and y0-2<y<y1+2 for x0,y0,x1,y1 in M)
def best_free(x,y,ns):
    cost=lambda X,Y:max(abs(X-pos[q][0])+abs(Y-pos[q][1]) for q in ns)
    best=None
    for r in range(2,400,2):
        for k in range(16):
            import math
            X=min(max(x+r*math.cos(k*math.pi/8),5.0),772.0);Y=min(max(y+r*math.sin(k*math.pi/8),1.0),517.0)
            if inmac(X,Y):continue
            c=cost(X,Y)
            if best is None or c<best[0]:best=(c,X,Y)
        if best and r>=8 and best[0]<=cost(x,y)+r: break
    return best
B=bad();before=len(B);mov=set(r for r in oldn if not fixed(r))|set(r for e in B for r in e if not fixed(r))
orig={r:tuple(pos[r]) for r in mov}
hist=[];proj=0
for it in range(12):
    for r in sorted(mov):
        ns=[x for x in nb[r] if x in pos and x!=r]
        if not ns:continue
        u=[pos[x][0]+pos[x][1] for x in ns];v=[pos[x][0]-pos[x][1] for x in ns]
        uc=(max(u)+min(u))/2;vc=(max(v)+min(v))/2;x,y=(uc+vc)/2,(uc-vc)/2
        x=min(max(x,5.0),772.0);y=min(max(y,1.0),517.0)
        if inmac(x,y):
            b=best_free(x,y,ns)
            if b is None:continue
            x,y=b[1],b[2];proj+=1
        pos[r]=[x,y]
    B=bad();hist.append(len(B))
    newbad=set(r for e in B for r in e if not fixed(r))-mov
    if not newbad and it>3:break
    mov|=newbad;orig.update({r:tuple(P0[r]) for r in newbad})
# SPREAD (GEOM-REVIEW-11 condition (b)): replicas with identical neighbour sets share one minimax centre (rstB model:
# 525 formatter g_safe.di copies in one 10-um bin).  Move the excess of every bin over CAP to the nearest bin with room
# (2-um ring search, off macros) where every arc of the anchor stays <= 400 um; never back to the GPL site.
CAP=int(os.environ.get('N59_BIN_CAP','120'))
import math
occ=Counter((int(pos[r][0]//10),int(pos[r][1]//10)) for r in mov)
spread=0;unspread=0
for r in sorted(mov,key=lambda r:(int(pos[r][0]//10),int(pos[r][1]//10),r)):
    bk=(int(pos[r][0]//10),int(pos[r][1]//10))
    if occ[bk]<=CAP:continue
    ns=[x for x in nb[r] if x in pos and x!=r];x0,y0=pos[r];done=False
    for rad in range(4,200,2):
        for k in range(max(8,rad)):
            X=min(max(x0+rad*math.cos(2*math.pi*k/max(8,rad)),5.0),772.0);Y=min(max(y0+rad*math.sin(2*math.pi*k/max(8,rad)),1.0),517.0)
            nbk=(int(X//10),int(Y//10))
            if occ[nbk]>=CAP or inmac(X,Y):continue
            if ns and max(abs(X-pos[q][0])+abs(Y-pos[q][1]) for q in ns)>400:continue
            occ[bk]-=1;occ[nbk]+=1;pos[r]=[X,Y];spread+=1;done=True;break
        if done:break
    if not done:unspread+=1
B=bad()
fam=lambda n:re.sub(r'\$_.*','',re.sub(r'\[\d+\]','[]',norm(n)))
bins=Counter((int(pos[r][0]//10),int(pos[r][1]//10)) for r in mov)
rem=Counter((fam(a),fam(s)) for a,s in B)
summ=dict(scope='MODEL ONLY (neighbours at the kit netlist post-DPL sites); post-DPL full census is the gate',geometry=geo,
 before_over405=before,after_over405=len(B),iters=hist,anchors=len(mov),projected_off_macro=proj,from_old=len(oldn),
 max_anchors_per_10um_bin=max(bins.values()) if bins else 0,bins_over_150=sum(v>150 for v in bins.values()),
 max_move_um=round(max([abs(pos[r][0]-orig[r][0])+abs(pos[r][1]-orig[r][1]) for r in mov] or [0]),1),
 remaining=[dict(n=n,src=k[0],snk=k[1]) for k,n in rem.most_common()],families=Counter(fam(r) for r in mov).most_common())
summ['spread_moved']=spread;summ['spread_failed']=unspread;summ['bin_cap']=CAP;summ['reset_arcs']=len(RA);summ['reset_copy_drivers']=len(RST);summ['reset_over405_after']=sum(1 for e,ld in RA if d(e,ld)>405)
json.dump(summ,open(out+'.summary.json','w'),indent=1)
with open(out+'.tcl','w') as f:
    for r in sorted(mov):f.write(' {{%s} %.6f %.6f}\n'%(r,pos[r][0],pos[r][1]))
print(json.dumps({k:v for k,v in summ.items() if k!='families'},indent=0)[:3000])
