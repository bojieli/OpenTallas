import sys,json,re,collections
sys.path.insert(0,"/srv/opentallas-scratch2/claude/rt/current/tools/die_plan")
import adv_fp_floorplan as fp
P=json.load(open(sys.argv[1]))
for n in sys.argv[2].split(","):
    t=P["partition_types"][n]; bxs=[fp._box(c) for c in t["hard_cores"]]
    w=fp.street_worst(t); cr=fp.core_crossings(t)
    print(n,"street",w[:6] if w else None,"crossbits",sum(c[2] for c in cr))
    # per-bit
    bits=collections.defaultdict(dict)
    for k,v in t["relay_sites"].items():
        m=re.match(r"u_ist_(.*)_(\d+)\.q\[(\d+)\]$",k)
        if m: bits[(m.group(1),int(m.group(3)))][int(m.group(2))]=v
    hop=collections.defaultdict(float); crs=collections.Counter(); inc=collections.Counter()
    for (l,b),st in bits.items():
        ks=sorted(st)
        for k in ks:
            p=st[k]
            if any(bx[0]<p[0]<bx[2] and bx[1]<p[1]<bx[3] for bx in bxs): inc[l]+=1
        for a,c in zip(ks,ks[1:]):
            hop[l]=max(hop[l],abs(st[a][0]-st[c][0])+abs(st[a][1]-st[c][1]))
            for bx in bxs:
                if fp._inside_um(st[a],st[c],bx)>=2: crs[l]+=1
    print("  perbit max hop",{k:round(v) for k,v in hop.items()},"core-crossing segs",dict(crs),"sites in cores",dict(inc))
    for s in t["internal_stations"]:
        if s.get("bit_sites_um"):
            bs=s["bit_sites_um"]; h=max(abs(bs[i][j][0]-bs[i+1][j][0])+abs(bs[i][j][1]-bs[i+1][j][1]) for i in range(len(bs)-1) for j in range(len(bs[0])))
            c=sum(1 for i in range(len(bs)-1) for j in range(len(bs[0])) for bx in bxs if fp._inside_um(bs[i][j],bs[i+1][j],bx)>=2)
            print("  bank lane",s["conn"],"max hop",round(h),"crossing",c)
    for s in t["ft_slots"][:2]:
        bs=s["bit_sites_um"]; h=max(abs(bs[i][j][0]-bs[i+1][j][0])+abs(bs[i][j][1]-bs[i+1][j][1]) for i in range(len(bs)-1) for j in range(len(bs[0])))
        c=sum(1 for i in range(len(bs)-1) for j in range(len(bs[0])) for bx in bxs if fp._inside_um(bs[i][j],bs[i+1][j],bx)>=2)
        print("  ft",s["name"],"max hop",round(h),"crossing",c)
