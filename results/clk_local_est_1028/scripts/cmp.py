import json, sys, collections
d = sys.argv[1]; feed = sys.argv[2] if len(sys.argv) > 2 else "fish"
cur = {r["port"]: r for r in json.load(open(f"{d}/cur.json"))["rows"]}
L = json.load(open(f"{d}/loc_v1/loc_{feed}.json")); rows = L["rows"]
topo = json.load(open(f"{d}/cur_topo.json"))
def q(v, p):
    v = sorted(v); return v[min(len(v)-1, int(p*len(v)))] if v else 0
match = sum(1 for r in rows if r["id"] in cur); print("loc rows", len(rows), "matched to bind ports", match)
on = [r for r in rows if r["on_feed"]]; off = [r for r in rows if not r["on_feed"]]
for nm, S in (("on-feed", on), ("off-feed", off)):
    u = [r["unshared"] for r in S]; p = [r["p_tt"] for r in S]
    print(f"LOCAL {feed} {nm}: n {len(S)} bits {sum(r['width'] for r in S)} unshared ns med {q(u,.5)/1e3:.2f} p90 {q(u,.9)/1e3:.2f} max {max(u or [0])/1e3:.2f}; OCV p_tt med {q(p,.5):.0f} max {max(p or [0]):.0f}; tree hops {sorted(collections.Counter(min(r['tree_hops'],20) for r in S).items())}")
for U in (1500, 2500, 4000):
    big = [r for r in off if r["unshared"] > U]
    print(f"  off-feed unshared > {U/1e3} ns: {len(big)} crossings, {sum(r['width'] for r in big)} bits, region pairs {len({(r['ra'],r['rb']) for r in big})}, tree hops max {max([r['tree_hops'] for r in big] or [0])}, bit-hops extra {sum(r['width']*(r['tree_hops']-1) for r in big)}")
dep = collections.Counter((r["depth"] or "FAIL") for r in rows); print("LOCAL depth", dict(dep), "D16 fail", sum(not r["d16_ok"] for r in rows))
print("LOCAL depth by class: on", dict(collections.Counter(r["depth"] for r in on)), "off", dict(collections.Counter(r["depth"] for r in off)))
ml = [min(r["m_lo"], r["m_hi"]) for r in rows if r["depth"]]; print("LOCAL min CA margin %.1f, <100: %d" % (min(ml), sum(m < 100 for m in ml)))
# current split by relation
par = topo["parent"]
def lin(r):
    o = [r]
    while par.get(o[-1]) is not None: o.append(par[o[-1]])
    return o
rel = collections.defaultdict(list)
for r in cur.values():
    a, b = r["tag"].split("->")
    if a not in par or b not in par: continue
    la, lb = lin(a), lin(b); L_ = next((x for x in la if x in set(lb)), None)
    h = la.index(L_) + lb.index(L_) if L_ else 99
    rel["tree-edge" if h == 1 else "loop"].append(r)
for k, S in rel.items():
    u = [r["TT"]["un"] for r in S if "TT" in r]; o = [max(r["TT"]["ocv_lo"] or 0, r["TT"]["ocv_hi"] or 0) for r in S if "TT" in r]
    m = [min(r[c][x] for c in ("TT","FF") if c in r for x in ("ml","mh")) for r in S]
    print(f"CURRENT {k}: n {len(S)} unshared ns med {q(u,.5)/1e3:.2f} p90 {q(u,.9)/1e3:.2f} max {max(u)/1e3:.2f}; OCV med {q(o,.5):.0f} max {max(o):.0f}; gate margin min {min(m):.1f} <100 {sum(x<100 for x in m)}; replan-K D8 <100 {sum(r['best8']<100 for r in S)} min {min(r['best8'] for r in S):.0f}")
# tree-edge crossings in current with large unshared: why
te = sorted(rel["tree-edge"], key=lambda r: -r["TT"]["un"])[:5]
for r in te: print("  cur tree-edge big:", r["tag"], r["port"], "un %.2f (A %.2f B %.2f) node %s dist %.2f" % (r["TT"]["un"]/1e3, r["TT"]["ua"]/1e3, r["TT"]["ub"]/1e3, r["TT"]["node"], r["TT"]["dist_mm"]))
# loc: same feed parents as current?
fp = L["feed"]["parent"]; same = sum(1 for r in fp if fp[r] is not None and par.get(r) == fp[r]); print("LOCAL feed edges equal to current region-tree edges:", same, "/", sum(1 for r in fp if fp[r] is not None), "root", L["feed"]["root"], "cur root", [r for r in par if par[r] is None])
w = sorted(rows, key=lambda r: -r["unshared"]); seen=set(); print("LOCAL worst 10 unshared:")
for r in w:
    k=(r["ra"],r["rb"])
    if k in seen: continue
    seen.add(k); print(f"  {r['ra']}->{r['rb']} {r['id']} on_feed {r['on_feed']} hops {r['tree_hops']} lca {r['lca']} un {r['unshared']/1e3:.2f} (A {r['ua']/1e3:.2f} B {r['ub']/1e3:.2f}) p {r['p_tt']:.0f} D{r['depth']} m {r['m_lo']}/{r['m_hi']}")
    if len(seen) >= 10: break
