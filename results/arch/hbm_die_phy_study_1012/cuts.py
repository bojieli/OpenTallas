"""Cut demand vs track capacity on the R25GQ die network (r25gqn_pr8). bits crossing each cut line, grouped by family."""
import sys,collections,json,re
import pathlib; R=pathlib.Path(__file__).resolve().parents[3]; sys.path.insert(0,str(R/'tools'))
import hbm_accel_die_fp as F
m=F.build(F.variant_arg('r25gqn_pr8'))
I={it.name:it for it in m['insts']}
W,H=m['geo']['die_w'] if 'die_w' in m['geo'] else None, None
xs=[it.x+it.w for it in m['insts']]; ys=[it.y+it.h for it in m['insts']]
DW,DH=32984.288,25980.528
def c(n):
    it=I[n]; return (it.x+it.w/2, it.y+it.h/2)
def fam(name):
    n=re.sub(r'_\d+(_\d+)?$','',name)
    if n.startswith('hgi_lg'): return n[:9]  # hgi_lge_ / hgi_lgw_
    return re.sub(r'(_?(SW|SE|NW|NE|[NSEW]\d?|s\d|\d+))+$','',n)[:22]
blocks=[it for it in m['insts'] if it.w*it.h>4e4]   # hard blocks (>0.04 mm2), relays/stations excluded
def covered(axis,cpos,lo,hi):
    iv=[]
    for it in blocks:
        if axis=='x' and it.x<cpos<it.x+it.w: iv.append((max(lo,it.y),min(hi,it.y+it.h)))
        if axis=='y' and it.y<cpos<it.y+it.h: iv.append((max(lo,it.x),min(hi,it.x+it.w)))
    iv=sorted(v for v in iv if v[1]>v[0]); t=0; cur=None
    for a,b in iv:
        if cur is None or a>cur[1]:
            if cur: t+=cur[1]-cur[0]
            cur=[a,b]
        else: cur[1]=max(cur[1],b)
    if cur: t+=cur[1]-cur[0]
    return t
# ASAP7 pitches (nm) -> tracks/um ; horizontal: M2 M4 M6 M8, vertical: M3 M5 M7 M9
TPU={'M4':1/0.048,'M5':1/0.048,'M6':1/0.064,'M7':1/0.064,'M8':1/0.080,'M9':1/0.080}
def cap(axis,L,Lch):
    # crossing a vertical line (axis x) uses horizontal layers; over blocks only die layers M8 (M9 for y cuts)
    lo,hi=(('M6','M8') if axis=='x' else ('M7','M9'))
    raw=L*(TPU[lo]+TPU[hi])                       # M6-M9 raw tracks along the whole cut
    use=0.75*L*TPU[hi]+0.75*Lch*TPU[lo]+0.5*Lch*TPU['M4' if axis=='x' else 'M5']   # die-usable: PDN 25 %, M4/5 0.5 in channels (D21)
    return raw,use
cuts={'X_centre_full':('x',DW/2,0,DH),'Y_centre_full':('y',DH/2,0,DW)}
for xc in (12000,13000,14000,14400,15000,15500,16000,16500,17000,18000): cuts[f'x{xc/1000:g}_hub']=('x',xc,10000,16000)
for yc in (10000,11000,12000,12500,13000,14000,14600,15000,16000): cuts[f'y{yc/1000:g}_hub']=('y',yc,12000,18000)
res={}
for cn,(ax,cp,lo,hi) in cuts.items():
    tot=0; byf=collections.Counter()
    for bid,cls,bits,ends in m['buses']:
        pts=[c(e[0]) for e in ends if e[0] in I]
        if len(pts)<2: continue
        segs=list(zip(pts,pts[1:])) if len(pts)<=2 or cls in ('hub',) and 'lg' in bid else [(pts[0],p) for p in pts[1:]]
        for (x1,y1),(x2,y2) in segs:
            if ax=='x':
                if min(x1,x2)<cp<max(x1,x2) and max(min(y1,y2),lo)<=min(max(y1,y2),hi)+1e-9:
                    tot+=bits; byf[fam(bid)]+=bits
            else:
                if min(y1,y2)<cp<max(y1,y2) and max(min(x1,x2),lo)<=min(max(x1,x2),hi)+1e-9:
                    tot+=bits; byf[fam(bid)]+=bits
    L=hi-lo; Lb=covered(ax,cp,lo,hi); raw,use=cap(ax,L,L-Lb)
    res[cn]=dict(axis=ax,pos_um=cp,span_um=[lo,hi],bits=tot,block_cover_um=round(Lb),raw_M6_M9_tracks=round(raw),usable_tracks=round(use),util_usable=round(tot/use,3),top=byf.most_common(12),fam=dict(byf))
    print(cn,tot,round(Lb),round(raw),round(use),round(tot/use,3),byf.most_common(6))
lg={}
for bid,cls,bits,ends in m['buses']:
    if bid.startswith('hgi_lg'):
        k=re.sub(r'_\d+(_\d+)?$','',bid); lg.setdefault(k,[0,0]); lg[k][0]=bits; lg[k][1]+=1
res['lane_group_buses']=lg
json.dump(res,open(pathlib.Path(__file__).with_name('cuts_today.json'),'w'),indent=1)
print(json.dumps(lg)[:1500])
