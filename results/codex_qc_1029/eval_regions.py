# DIE-QC-19: routed clock-only GRT arrivals -> per region spread of (tap late arrival + declared core insertion);
# c_* also: A0 (core tap) minus glue mean gap. usage: eval13.py TRIAL_DIR ARR_DIR_PREFIX PLAN OUT_JSON TOOLS_DIR PART_REGION_JSON
import json, collections, statistics as st, sys
sys.path.insert(0, sys.argv[5]); import schema as S
K, A, PL, OUT = sys.argv[1:5]
P = S.Plan(json.load(open(PL)))
T = json.load(open(K + "/clock/tree.json"))
reg = json.load(open(sys.argv[6]))["part_region"]
contracts = {(p, n): tp for p, pp in P.parts.items() for n, _, _, tp in S.core_taps(P, pp["type"])}
out = {}
for c in ("TT", "FF"):
    tl = {}
    for l in open(f"{A}_{c}/arr_{c}.txt"):
        f = l.split()
        if f[0] == "T": tl[f[1]] = float(f[2])
    com = S.common_latency_ps(P, c); G = collections.defaultdict(list)
    for t in T["taps"]:
        tp = contracts.get((t["part"], t["tap"])); lat = S.core_tap_insertion_ps(tp, c) if tp else com
        G[reg[t["part"]]].append((tl[t["port"]] + lat, bool(tp)))
    rows = {}
    for g, L in G.items():
        b = [x for x, _ in L]; r = dict(n=len(L), spread=round(max(b) - min(b), 1))
        cc = [x for x, k in L if k]; gg = [x for x, k in L if not k]
        if cc and gg:
            r.update(core_minus_glue=round(st.mean(cc) - st.mean(gg), 1), glue_spread=round(max(gg) - min(gg), 1),
                     core_spread=round(max(cc) - min(cc), 1))
        rows[g] = r
    out[c] = rows
summ = {}
for c, rows in out.items():
    Kc = collections.defaultdict(list)
    for g, r in rows.items(): Kc["c" if g.startswith("c_") else ("su_c" if g.endswith("su_c") else g.split("_")[0])].append(r)
    summ[c] = {}
    for k, L in sorted(Kc.items()):
        d = dict(regions=len(L), spread_med=round(st.median(x["spread"] for x in L), 1), spread_max=max(x["spread"] for x in L))
        g = [x["core_minus_glue"] for x in L if "core_minus_glue" in x]
        if g: d.update(core_minus_glue_min=min(g), core_minus_glue_med=round(st.median(g), 1), core_minus_glue_max=max(g),
                       glue_spread_max=max(x["glue_spread"] for x in L if "glue_spread" in x))
        summ[c][k] = d
    print(c); [print(" ", k, v) for k, v in summ[c].items()]
json.dump(dict(scope="DIE-QC-19 clock-only GRT arrivals; spread = max-min of (tap late + declared insertion) per region, nominal (no OCV)",
               trial=K, arr=A, plan=PL, summary=summ, regions=out), open(OUT, "w"), indent=1)
