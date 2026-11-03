import re,sys,glob,os,json
rows=[]
for f in sorted(glob.glob(sys.argv[1]+"/*.log")):
    t=open(f).read(); m=re.search(r"^R (\S+) (\S+) nseg (\d+) seg (\S+)",t,re.M)
    if not m: continue
    corner,name,nseg,seg=m.groups()
    blocks=re.split(r"\nStartpoint: ",t)[1:]
    r=dict(corner=corner,case=name,nseg=int(nseg),seg_um=float(seg))
    for b in blocks:
        ep=re.search(r"Endpoint: (\S+)",b).group(1); typ=re.search(r"Path Type: (\w+)",b).group(1)
        sl=float(re.search(r"([-\d.]+)\s+slack",b).group(1))
        key=("wire" if ep=="u_c" else "bay")+"_"+typ
        r[key+"_slack"]=sl
        if ep=="u_c":
            # launch->D data delay excluding the launching cell's clk->Q
            lines=[l for l in b.splitlines() if re.match(r"\s+[\d.]+\s+[-\d.]+\s+[\d.]+\s+[v^]",l)]
            vals=[list(map(float,l.split()[:3])) for l in lines]
            if vals:
                r[typ+"_slew_max"]=max(v[0] for v in vals)
                r[typ+"_launch_cq"]=vals[1][1] if len(vals)>1 else 0
                r[typ+"_wirebuf_ps"]=round(vals[-1][2]-vals[1][2],1)
    rows.append(r)
json.dump(rows,open(sys.argv[2],"w"),indent=1)
for r in rows: print(r)
