#!/usr/bin/env python3
"""H-DIE 0600 (10-16): die stream-clock alternatives on the d3b service+SM placement (run.tcl + die.v instance list + v5 plan +
v15 grants given as files): model insertion, buffer count and NON-COMMON clock path between communicating neighbours (the
491 consecutive SM_HBM relay pairs).  Usage: clock_alt_model.py <base|granted|grid|open> <htree|lane|quad> [bin_um]
Inputs (paths below): /tmp/hdie_d3b_run.tcl, /tmp/hdie_an/{insts.txt,v5P.json,grants.json}."""
import sys,re,json,time
sys.path.insert(0, __import__('os').path.dirname(__file__))
import die_clock_tree as dct
variant=sys.argv[1]; mode=sys.argv[2] if len(sys.argv)>2 else 'htree'; bin_um=float(sys.argv[3]) if len(sys.argv)>3 else 1600.0
SIZE={'hfd_stn_v15_cc1182':(43.2,129.6),'ot_hbm3e_phy_rc_e8p5':(8500.032,1177.2),'ot_hbm_accel_smh_static':(6609.6,1712.08),
      'ot_hbm_svc_pc_ctrl_leaf':(170.64,170.64),'ot_hbm_svc_sm_group':(1036.8,228.96)}
M={}
for l in open('/tmp/hdie_an/insts.txt'):
    m,i=l.split(); M[i]=m
pl={}
for l in open('/tmp/hdie_d3b_run.tcl'):
    mm=re.match(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\} -orientation (\S+)',l)
    if mm and mm.group(1) in M: pl[mm.group(1)]=(float(mm.group(2)),float(mm.group(3)),mm.group(4))
W,H=31018.4,21277.693
P=json.load(open('/tmp/hdie_an/v5P.json'))
g=json.load(open('/tmp/hdie_an/grants.json'))
rch={s['name']:s.get('reserved_channels',[]) for s in g['slots']}
# map SM instance -> slot name: SM instance names?
def carve(rects,chs,x0,y0,w,h,o):
    for ch in chs:
        cx0,cx1=ch['x_um']; cy0,cy1=ch['y_um']
        if o in ('MY','R180'): cx0,cx1=w-cx1,w-cx0
        if o in ('MX','R180'): cy0,cy1=h-cy1,h-cy0
        cut=(x0+cx0,y0+cy0,x0+cx1,y0+cy1); nr=[]
        for (a0,b0,a1,b1) in rects:
            if cut[0]>=a1 or cut[2]<=a0 or cut[1]>=b1 or cut[3]<=b0: nr.append((a0,b0,a1,b1)); continue
            for r in ((a0,b0,cut[0],b1),(cut[2],b0,a1,b1),(max(a0,cut[0]),b0,min(a1,cut[2]),cut[1]),(max(a0,cut[0]),cut[3],min(a1,cut[2]),b1)):
                if r[2]-r[0]>0.01 and r[3]-r[1]>0.01: nr.append(r)
        rects=nr
    return rects
SMCH=[{'x_um':[3284.8,3324.8],'y_um':[0,1712.08]},{'x_um':[0,6609.6],'y_um':[836.04,876.04]}]
# extra: islands grid -- 40um column every 1600um and row every 856 in SM (variant 'grid')
def sm_channels(w,h):
    if variant=='granted': return SMCH
    if variant=='grid':
        chs=[{'x_um':[x,x+40],'y_um':[0,h]} for x in (1632.4,3284.8,4937.2)]+[{'x_um':[0,w],'y_um':[836.04,876.04]}]
        return chs
    return []
obs=[]; sinks=[]
for i,(x,y,o) in pl.items():
    m=M[i]; w,h=SIZE[m]
    if o in ('R90','R270','MXR90','MYR90'): w,h=h,w
    if m=='hfd_stn_v15_cc1182':
        sinks.append((i,'clk',x+w/2,y+h/2)); continue
    if variant=='open' and m not in ('ot_hbm3e_phy_rc_e8p5',):
        r=[]
    elif m=='ot_hbm_accel_smh_static':
        r=carve([(x,y,x+w,y+h)],sm_channels(w,h),x,y,w,h,o)
    else: r=[(x,y,x+w,y+h)]
    obs+=r
    if m in ('ot_hbm_accel_smh_static','ot_hbm_svc_sm_group'):
        sinks.append((i,'clk',x+w/2,y+h/2))
for n,b in P.items():
    if isinstance(b,dict) and 'x' in b and n.split('_')[0] not in ('phy','pc','sm'):
        if variant=='open': continue
        obs.append((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
t0=time.time()
q=lambda inst: (re.search(r'(SW|SE|NW|NE)',inst) or re.search('',inst)) and (re.search(r'(SW|SE|NW|NE)',inst).group(1) if re.search(r'(SW|SE|NW|NE)',inst) else ('S' if pl[inst][1]<H/2 else 'N')+('W' if pl[inst][0]<W/2 else 'E'))
t=dct.build(W,H,obs,(15505.0,10555.0),sinks,q,mode=mode,bin_um=bin_um)
mo=t['model']
pads=sum(1 for b in t['buffers'] if '_bP_' in b[0] or 'P' in b[0].split('_')[1])
print(json.dumps(dict(variant=variant,mode=mode,bin_um=bin_um,sinks=len(sinks),buffers=mo['buffers'],pad_bufs=pads,insertion_ps=mo['model_insertion_ps'],free=mo['free_cells_frac'],secs=round(time.time()-t0))))
# ---- non-common path between communicating neighbours (consecutive relay stages of one chain) ----
pos={b[0]:(b[2],b[3]) for b in t['buffers']}
sinkpos={s[0]:(s[2],s[3]) for s in sinks}
par={}; 
for n,d,loads in t['nets']:
    for ld in loads:
        key=ld[1] if ld[0]!='pin' else ld[1]
        par[key]=d[1] if d[0]!='port' else None
def p_of(k): return pos.get(k) or sinkpos.get(k)
arr={}
def A(k):
    if k in arr: return arr[k]
    p=par.get(k)
    if p is None: arr[k]=0.0; return 0.0
    (x0,y0),(x1,y1)=p_of(p),p_of(k)
    L=abs(x1-x0)+abs(y1-y0)
    arr[k]=A(p)+dct.stage_ps(min(L,420))*(max(1,L/420))
    return arr[k]
sys.setrecursionlimit(100000)
def anc(k):
    out=[]
    while k is not None: out.append(k); k=par.get(k)
    return out
chains={}
for s in sinks:
    m=re.match(r'rly_(\w\w)(\d+)_(\d+)',s[0])
    if m: chains.setdefault((m.group(1),m.group(2)),[]).append((int(m.group(3)),s[0]))
nc=[]
for key,lst in chains.items():
    lst.sort()
    for (a,x),(b,y) in zip(lst,lst[1:]):
        ax=anc(x); ay=set(anc(y))
        lca=next(k for k in ax if k in ay)
        nc.append(max(A(x),A(y))-A(lca))
nc.sort()
import statistics
if nc: print(json.dumps(dict(variant=variant,mode=mode,neighbour_pairs=len(nc),noncommon_ps_median=round(statistics.median(nc)),p90=round(nc[int(.9*len(nc))]),max=round(nc[-1]),ocv5pct_pessimism_max_ps=round(0.10*nc[-1]))))
