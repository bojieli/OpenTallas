"""DIE-S81-13 F1 (c): tap pairs of the relay FF timing arcs whose launch or capture moves with the x2 re-tap.
Walk each relay FF's D back through buffers/inverters to its launching FF or port; record (launch tap, capture tap, wire um,
stages) before/after the re-tap.  usage: f1_pairs.py JOINT4 OVERLAY OUT.json"""
import json, sys, re, collections
J, OV, OUT = sys.argv[1:4]
a = json.load(open(J + "/allocated_sites.json")); ov = json.load(open(OV))
G = json.load(open(J + "/endpoint_net_graph_v2.json")); C = G["cells"]; N = G["nets"]
def loc(c): return ov["cells"][c]["origin_um"] if c in ov["cells"] else (a[c]["origin_um"] if c in a else C[c]["origin_um"])
def drv(net):
    for p in N[net]["pins"]:
        if p["direction"] == "OUTPUT": return p["pin"].rsplit("/", 1)[0], p["master"]
    return None, None
def innet(c):
    pins = C[c]["pins"]; ins = [p for p, v in pins.items() if v["direction"] == "INPUT"]
    return pins[ins[0]]["net"] if ins else None
def tap(f):
    c, m = drv(C[f]["pins"]["CLK"]["net"]); mt = re.search(r"clk_(t\d+|c\d+)", c or "")
    return "clk_" + mt.group(1) if mt else None
ffs = [c for c in a if C.get(c, {}).get("master", "").startswith("DFF")]
rt = ov["retap"]
rows = []; cnt = collections.Counter()
for f in ffs:
    net = C[f]["pins"]["D"]["net"]; st = 0; wire = 0.0; prev = loc(f); src = None
    for _ in range(60):
        c, m = drv(net)
        if c is None: src = ("PORT", net); break
        if c not in C and c not in a: src = (c, "CORE"); break
        p = loc(c); wire += abs(p[0] - prev[0]) + abs(p[1] - prev[1]); prev = p
        if m.startswith("DFF"): src = (c, m); break
        if not (m.startswith("BUF") or m.startswith("INV")): src = (c, m); break
        st += 1; net = innet(c)
    if src is not None and src[1] == "CORE":
        ct0 = tap(f); ct1 = rt.get(f, ct0)
        if ct0 != ct1:
            rows.append(dict(launch=src[0], capture=f, before=["core:" + src[0], ct0], after=["core:" + src[0], ct1], wire_um=round(wire, 1), stages=st))
            cnt["changed_core_launch"] += 1
        else: cnt["same_core"] += 1
        continue
    if src is None or src[0] == "PORT" or not src[1].startswith("DFF"):
        cnt["src_" + ("port" if src and src[0] == "PORT" else "logic")] += 1; continue
    L = src[0]
    lt0, ct0 = tap(L), tap(f)
    lt1, ct1 = rt.get(L, lt0), rt.get(f, ct0)
    if (lt0, ct0) != (lt1, ct1):
        rows.append(dict(launch=L, capture=f, before=[lt0, ct0], after=[lt1, ct1], wire_um=round(wire, 1), stages=st))
        cnt["changed"] += 1
    else:
        cnt["same"] += 1
pc = collections.Counter((tuple(r["before"]), tuple(r["after"])) for r in rows)
print(dict(cnt)); print([(k, v) for k, v in pc.most_common()])
json.dump(dict(rows=rows, pairs=[dict(before=list(k[0]), after=list(k[1]), n=v) for k, v in pc.items()]), open(OUT, "w"), indent=0)
