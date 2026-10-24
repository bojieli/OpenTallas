import json,re,random,math,sys
sys.path.insert(0,'.')
PD="physical/die_plan/s81/inputs/core_pins/%s.json"
MOD = dict(vp="ot_s81sl_vp", vn="ot_s81sl_vn", vs="ot_s81sl_vs", vsw="ot_s81sl_vsw", vq="ot_s81sl_vq",
           rxsf="dsfd_su_t_rxsf", rxsb="dsfd_su_t_rxsb", ve="ot_s81sl_ve")
SZ = dict(vp=(734.4, 864), vn=(356.4, 356.4), vs=(172.8, 172.8), vsw=(224.64, 224.64), vq=(172.8, 129.6),
          rxsf=(140.4, 140.4), rxsb=(140.4, 140.4), ve=(345.6, 345.6))
B = [("vp", "hw_ hq_ hr_ n_ wl_", "vn", "hw_ hq_ hr_ n_ wl_"), ("vp", "s_", "vs", "s_"), ("vp", "x_q x_r", "vs", "x_q x_r"),
     ("vp", "x_w", "vs", "x_w"), ("vp", "m_", "vq", "m_"), ("vn", "y", "vq", "y"), ("vs", "u um_", "vq", "u um_"),
     ("ve", "r_ p_", "vs", "ve_r ve_p"), ("ve", "a_", "vs", "ve_a"), ("ve", "o_", "vs", "ve_o"),
     ("vs", "sw_v sw_d sw_w sw_lim", "vsw", "i_"), ("vsw", "o_", "vs", "sw_vi sw_ri sw_fi"),
     ("vs", "ra_v ra_x", "rxsf", "i_"), ("rxsf", "o_", "rxsb", "i_"), ("rxsb", "o_", "vs", "ra_vi ra_ri ra_fi")]
C={}
for c in MOD:
    ps=json.load(open(PD%MOD[c]))["pins"]
    for a,pa,b,pb in B:
        for cc,g in ((a,pa),(b,pb)):
            if cc==c and (c,g) not in C:
                sel=[p for p in ps if any(re.sub(r"\[.*","",p["name"]).startswith(q) for q in g.split())]
                C[(c,g)]=(len(sel),sum(p['x'] for p in sel)/len(sel),sum(p['y'] for p in sel)/len(sel))
W=float(sys.argv[1]);H=1226.88;G=8.64;E=34.56;GAP=13.8;DX=0.108;DY=0.012
def RL(O,r):
    out=[]
    for (a,pa,b,pb),(_,_,_,n,d) in zip(B,r):
        if d<=450: out.append(d); continue
        _,ax,ay=C[(a,pa)];_,bx_,by=C[(b,pb)]
        out.append(routed(O,a,b,(O[a][0]+ax,O[a][1]+ay),(O[b][0]+bx_,O[b][1]+by)))
    return out
def ev(O):
    rows=[]
    for a,pa,b,pb in B:
        n,ax,ay=C[(a,pa)];_,bx,by=C[(b,pb)]
        d=abs(O[a][0]+ax-O[b][0]-bx)+abs(O[a][1]+ay-O[b][1]-by); rows.append((a,b,pa,n,d))
    return rows
def legal(O):
    bx={c:(O[c][0]+DX,O[c][1]+DY,O[c][0]+DX+SZ[c][0],O[c][1]+DY+SZ[c][1]) for c in O}
    for c,b in bx.items():
        if b[0]<E-1e-6 or b[1]<E-1e-6 or b[2]>W-E+1e-6 or b[3]>H-E+1e-6: return False
    ks=list(bx)
    for i,a in enumerate(ks):
        for k in ks[i+1:]:
            A=bx[a];Bb=bx[k]
            if max(Bb[0]-A[2],A[0]-Bb[2],Bb[1]-A[3],A[1]-Bb[3])<GAP-1e-6: return False
    return True
HALO=8.64
def boxes(O):
    return {c:(O[c][0]+DX-HALO,O[c][1]+DY-HALO,O[c][0]+DX+SZ[c][0]+HALO,O[c][1]+DY+SZ[c][1]+HALO) for c in O}
def seglen(p,q,bx,skip):
    # axis-aligned segment p->q; detour around any crossed box (not endpoints' own cores)
    L=abs(p[0]-q[0])+abs(p[1]-q[1]); add=0
    for c,b in bx.items():
        if c in skip: continue
        if p[1]==q[1] and b[1]<p[1]<b[3] and min(p[0],q[0])<b[2] and max(p[0],q[0])>b[0]:
            add=max(add,2*min(p[1]-b[1],b[3]-p[1]))
        if p[0]==q[0] and b[0]<p[0]<b[2] and min(p[1],q[1])<b[3] and max(p[1],q[1])>b[1]:
            add=max(add,2*min(p[0]-b[0],b[2]-p[0]))
    return L+add
def routed(O,a,b,A,Bp):
    bx=boxes(O); sk={a,b}
    m1=(Bp[0],A[1]); m2=(A[0],Bp[1])
    return min(seglen(A,m1,bx,sk)+seglen(m1,Bp,bx,sk), seglen(A,m2,bx,sk)+seglen(m2,Bp,bx,sk))
def cost(O):
    r=ev(O)
    st=0
    for a,b,pa,n,d in r:
        if d>450:
            na,ax,ay=C[(a,pa)]
            pb=[x for x in B if x[0]==a and x[1]==pa][0][3] if False else None
            st+=n*(math.ceil(d/450)-1)
    st=sum(n*max(0,math.ceil(rl/450)-1) for (a,b,pa,n,d),rl in zip(r,RL(O,r))); return st*1e4+sum(n*d for *_,n,d in r)/1e3, r
if __name__=='__main__':
    O0=json.loads(sys.argv[2]) ; assert legal(O0),'start illegal'
    best=(cost(O0)[0],O0); random.seed(int(sys.argv[3]) if len(sys.argv)>3 else 1)
    fixed=set(sys.argv[4].split(',')) if len(sys.argv)>4 else set()
    T=50.0
    cur=best
    for it in range(150000):
        O=dict(cur[1]); c=random.choice([k for k in O if k not in fixed])
        st=random.choice([1,1,2,4,8,16,40])
        O[c]=(round(O[c][0]+random.randint(-1,1)*st*G,4),round(O[c][1]+random.randint(-1,1)*st*G,4))
        if not legal(O): continue
        cc=cost(O)[0]
        if cc<cur[0] or random.random()<math.exp((cur[0]-cc)/T):
            cur=(cc,O)
            if cc<best[0]: best=(cc,O)
        T=max(0.5,T*0.99997)
    c,r=cost(best[1]); print(json.dumps(best[1])); print(round(c,1))
    for x,rl in zip(r,RL(best[1],r)): print(x[0],x[1],x[2],x[3],round(x[4]),round(rl))
