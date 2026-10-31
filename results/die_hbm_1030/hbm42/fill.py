import json,sys,itertools
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
raw=json.load(open(sys.argv[1])); out=sys.argv[2]
CORE=(388.8,345.6); HALO=4.32; G=4.32
need={'q_b113':int(sys.argv[3]),'q_b111':int(sys.argv[4])}
fig,axs=plt.subplots(1,2,figsize=(22,10),dpi=100)
for ax,tn in zip(axs,('q_b113','q_b111')):
    t=raw['partition_types'][tn]; W,H=t['outline_um']
    boxes=[(c['origin_um'][0],c['origin_um'][1],c['origin_um'][0]+c['outline_um'][0],c['origin_um'][1]+c['outline_um'][1],c['inst']) for c in t['hard_cores']]
    sites=[]
    for s in t['ft_slots']:
        for st in s.get('bit_sites_um') or []: sites+= [tuple(p) for p in st]
        if not s.get('bit_sites_um'): sites+=[tuple(p) for p in s.get('regs_um',[])]
    regs=[tuple(p) for s in t.get('internal_stations',[]) for p in s.get('regs_um',[])]
    nbits=sum(len(s.get('width') and [0]*0 or []) for s in [])
    stn_bits=sum(int(s.get('width',1))*len(s.get('regs_um',[])) for s in t.get('internal_stations',[]))
    ft_bits=sum((int(s['width'])+1)*max(int(s.get('stations',1)),1) for s in t['ft_slots'])
    std_area=(stn_bits+ft_bits)*1.404*0.27/0.7  # flops at 70% local density
    core_a=sum((b[2]-b[0])*(b[3]-b[1]) for b in boxes)
    # greedy lattice placement of new lane cores avoiding cores(+halo), ft sites and station regs (keep-out 5 um)
    occ=[(b[0]-HALO,b[1]-HALO,b[2]+HALO,b[3]+HALO) for b in boxes]
    pts=sites+regs
    placed=[]
    def free(x,y):
        r=(x-HALO,y-HALO,x+CORE[0]+HALO,y+CORE[1]+HALO)
        if r[0]<0 or r[1]<0 or r[2]>W or r[3]>H: return False
        for o in occ+placed:
            if r[0]<o[2] and o[0]<r[2] and r[1]<o[3] and o[1]<r[3]: return False
        return True
    def hits(x,y):
        return sum(1 for p in pts if x-5<p[0]<x+CORE[0]+5 and y-5<p[1]<y+CORE[1]+5)
    cand=[(x,y) for x in [i*G for i in range(int(W/G))] for y in [j*G for j in range(int(H/G))]]
    cand=[c for c in cand if free(*c)]
    tot_hits=0
    for k in range(need[tn]):
        cand=[c for c in cand if free(*c)]
        if not cand: break
        c=min(cand,key=lambda c:(hits(*c),c[1],c[0]))
        tot_hits+=hits(*c); placed.append((c[0]-HALO,c[1]-HALO,c[0]+CORE[0]+HALO,c[1]+CORE[1]+HALO))
    new_a=len(placed)*CORE[0]*CORE[1]
    free_after=W*H-core_a-new_a
    print(tn,'outline',W,H,'cores',len(boxes),'core_area',round(core_a),'new placed',len(placed),'of',need[tn],'displaced ft/station sites',tot_hits,
          'macro frac before/after',round(core_a/(W*H),3),round((core_a+new_a)/(W*H),3),'est std area (flops)',round(std_area),'std fill of free area after',round(std_area/free_after,3))
    ax.set_title(f'{tn}: grey = existing cores, red = {len(placed)} new lane cores, dots = ft/station sites',fontsize=9)
    ax.set_aspect('equal'); ax.add_patch(Rectangle((0,0),W,H,fill=False,ec='k'))
    for b in boxes: ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc='0.8',ec='k')); ax.text(b[0]+5,b[1]+5,b[4].replace('u_sfucore_Q_',''),fontsize=7)
    for p in placed: ax.add_patch(Rectangle((p[0]+HALO,p[1]+HALO),CORE[0],CORE[1],fc='salmon',ec='r',alpha=.6))
    if pts: ax.scatter([p[0] for p in pts[::3]],[p[1] for p in pts[::3]],s=0.2,c='b')
    ax.set_xlim(-20,W+20); ax.set_ylim(-20,H+20)
plt.tight_layout(); plt.savefig(out)
