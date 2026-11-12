"""TOOLS GEOM_TSV OUT_JSON -> every r2r capture > 405 um (launch, capture, distance) + grouping by bus name stem"""
import sys, json, re, collections
sys.path.insert(0, sys.argv[1] + "/autopilot")
import geom_rules as G
D = G.Design(sys.argv[2])
pairs = []
m = G.r2r_metrics(D, capture_pairs=pairs)
stem = lambda n: re.sub(r"\\?\[\d+\\?\]", "", n.replace("$_DFF_P_", "").replace("$_DFF_N_", "")).rsplit("/", 1)[0] if "/" in n else re.sub(r"\\?\[\d+\\?\]", "", n)
g = collections.Counter((stem(p["launch"]), stem(p["capture"])) for p in pairs)
mx = collections.defaultdict(float)
for p in pairs:
    k = (stem(p["launch"]), stem(p["capture"])); mx[k] = max(mx[k], p["distance_um"])
json.dump(dict(metrics=m, pairs=pairs, groups=[dict(launch=a, capture=b, n=n, max_um=mx[(a, b)]) for (a, b), n in g.most_common()]), open(sys.argv[3], "w"), indent=1)
print(m["r2r_captures_gt405"], m["r2r_max"])
for (a, b), n in g.most_common(40):
    print(n, round(mx[(a, b)], 1), a, "->", b)
