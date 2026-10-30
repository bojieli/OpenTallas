"""DIE-QC-39 A0: can equal-count register leaves (core_infra equal_load: sink counts within a domain differ by <= 1)
keep every leaf -> sink leg <= LEGCAP um?  Uses the V2 placed register xy per clock domain (gate ancestor) and the
generator's own recursive-bisection split(); tries leaf sizes and reports the worst leg / legs over the cap."""
import csv, sys, json, math, collections
sys.path.insert(0, sys.argv[3]); from gen_a0_tree21 import split, equal_counts, centroid, man
D = sys.argv[1]; out = {}
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    def dom(n):
        m = T[n]["parent"]
        while m != "port:ck":
            if T[m]["master"].startswith("ICG"): return m
            m = T[m]["parent"]
        return "root"
    doms = collections.defaultdict(list)
    for n, r in T.items():
        if r["kind"] == "sink" and not r["master"].startswith("ot_"): doms[dom(n)].append((float(r["x"]), float(r["y"]), n))
    res = {}
    for size in (21, 16, 12, 10, 8):
        legs = []; nleaf = 0; per = {}
        for g, pts in doms.items():
            grps = split(pts, equal_counts(len(pts), math.ceil(len(pts) / size)))
            nleaf += len(grps); w = 0
            for grp in grps:
                c = centroid(grp)
                for p in grp: legs.append(man(p, c)); w = max(w, man(p, c))
            per[g.split(".")[-1]] = round(w, 1)
        legs.sort()
        res[size] = dict(leaves=nleaf, leg_max=round(legs[-1], 1), leg_p99=round(legs[int(0.99 * len(legs))], 1),
                         regs_leg_gt60=sum(l > 60 for l in legs), regs_leg_gt40=sum(l > 40 for l in legs),
                         worst_domains=sorted(per.items(), key=lambda kv: -kv[1])[:4])
        print(t, size, res[size])
    out[t] = res
json.dump(out, open(sys.argv[2], "w"), indent=1)
