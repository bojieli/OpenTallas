# S81-LEAF-CYC: positions-only delta = lane slot permutation (identical hcpost lane cores; module/outline checked equal)
# -> {type: {inst: [x, y, orient]}} for explorer/route_supply, plus quad station sites (centroid of the 4 lane pins after).
import json, sys
plan, permf, out = sys.argv[1:4]
P = json.load(open(plan))['partition_types']; perm = json.load(open(permf))
D, S = {}, {}
for t, r in perm.items():
    hc = {h['inst']: h for h in P[t]['hard_cores']}
    ln = {int(k.split('g_ln[')[1].split(']')[0]): h for k, h in hc.items() if '.g_ln[' in k}
    assert len({(h['module'], tuple(h['outline_um'])) for h in ln.values()}) == 1, t
    D[t] = {}
    for l, s in enumerate(r['perm']):
        src = ln[s]
        if s != l:
            D[t][ln[l]['inst']] = [src['origin_um'][0], src['origin_um'][1], src['orient']]
    S[t] = []
    for g in range(4):
        hs = [ln[r['perm'][l]] for l in range(4 * g, 4 * g + 4)]
        c = [round(sum(h['origin_um'][i] + h['outline_um'][i] / 2 for h in hs) / 4, 3) for i in (0, 1)]
        S[t].append(dict(group=g, lanes=list(range(4 * g, 4 * g + 4)), site_um=c))
    print(t, 'moved lanes', len(D[t]))
json.dump(D, open(out, 'w'), indent=1)
json.dump(S, open(out.replace('.json', '_sites.json'), 'w'), indent=1)
