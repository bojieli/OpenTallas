# rst_n port fanout census on a placed geom.tsv (same traversal as DIE-QC-33 solve.py): flops whose async/any pin is
# reached from rst_n through buffers only, and their L1 distance to the rst_n pin.
import sys,json
sys.path.insert(0,sys.argv[2])
import geom_rules as G
D=G.Design(sys.argv[1])
rp=[p for p in D.pins if p["name"]=="rst_n"][0]
fr=[D.pin_net[rp["k"]]];seen=set(fr);asr=[]
while fr:
    nf=[]
    for nn in fr:
        for s in D.nets[nn][2]:
            if s[0]=="i" and not s[2]:
                k=D.kind(s[1])
                if k=="S": asr.append(s[1])
                elif k=="B":
                    for o in D.drives.get(s[1],[]):
                        if o not in seen: seen.add(o);nf.append(o)
    fr=nf
d=sorted(((abs(G.ctr(D.cells[c])[0]-rp["x"])+abs(G.ctr(D.cells[c])[1]-rp["y"])),D.cells[c][6]) for c in asr)
print(json.dumps({"rst_n_direct_flops":len(d),"max":round(d[-1][0],2) if d else None,"gt150":sum(x>150 for x,_ in d),"flops":[[round(x,2),n] for x,n in d]},indent=0))
