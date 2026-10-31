"""GRT-0183 lint (HUBMESH-3, diagnostic): flag clock pins whose GRT gcell (570 nm) has a LOW h-layer row (an M8 PG stripe or strap band in the row; the exact residual is 0-1 track after the min-1 adjustment rule, not modelled) AND a zero-capacity M9 column -- the boxed-in candidates.
tile 570 nm, tracks M8/M9 0.116+0.08k, layer adj 0.4 floor (min 1), obstruction = DEF BLOCKAGES + supply SWires (no spacing),
reduce = ceil(covered/80) per tile edge, interior tiles 0.  Flags pins whose gcell(s) are boxed."""
import sys,re,math,collections
T=570; P=80; OFF=116; ADJ=0.4
def tracks(lo,hi):  # tracks with coord in [lo,hi)
    return max(0, math.ceil((hi-OFF)/P) - math.ceil((lo-OFF)/P))
d=open(sys.argv[1]).read().split('\n')
die=[int(v) for v in re.findall(r'\d+',[l for l in d if l.startswith('DIEAREA')][0])]
W,H=die[2],die[3]; nx,ny=W//T,H//T
obs={'M8':[], 'M9':[]}   # (lo,hi) across-track intervals; full-length stripes assumed
sec=None
for l in d:
    if l.startswith('BLOCKAGES'):sec='B'
    elif l.startswith('SPECIALNETS'):sec='S'
    elif l.startswith('NETS') or l.startswith('END BLOCKAGES') or l.startswith('END SPECIALNETS'):sec=None if not l.startswith('END') else None
    if sec=='B':
        m=re.search(r'LAYER (M8|M9) RECT \( (\d+) (\d+) \) \( (\d+) (\d+) \)',l)
        if m:
            L=m.group(1);x0,y0,x1,y1=map(int,m.groups()[1:])
            obs[L].append((y0,y1) if L=='M8' else (x0,x1))
    if sec=='S' and (l.startswith('- VDD') or l.startswith('- VSS') or l.lstrip().startswith('NEW')):
        if 'VIA' in l: continue
        m=re.search(r'(M8|M9) (\d+) \+ SHAPE STRIPE \( (\d+) (\d+) \) \( (\d+) (\d+) \)',l)
        if m and (cur in ('VDD','VSS')):
            L=m.group(1);w=int(m.group(2));x0,y0,x1,y1=map(int,m.groups()[2:])
            if L=='M8': obs[L].append((y0-w//2,y0+w//2))
            else: obs[L].append((x0-w//2,x0+w//2))
    if sec=='S' and l.startswith('- '): cur=l.split()[1]
    if sec!='S': cur=None
def capvec(L,n):
    red=collections.defaultdict(int); full=set()
    cov=collections.defaultdict(list)
    for lo,hi in obs[L]:
        a,b=lo//T,(hi-1)//T
        for t in range(a,b+1):
            if a<t<b: full.add(t)
            else: cov[t].append((max(lo,t*T),min(hi,(t+1)*T)))
    cap=[]
    for t in range(n):
        c=tracks(t*T,(t+1)*T); c=max(math.floor(c*(1-ADJ)),1) if c>0 else 0
        if t in full: c=0
        elif t in cov:
            iv=sorted(cov[t]);tot=0;s,e=iv[0]
            for lo,hi in iv[1:]:
                if lo>e: tot+=e-s; s,e=lo,hi
                else: e=max(e,hi)
            tot+=e-s
            c=max(c-math.ceil(tot/P),0)
        cap.append(c)
    return cap
rowcap=capvec('M8',ny); colcap=capvec('M9',nx)
print('rows M8 cap0 %d/%d  cols M9 cap0 %d/%d'%(sum(c==0 for c in rowcap),ny,sum(c==0 for c in colcap),nx))
# cells + pins
PIN={'BUFx24_ASAP7_75t_R':{'A':[(18,27,36,243),(18,126,78,144)],'Y':[(310,27,1602,45),(1584,27,1602,243),(310,225,1602,243)]},
     'BUFx4f_ASAP7_75t_R':None}
cells={}
for l in d:
    m=re.match(r'- (\S+) (\S+) \+ (?:FIXED|PLACED) \( (\d+) (\d+) \) (\S+)',l)
    if m: cells[m.group(1)]=(m.group(2),int(m.group(3)),int(m.group(4)),m.group(5))
def pin_tiles(c,p):
    mst,x,y,o=cells[c]
    if mst!='BUFx24_ASAP7_75t_R': 
        sh=[(0,0,432,270)]
    else: sh=PIN[mst][p]
    ts=set()
    for a,b,cc,dd in sh:
        if o=='FS': b,dd=270-dd,270-b
        for tx in range((x+a)//T,(x+cc-1)//T+1):
            for ty in range((y+b)//T,(y+dd-1)//T+1): ts.add((tx,ty))
    return ts
def boxed(t): return rowcap[t[1]]==0 and colcap[t[0]]==0
nets={}
on=False
for l in d:
    if l.startswith('NETS'):on=True;continue
    if on and l.startswith('- '):
        nm=l.split()[1]; nets[nm]=re.findall(r'\( (\S+) (\S+) \)',l)
allb=[];anyb=[]
for nm,pins in nets.items():
    for c,p in pins:
        if c not in cells: continue
        ts=pin_tiles(c,p); bx=[t for t in ts if boxed(t)]
        if bx and len(bx)==len(ts): allb.append((nm,c,p,sorted(ts)))
        elif bx: anyb.append((nm,c,p,len(bx),len(ts)))
print('pins ALL gcells boxed:',len(allb))
for r in allb: print('  ALL',r[0],r[1],r[2],cells[r[1]][1:],r[3][:3])
print('pins SOME gcells boxed:',len(anyb))
for nm in sys.argv[2:]:
    print('query',nm,[(c,p,cells.get(c,('?',))[1:],[(t,rowcap[t[1]],colcap[t[0]]) for t in sorted(pin_tiles(c,p))]) for c,p in nets.get(nm,[]) if c in cells])
