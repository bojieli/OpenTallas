import json,sys,collections
s=json.load(open(sys.argv[1])); e=json.load(open(sys.argv[2]))["rows"]
cs=s["cell_sites"]
nets_by={}
for n in s["nets"]: nets_by.setdefault(n["edge"],n)
kinds=sys.argv[3].split(",")
k=0
for r in e:
    c=cs.get(r["name"][6:])
    if c and c["kind"] in kinds:
        n=nets_by.get(r["edge"])
        print(r["name"],c["kind"],c["origin_um"],c["part"],r["detail"],r["edge"],n and (n["drv"],n["load"],n["layer"],n["ndr"]))
        k+=1
        if k>=int(sys.argv[4]): break
