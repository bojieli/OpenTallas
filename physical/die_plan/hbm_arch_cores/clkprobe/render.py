# HBM-CLKSTRUCT render: sinks coloured by FF clock arrival, clock-buffer tree edges, macros, clk port, worst hold pairs.
import csv,sys,json,re,numpy as np,collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d,W,H,mw,mh,title,out=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]),sys.argv[6],sys.argv[7]
nm=lambda s:s.replace('\\','')
S={nm(r['inst']):r for r in csv.DictReader(open(d+"/sinks.csv"))}
E=list(csv.DictReader(open(d+"/clknets.csv")))
Hd=list(csv.DictReader(open(d+"/hold.csv")))
fig,ax=plt.subplots(1,2,figsize=(16,9*max(H/W,0.6)))
for a in ax:
    a.add_patch(Rectangle((0,0),W,H,fill=False,lw=1))
    for r in S.values():
        if r['kind']=='macro': a.add_patch(Rectangle((float(r['x']),float(r['y'])),mw,mh,fc='#ddd',ec='k',lw=.5))
    a.set_xlim(-5,W+5);a.set_ylim(-5,H+5);a.set_aspect('equal')
ff=[r for r in S.values() if r['kind']=='ff' and r['arr_max']]
arr=np.array([float(r['arr_max'])/1e12 for r in ff])
sc=ax[0].scatter([float(r['x']) for r in ff],[float(r['y']) for r in ff],c=arr,s=2,cmap='turbo')
plt.colorbar(sc,ax=ax[0],label='FF clock arrival ps (placement RC)')
mac=[r for r in S.values() if r['kind']=='macro']
for r in mac: ax[0].text(float(r['x'])+3,float(r['y'])+3,"%.0f"%(float(r['arr_max'])/1e12),fontsize=8)
# tree edges: nets whose sinks are buffers (non-leaf) ; colour by net level
bufs=set(r['sink'] for r in E if r['smaster'].startswith(('BUF','INV','CLK')))
for r in E:
    if r['sink'] in bufs or r['drv']=='clk':
        ax[1].plot([float(r['dx']),float(r['sx'])],[float(r['dy']),float(r['sy'])],'-',lw=.6,color='tab:blue' if 'leaf' not in r['net'] else 'tab:green')
leafn=collections.Counter(r['net'] for r in E if 'leaf' in r['net'])
pos={r['sink']:(float(r['sx']),float(r['sy'])) for r in E}
for r in E:
    if r['drv']=='clk': ax[1].plot(float(r['dx']),float(r['dy']),'r*',ms=14); ax[0].plot(float(r['dx']),float(r['dy']),'r*',ms=14)
taps={r['drv']:(float(r['dx']),float(r['dy'])) for r in E if re.match(r'^ot_dtap_\d+$',r['drv'])}
for t,(x,y) in taps.items():
    ax[1].plot(x,y,'o',ms=9,mfc='none',mec='red',mew=1.5); ax[0].plot(x,y,'o',ms=9,mfc='none',mec='k',mew=1.2)
bx=[pos[b] for b in bufs]; ax[1].scatter([p[0] for p in bx],[p[1] for p in bx],s=4,c='navy')
# worst hold reg2reg pairs
rr=sorted([h for h in Hd if h['io']=='0'],key=lambda h:float(h['slack']))[:300]
n=0
for h in rr:
    a=S.get(nm(h['start'].rsplit('/',1)[0]));b=S.get(nm(h['end'].rsplit('/',1)[0]))
    if a and b:
        ax[0].plot([float(a['x']),float(b['x'])],[float(a['y']),float(b['y'])],'k-',lw=.8); ax[0].plot(float(b['x']),float(b['y']),'kx',ms=4);n+=1
nrr=sum(1 for h in Hd if h['io']=='0'); wrr=min([float(h['slack'])/1e12 for h in Hd if h['io']=='0'] or [0])
ax[0].set_title(f"{title}\nFF clk arrival {arr.min():.0f}..{arr.max():.0f} (mean {arr.mean():.0f}) ps; x = worst {n} hold capture (rr {nrr} ep, WNS {wrr:.0f} ps)",fontsize=9)
ax[1].set_title(f"clock tree: {len(bufs)} buffers (blue=trunk, green=leaf-driver nets), red * = clk port" + (f", red o = {len(taps)} density taps" if taps else ""),fontsize=9)
plt.tight_layout(); plt.savefig(out,dpi=110)
par={nm(r['sink']):nm(r['drv']) for r in E}
def tapof(i):
    for _ in range(60):
        if re.match(r'^ot_dtap_\d+$',i): return i
        if i not in par: return None
        i=par[i]
tg=collections.defaultdict(list)
for k,r in S.items():
    if r['kind']=='ff' and r['arr_max']:
        t=tapof(k)
        if t: tg[t].append(float(r['arr_max'])/1e12)
tst=dict(taps=len(tg),tap_mean_spread=(max(np.mean(v) for v in tg.values())-min(np.mean(v) for v in tg.values())) if tg else None,
         max_in_tap_spread=max((max(v)-min(v)) for v in tg.values()) if tg else None)
json.dump(dict(**tst,view=title,ff_arr_min=arr.min(),ff_arr_max=arr.max(),ff_arr_mean=arr.mean(),rr_hold_ep=nrr,rr_wns=wrr,clock_buffers=len(bufs)),open(out+".json","w"),indent=1)
