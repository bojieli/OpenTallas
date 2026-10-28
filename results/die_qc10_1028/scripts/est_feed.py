"""DIE-QC-10 ESTIMATE: QC local form = column spines along the A0 arms + slice-chain trunk along the slice links.
Every region's clock tree hangs from a tap ON the spine at its face; a crossing shares the clock up to the spine node
between its two taps.  Emits synthetic CA rows (same schema as landed_phase_ocv/ca_spice rows, trial6 ports) for
count_align_plan.py.  Model constants calibrated on trial6 (cal.py, UNCHECKED-independent):
 region tree  : leaf arrival from its tap = A_c + k_r * far_manhattan(tap, region corner)   TT -104 + 0.498 / FF -89 + 0.417
 spine/trunk  : k_s ps/um (plan-built repeated M8/M9; DIE-QC-9 0.281 TT), FF x 0.837
 OCV width    : w = c0 + kw * unshared (TT 79.2 + 0.0687, FF 61.4 + 0.0677), p_up from dst side, p_dn from src side
usage: est_spine.py OUT.json [k_s_TT] [region_k_scale]"""
import json, sys, collections, math
sys.path.insert(0,'/srv/opentallas-scratch2/claude/die-qc10-1028/est')
from ocvmodel import ocv, spread
CAL=80.0; LEG=40.0; LEG_CAL=40.0  # validate.py: model hull width med 344 vs trial6 measured 420 -> +80 ps width
B='/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/'
X='/srv/opentallas-scratch2/claude/die-qc9-1028/ca/t6/grp_spice_xing_lpo.json'
out=sys.argv[1]; KS=float(sys.argv[2]) if len(sys.argv)>2 else 0.281; RS=float(sys.argv[3]) if len(sys.argv)>3 else 1.0; TAP=sys.argv[4] if len(sys.argv)>4 else 'centre'; CS=float(sys.argv[5]) if len(sys.argv)>5 else 150.0; TREE=sys.argv[6] if len(sys.argv)>6 else 'feed'
box={r['tag']:r['box_um'] for r in json.load(open(B+'regions_map.json'))['regions']}
src=json.load(open(X))['corners']
CORN={'TT_droop-regions_corelat250':dict(a=-104,k=0.498*RS,ks=KS,c0=79.2,kw=0.0687),
      'FF_droop-regions_corelat202.5':dict(a=-89,k=0.417*RS,ks=KS*0.837,c0=61.4,kw=0.0677)}
def col(r):
    p=r.split('_'); return p[1]
cols=sorted({col(r) for r in box if r.startswith(('c_','sl_'))})
xc={c:box[f'c_{c}_bn_00'][2] for c in cols}          # arm x0/x1 boundary = column spine x
YF=12463.2                                              # slice-chain row (sl_stm/sc), feed taps y
ROOT=(16390.1,YF)
nodes={}; par={}
def add(n,xy,p): nodes[n]=xy; par[n]=p
feed=json.load(open(B+'feed_grpP.json'))['parent']
FEEDP=dict(feed)
def arm(X,half):   # half 'b' (bn/bf) or 't' (tn/tf); returns rows from slice outward
    n,f=('bn','bf') if half=='b' else ('tn','tf')
    return [f'c_{X}_{n}_00',f'c_{X}_{n}_01',f'c_{X}_{f}_00',f'c_{X}_{f}_01'],[f'c_{X}_{n}_10',f'c_{X}_{n}_11',f'c_{X}_{f}_10',f'c_{X}_{f}_11']
if TREE in ('rt1','rt2') or TREE.startswith('rt2'):
    for X in cols:
        for half,e0,e1 in (('b',f'sl_{X}_su_l1',f'sl_{X}_su_l0'),('t',f'sl_{X}_st_a',f'sl_{X}_st_b')):
            c0,c1=arm(X,half)
            for i,r in enumerate(c0): FEEDP[r]=e0 if i==0 else c0[i-1]
            for i,r in enumerate(c1):
                FEEDP[r]=(e1 if i==0 else c1[i-1]) if TREE=='rt1' else c0[i]
if TREE=='rt2c': FEEDP['coll_s']='c_W5_bf_00'
def cen(r): b=box[r]; return ((b[0]+b[2])/2,(b[1]+b[3])/2)
def entry(p,c):   # centre of the shared face segment
    P,Cb=box[p],box[c]
    x0,x1=max(P[0],Cb[0]),min(P[2],Cb[2]); y0,y1=max(P[1],Cb[1]),min(P[3],Cb[3])
    return ((x0+x1)/2,(y0+y1)/2)
root=[r for r,p in FEEDP.items() if p is None][0]
add('c_'+root,cen(root),None)
kids=collections.defaultdict(list)
for r,p in FEEDP.items():
    if p: kids[p].append(r)
q=[root]
for p in q:
    for c in sorted(kids[p]):
        add('e_'+c,entry(p,c),'c_'+p); add('c_'+c,cen(c),'e_'+c); q.append(c)
tapn={r:'c_'+r for r in box}
print('regions',len(box),'tree',TREE,'coll_s<-',FEEDP['coll_s'],'coll_f0<-',FEEDP['coll_f0'])
def path(n):
    p=[n]
    while par[n]: n=par[n]; p.append(n)
    return p
