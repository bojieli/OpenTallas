import sys, json, collections
P = json.load(open(sys.argv[1]))
PO = {p["id"]: p for p in P["ports"]}
c = collections.Counter(); hopn = collections.Counter()
for l in P["lanes"]:
    ps = [PO[x] for x in l["ports"] if x in PO]
    if not ps: continue
    a, b = ps[0]["src"]["part"], ps[-1]["dst"]["part"]
    if not (a.startswith("NE_") or b.startswith("NE_")): continue
    k = tuple(sorted((a, b))); c[k] += ps[0]["width"]; hopn[k] = max(hopn[k], len(ps))
row = ["NE_b101","NE_b100","NE_b110","NE_su31","NE_su30","NE_spu1","NE_su21","NE_su20","NE_b111","NE_b103","NE_b102","NE_b112","NE_b113","NE_su00","NE_su01"]
for r in row:
    tot = sum(v for k, v in c.items() if r in k)
    hub = c.get(tuple(sorted((r, "NE_hub"))), 0)
    nb = sorted(((v, [x for x in k if x != r][0], hopn[k]) for k, v in c.items() if r in k), reverse=True)[:5]
    print(f"{r:9s} lanes-bits {tot:6d} hub {hub:6d} top {nb}")
