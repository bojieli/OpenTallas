"""TOK-HBM-3: d44s -> d44t lane latency delta (gen.py latency outputs) joined to bind leaves and plan pad groups."""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2])); bl = json.load(open(sys.argv[3]))
leaves = {x['lane']: x['leaves'] for x in bl['buses']}
rows = []
for lid, d in sorted(b['lanes'].items(), key=lambda kv: kv[0]):
    o = a['lanes'].get(lid)
    if o is None or o['cycles'] != d['cycles'] or o.get('pad') != d.get('pad') or o['stations'] != d['stations']:
        rows.append(dict(lane=lid, param=d['param'], src=f"{d['src']['part']}.{d['src']['bus']}", dst=f"{d['dst']['part']}.{d['dst']['bus']}",
                         width=d['width'], before=o and o['cycles'], after=d['cycles'], d_cycles=d['cycles'] - (o['cycles'] if o else 0),
                         st_before=o and o['stations'], st_after=d['stations'], pad_before=o and o.get('pad', 0), pad_after=d.get('pad', 0),
                         leaves=leaves.get(lid)))
ga = {g['name']: g for g in a.get('groups', [])}; gb = {g['name']: g for g in b.get('groups', [])}
gch = [dict(name=n, before=ga.get(n, {}).get('cycles'), after=g['cycles'], lanes=g['lanes']) for n, g in gb.items() if ga.get(n, {}).get('cycles') != g['cycles']]
out = dict(schema='opentallas.tok_hbm_3.lat_delta.v1', before_digest=a['plan_digest'], after_digest=b['plan_digest'],
           lanes_total=len(b['lanes']), changed=len(rows), sum_added_cycles=sum(r['d_cycles'] for r in rows),
           rows=rows, landed_groups_changed=gch)
json.dump(out, open(sys.argv[4], 'w'), indent=1)
for r in rows: print(r['lane'], r['before'], '->', r['after'], f"st {r['st_before']}->{r['st_after']} pad {r['pad_before']}->{r['pad_after']}", r['src'], '->', r['dst'], r['width'], (r['leaves'] or [])[:3])
print('changed', len(rows), 'sum', out['sum_added_cycles'], 'groups changed', len(gch))
