import json,collections,sys
d=json.load(open(sys.argv[1])); spec=json.load(open(sys.argv[2]))
cs=spec["cell_sites"]
rows=d["rows"]
def cell_of(name):
    n=name
    if n.startswith("ckm_w_"): n=n[6:]
    return cs.get(n)
C=collections.Counter()
ex=collections.defaultdict(list)
for r in rows:
    c=cell_of(r["name"])
    k=(r["kind"], " ".join(r["detail"].split()[:2]), c["kind"] if c else None)
    C[k]+=1
    if len(ex[k])<3: ex[k].append((r["name"], c["origin_um"] if c else None, c["part"] if c else None, r["detail"][:60]))
for k,v in C.most_common(): print(v,k, ex[k][:2])
# phase of pin rows relative to VSS (8.64k)
ph=collections.Counter()
for n,v in cs.items(): ph[round((v["origin_um"][1]+0.135)%8.64,2)]+=1
print("pin phase mod 8.64 (top)",ph.most_common(8), len(ph))
P=json.load(open("inputs/candidate_oneqc0733.json"))
