import json,math,sys
d=json.load(open('/tmp/qc52.json'))
pins=json.load(open('/tmp/redpins.json'))['pins']
R=405.0
def bus(T,n): return [b for b in d['partition_types'][T]['buses'] if b['name']==n][0]
def pos(T,name,i):
    b=bus(T,name); lo,hi=b['window_um']; W,H=d['partition_types'][T]['outline_um']
    s=lo+(i+0.5)*(hi-lo)/b['width']
    return {'E':(W,s),'W':(0,s),'N':(s,H),'S':(s,0)}[b['face']]
# RED input bits -> lane bus bits (from bound sle_su_c wiring; same index pattern on all su_c types)
l0=[(26,'l_last0')]+[(i,'l_out') for r in [(27,58),(273,304),(492,523),(711,742)] for i in range(r[0],r[1]+1)]+[(i,'l_ov') for i in (59,305,524,743)]+[(i,'l_raddr0') for i in range(60,84)]+[(84,'l_red0'),(85,'l_red0'),(86,'l_redsq0')]
l1=[(i,'l_out') for r in [(28,59),(247,278),(466,497),(685,716)] for i in range(r[0],r[1]+1)]+[(i,'l_ov') for i in (60,279,498,717)]
def st(T,lane,i):
    if lane=='l0': return pos(T,'x_su_l0_i',i) if i<452 else pos(T,'x_su_l0_p1_i',i-452)
    return pos(T,'x_su_l1_i',i) if i<438 else pos(T,'x_su_l1_p1_i',i-438)
def face_pin(face, port):
    c=[p for p in pins if p['face']==face and p['bus']==port]
    return c
def evaluate(T,ox,oy):
    W,H=d['partition_types'][T]['outline_um']
    ein=max(abs(st(T,'l0',i)[0]-(ox+276.438))+abs(st(T,'l0',i)[1]-(oy+150)) for i,_ in l0)
    win=max(abs(st(T,'l1',i)[0]-ox)+abs(st(T,'l1',i)[1]-(oy+140)) for i,_ in l1)
    sx,sy=ox+140,oy
    ctl=[pos(T,'x_ctl_o',i) for i in range(57)]; sc=[pos(T,'x_sc_o',i) for i in range(57)]
    octl=max(abs(a-sx)+abs(b-sy) for a,b in ctl); osc=max(abs(a-sx)+abs(b-sy) for a,b in sc)
    su8=[h for h in d['partition_types'][T]['hard_cores'] if h['inst']=='u_suvm_u_su8'][0]
    s8=(su8['origin_um'][0]+0.042, su8['origin_um'][1]+55.45)
    dsu8=abs(s8[0]-(ox+146))+abs(s8[1]-oy)
    shim=max(abs(st(T,'l0',i)[0]-s8[0])+abs(st(T,'l0',i)[1]-s8[1]) for i in (59,84,85))
    return dict(ein=round(ein,1),win=round(win,1),octl=round(octl,1),osc=round(osc,1),su8=round(dsu8,1),shim=round(shim,1))
def legal(T,ox,oy,m=8.64,edge=25.92):
    W,H=d['partition_types'][T]['outline_um']
    if ox<edge or oy<edge or ox+276.48>W-edge or oy+276.48>H-edge: return False
    for h in d['partition_types'][T]['hard_cores']:
        x0,y0=h['origin_um'];w,hh=h['outline_um']
        if ox<x0+w+m and ox+276.48+m>x0 and oy<y0+hh+m and oy+276.48+m>y0: return False
    return True
if __name__=='__main__':
    T=sys.argv[1] if len(sys.argv)>1 else 'sle_su_c'
    best=[]
    for ix in range(0,150):
        for iy in range(0,160):
            ox,oy=ix*8.64,iy*8.64
            if not legal(T,ox,oy): continue
            e=evaluate(T,ox,oy)
            kin=max(math.ceil(e['ein']/R),math.ceil(e['win']/R))-1
            kout=max(math.ceil(e['octl']/R),math.ceil(e['osc']/R))-1
            best.append((kin+kout,kin,kout,e['su8']>R,max(e['ein'],e['win'])+max(e['octl'],e['osc']),ox,oy,e))
    best.sort(key=lambda x:(x[3],x[0],x[4]))
    for b in best[:8]: print(b)

def chain_out(T,ox,oy,n):
    """shared output chain RED S pin -> n stages -> fan out to x_ctl_o and x_sc_o stations; best branch point M on a grid"""
    sx,sy=ox+140,oy
    ctl=[pos(T,'x_ctl_o',i) for i in range(57)]; sc=[pos(T,'x_sc_o',i) for i in range(57)]
    W,H=d['partition_types'][T]['outline_um']
    best=None
    for mx in range(0,int(W),20):
        for my in range(0,int(H),20):
            fin=max(max(abs(a-mx)+abs(b-my) for a,b in ctl),max(abs(a-mx)+abs(b-my) for a,b in sc))
            lead=(abs(mx-sx)+abs(my-sy))/n if n else (0 if (mx,my)==(sx,sy) else 1e9)
            h=max(fin,lead)
            if best is None or h<best[0]: best=(round(h,1),mx,my,round(fin,1),round(lead,1))
    return best
def run(T,kin,kout):
    res=[]
    for ix in range(0,150,2):
        for iy in range(0,160,2):
            ox,oy=ix*8.64,iy*8.64
            if not legal(T,ox,oy): continue
            e=evaluate(T,ox,oy)
            hin=max(e['ein'],e['win'])/(kin+1)
            res.append((round(hin,1),e['su8'],ox,oy))
    res.sort()
    out=[]
    for hin,su8,ox,oy in res[:40]:
        c=chain_out(T,ox,oy,kout)
        out.append((max(hin,c[0]),hin,c,su8,ox,oy))
    out.sort()
    return out[:3]
