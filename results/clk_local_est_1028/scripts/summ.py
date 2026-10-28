import json, sys, collections, statistics as S
d = json.load(open(sys.argv[1])); rows = d["rows"]
def q(v, p): v = sorted(v); return v[min(len(v)-1, int(p*len(v)))]
for c in ("TT", "FF"):
    x = d["corners"][c]; print(c, {k: x[k] for k in ("crossings","below","worst_lo","worst_hi","ocv_max")})
tt = [r for r in rows if "TT" in r]
un = [r["TT"]["un"] for r in tt]; oc = [max(r["TT"]["ocv_lo"] or 0, r["TT"]["ocv_hi"] or 0) for r in tt]
print("unshared TT ns: med %.2f p90 %.2f max %.2f  | ocv med %.0f p90 %.0f max %.0f" % (q(un,.5)/1e3, q(un,.9)/1e3, max(un)/1e3, q(oc,.5), q(oc,.9), max(oc)))
print("hist unshared ns:", sorted(collections.Counter(min(12, int(u/1000)) for u in un).items()))
print("LCA depth hist:", sorted(collections.Counter(r["TT"]["depth"] for r in tt).items()))
print("LCA node top:", collections.Counter(r["TT"]["node"] for r in tt).most_common(6))
# ratio ocv/unshared
rat = [o/u for o,u in zip(oc,un) if u>500]; print("ocv/unshared med %.3f p90 %.3f" % (q(rat,.5), q(rat,.9)))
wn = [r["wander"] or 0 for r in tt]; print("wander ps med %.0f max %.0f" % (q(wn,.5), max(wn)))
sp = [r["span_ps"] for r in tt]; print("lag span ps med %.0f p90 %.0f max %.0f; (D8 usable 7T-200=%.0f, D16 %.0f)" % (q(sp,.5), q(sp,.9), max(sp), 7*833.333-200, 15*833.333-200))
for Dn in (8,16):
    b = [r["best%d"%Dn] for r in rows]; print("replan-K DEPTH %d: <100 %d / %d, min %.1f" % (Dn, sum(v<100 for v in b), len(b), min(b)))
print("cur depth hist", collections.Counter(r["depth"] for r in rows))
print("worst 10 by unshared (distinct tags):")
seen=set()
for r in sorted(tt, key=lambda r: -r["TT"]["un"]):
    if r["tag"] in seen: continue
    seen.add(r["tag"]); t=r["TT"]
    print("  %-28s %-12s un %.2f ns (A %.2f B %.2f) node %s st %s/%s dist %.2f mm ocv %.0f/%.0f margin TT %.0f/%.0f FF %s best8 %.0f best16 %.0f" % (r["tag"], r["port"], t["un"]/1e3, t["ua"]/1e3, t["ub"]/1e3, t["node"], t["stA"], t["stB"], t["dist_mm"], t["ocv_lo"] or 0, t["ocv_hi"] or 0, t["ml"], t["mh"], r.get("FF",{}).get("ml"), r["best8"], r["best16"]))
    if len(seen)>=10: break
print("worst 10 by min margin TT/FF (distinct tags):")
seen=set()
for r in sorted(rows, key=lambda r: min(r[c][k] for c in ("TT","FF") if c in r for k in ("ml","mh"))):
    if r["tag"] in seen: continue
    seen.add(r["tag"]); t=r["TT"]
    print("  %-28s %-12s un %.2f ns node %s dist %.2f ocv %.0f margin TT %.0f/%.0f FF %.0f/%.0f wander %.0f span %.0f best8 %.0f best16 %.0f" % (r["tag"], r["port"], t["un"]/1e3, t["node"], t["dist_mm"], max(t["ocv_lo"] or 0,t["ocv_hi"] or 0), t["ml"], t["mh"], r["FF"]["ml"], r["FF"]["mh"], r["wander"] or 0, r["span_ps"], r["best8"], r["best16"]))
    if len(seen)>=10: break
ri = d["corners"]["TT"]["region_ins"]; mx = sorted(ri.items(), key=lambda kv: -kv[1][1])
print("region tap arrival TT ns (abs, from die root) min..max over regions: lo %.2f hi %.2f; median region max %.2f" % (min(v[0] for v in ri.values())/1e3, max(v[1] for v in ri.values())/1e3, q([v[1] for v in ri.values()],.5)/1e3))
print("in-region spread (max-min) med %.0f max %.0f ps" % (q([v[1]-v[0] for v in ri.values()],.5), max(v[1]-v[0] for v in ri.values())))
