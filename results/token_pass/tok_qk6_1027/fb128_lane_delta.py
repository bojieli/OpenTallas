import json, gzip, collections, sys
P = json.load(gzip.open('hm_r26.json.gz', 'rt')); X = json.load(open('xing.json')); J = json.load(open('lat_q3.json'))['lanes']
ports = {p['id']: p for p in P['ports']}
cnt = collections.Counter(); kinds = collections.defaultdict(set)
for q in X['ports']:
    cnt[q['lane']] += q['added_cycles']; kinds[q['lane']].add(q['kind'])
mis = 0; L = []
for l in P['lanes']:
    a, b = ports[l['ports'][0]], ports[l['ports'][-1]]
    s = a['src']['part'] + '.' + a['src']['bus']; t = b['dst']['part'] + '.' + b['dst']['bus']
    j = J.get(l['id'])
    if j is None or (j['src']['part'] + '.' + j['src']['bus'], j['dst']['part'] + '.' + j['dst']['bus']) != (s, t): mis += 1
    L.append(dict(lane=l['id'], src=s, dst=t, width=j['width'] if j else None, delta=cnt.get(l['id'], 0), kinds=sorted(kinds.get(l['id'], []))))
print('lanes', len(L), 'endpoint mismatches vs q3', mis, 'lanes with delta', sum(1 for x in L if x['delta']), 'sum', sum(x['delta'] for x in L),
      'crossing lanes not in plan', len(set(cnt) - {x['lane'] for x in L}))
json.dump(dict(lanes=L, note='TOK-QK-6: 128-group fallback (codex d06cccbc4 row_groups_crossings.json), +3 per landed face, hm_r26 lane endpoints'), open('lane_delta_fb128.json', 'w'), indent=0)