def S(n,ks):
    t=0.0; p=path(n)
    for a,b in zip(p,p[1:]): t+=abs(nodes[a][0]-nodes[b][0])+abs(nodes[a][1]-nodes[b][1])
    return t*ks
def far(r,xy):
    b=box[r]; return max(abs(xy[0]-x)+abs(xy[1]-y) for x in (b[0],b[2]) for y in (b[1],b[3]))
def lca(a,b):
    s=set(path(a))
    for n in path(b):
        if n in s: return n
res={'corners':{}, 'model':__doc__, 'k_s_TT':KS, 'region_k_scale':RS}
for cn,m in CORN.items():
    C='TT' if cn.startswith('TT') else 'FF'
    A={r:S(tapn[r],m['ks'])+m['a']+m['k']*far(r,nodes[tapn[r]]) for r in tapn}
    rows=[]
    for r0 in src[cn]['all']:
        a,b=r0['src'],r0['dst']; l=lca(tapn[a],tapn[b]); sl=S(l,m['ks'])
        ua,ub=A[a]-sl,A[b]-sl
        ca=box[a]; cb=box[b]; dist=math.hypot((ca[0]+ca[2]-cb[0]-cb[2])/2,(ca[1]+ca[3]-cb[1]-cb[3])/2)
        s_=(spread(a,C,CS)+spread(b,C,CS))/2; os_,oh=ocv(ua,ub,dist,C)
        pdn=max(m['c0']/2+m['kw']*ua, s_+os_)+CAL/2; pup=max(m['c0']/2+m['kw']*ub, s_+oh)+CAL/2
        rows.append(dict(port=r0['port'],src=a,dst=b,lca=l,d_ps=A[b]-A[a],unshared_a_ps=ua,unshared_b_ps=ub,dist_um=dist,
                         p_up_ps=pup,p_dn_ps=pdn,margin_ps=0.0,
                         src_part=r0.get('src_part'),dst_part=r0.get('dst_part')))
    # START / RESET pipeline beside the clock spine (12.16b(iv)): one 1-bit stage per spine tap, launch flop on the
    # parent tap node leg, sync flop on the child tap node leg (LEG ps each), interval = that pair only (no region spread)
    for n in sorted(nodes):
        if par[n] is None: continue
        reg=lambda q: q[2:]
        if not n.startswith('c_'): continue
        p=par[par[n]]
        seg=0.0; ua=LEG; ub=LEG    # START-TREE-1 fork start port: launch + sync flops on the two legs of the fork node
        os_,oh=ocv(ua,ub,abs(nodes[n][0]-nodes[p][0])+abs(nodes[n][1]-nodes[p][1]),C)
        os_-=ocv(0,0,0,C)[0]; oh-=ocv(0,0,0,C)[1]   # no core latency on die start flops
        rows.append(dict(port='start__'+reg(n),src=reg(p),dst=reg(n),lca=p,d_ps=seg,unshared_a_ps=ua,unshared_b_ps=ub,
                         dist_um=0,p_up_ps=oh+LEG_CAL/2,p_dn_ps=os_+LEG_CAL/2,margin_ps=0.0,kind_est='start'))
    res['corners'][cn]={'all':rows}
    us=sorted(r['unshared_a_ps']+r['unshared_b_ps'] for r in rows)
    print(cn,'unshared med %.0f p90 %.0f max %.0f; |d| max %.0f; max arrival %.0f'%(us[len(us)//2],us[int(.9*len(us))],us[-1],max(abs(r['d_ps']) for r in rows),max(A.values())))
json.dump(res,open(out,'w'))
json.dump({'nodes':nodes,'parent':par,'tap':tapn},open(out.replace('.json','_tree.json'),'w'))
# --tree-parent args in BFS order of the start tree (parents first)
st_rows=[r for r in rows if r.get('kind_est')=='start']; kid=collections.defaultdict(list)
for r in st_rows: kid[r['src']].append(r)
order=[]; q=[root]
for x in q:
    for r in sorted(kid[x],key=lambda r:r['dst']): order.append(f"{r['dst']}={r['port']}"); q.append(r['dst'])
open(out.replace('.json','_tp.txt'),'w').write(' '.join('--tree-parent '+o for o in order))
print('start rows',len(st_rows),'tree-parent',len(order))
# long-loop report: crossings whose LCA is not one of the two regions' own fork/centre nodes chain (= not a tree edge)
def hop(a,b):
    pa=[n for n in path('c_'+a) if n.startswith('c_')]; pb=[n for n in path('c_'+b) if n.startswith('c_')]
    s={x:i for i,x in enumerate(pa)}
    for j,x in enumerate(pb):
        if x in s: return s[x]+j
TT=res['corners']['TT_droop-regions_corelat250']['all']
data=[r for r in TT if r.get('kind_est')!='start']
H=collections.Counter(hop(r['src'],r['dst']) for r in data)
far_=[r for r in data if hop(r['src'],r['dst'])>2]
print('data crossings by tree hops',sorted(H.items()),'| >2 hops',len(far_),'max unshared TT %.0f'%max(r['unshared_a_ps']+r['unshared_b_ps'] for r in data))
json.dump([dict(port=r['port'],src=r['src'],dst=r['dst'],hops=hop(r['src'],r['dst']),unshared_ps=round(r['unshared_a_ps']+r['unshared_b_ps'])) for r in far_],open(out.replace('.json','_longloop.json'),'w'))
