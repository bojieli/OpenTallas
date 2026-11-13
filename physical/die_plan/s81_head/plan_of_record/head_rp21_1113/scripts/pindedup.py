"""HEAD-97 rp21: a private raw-export landing pin that shares its M-layer site with another pin of the type moves one
8.64 step along its face (G0 pin_sites / GRT-0080)."""
import json, sys
src, out = sys.argv[1:3]
P = json.load(open(src)); n = 0
for tn, t in P['partition_types'].items():
    pins = ((t.get('clock') or {}).get('landing_contract') or {}).get('pins') or []
    W, H = t['outline_um']
    priv = {r['port'] for r in t.get('reset_start_raw_exports', []) if not r.get('existing_port')}
    occ = {}
    for p in pins: occ.setdefault((round(p['xy_um'][0], 3), round(p['xy_um'][1], 3), p.get('layer')), []).append(p)
    for k, v in occ.items():
        if len(v) < 2: continue
        for p in [q for q in v if q['name'] in priv][: len(v) - 1]:
            x, y = p['xy_um']; vert = x < 10 or x > W - 10
            for s in (1, -1, 2, -2, 3, -3):
                nx, ny = (x, round(y + s * 8.64, 4)) if vert else (round(x + s * 8.64, 4), y)
                if (round(nx, 3), round(ny, 3), p.get('layer')) not in occ:
                    p['xy_um'] = [nx, ny]; occ[(round(nx, 3), round(ny, 3), p.get('layer'))] = [p]; n += 1
                    print('moved', tn, p['name'], [x, y], '->', p['xy_um']); break
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n'); print('pins moved', n)
