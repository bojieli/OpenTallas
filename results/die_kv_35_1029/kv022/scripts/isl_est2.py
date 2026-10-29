import json, sys, math, collections
p = json.load(open("plan/die_plan_sd35.json"))
taps = [(190.56,21.6),(570.72,21.6),(949.92,21.6),(1331.04,21.6),(1711.2,21.6)]
SRIM_Y = 33.48  # S rim centre (free y 17.28-49.68, README)
res = {}
for tn in ("kv3_sys_SD","kv3_sys_SD_v1"):
    t = p["partition_types"][tn]; c = t["contents"][0]; ox, oy = c["origin_um"]; w, h = c["outline_um"]
    m = (ox-4.32, oy-4.32, ox+w+4.32, oy+h+4.32)
    isl = t["clock"]["die_islands_um"]
    on = [r for r in isl if r[0] < m[2] and r[2] > m[0] and r[1] < m[3] and r[3] > m[1]]
    sz = collections.Counter((round(r[2]-r[0],3), round(r[3]-r[1],3)) for r in on)
    # clusters
    cl = []
    for r in sorted(on):
        cx, cy = (r[0]+r[2])/2, (r[1]+r[3])/2
        for g in cl:
            if abs(g[0]-cx) < 20 and abs(g[1]-cy) < 20: g[2] += 1; break
        else: cl.append([cx, cy, 1])
    singles = [g for g in cl if g[2] == 1]; groups = [g for g in cl if g[2] > 1]
    mv = [g[1]-SRIM_Y for g in singles]
    hist = collections.Counter(round(g[1]) for g in singles)
    # reset/start chain: E entry -> groups along y518 -> branch groups at y259 (original order by x desc)
    g518 = sorted([g for g in groups if g[1] > 400], key=lambda g: -g[0]); g259 = sorted([g for g in groups if g[1] < 400], key=lambda g: -g[0])
    entry = (1897.0, 518.5)
    path = [entry] + [(g[0], g[1]) for g in g518] + [(g[0], g[1]) for g in g259]
    legs = [abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in zip(path, path[1:])]
    # re-sited: E rim x 1892 down to S rim, then west along S rim; same relay count, equal split
    end = (min(g[0] for g in g259), SRIM_Y)
    newlen = abs(entry[1]-SRIM_Y) + abs(1892-end[0]) + 5
    nrel = len(path) - 1
    res[tn] = dict(on_macro=len(on), sizes={str(k): v for k, v in sz.items()}, clock_singles=len(singles),
                   relay_groups=len(groups), relay_group_cells=sum(g[2] for g in groups),
                   singles_by_row_y=dict(sorted(hist.items())), single_move_to_Srim_um=dict(min=round(min(mv),1), max=round(max(mv),1), mean=round(sum(mv)/len(mv),1)),
                   singles_nearest_tap_um=sorted(round(min(abs(g[0]-x)+abs(g[1]-y) for x, y in taps),1) for g in singles),
                   rst_chain_path=[[round(a,1), round(b,1)] for a, b in path], rst_chain_legs_um=[round(l,1) for l in legs],
                   rst_chain_len_um=round(sum(legs),1), rst_resite_len_um=round(newlen,1), rst_relays=nrel,
                   rst_resite_leg_um=round(newlen/nrel,1), rst_resite_min_relays_405=math.ceil(newlen/405)-1)
    print(tn, json.dumps(res[tn]))
json.dump(res, open("islands/isl_est2.json","w"), indent=1)
