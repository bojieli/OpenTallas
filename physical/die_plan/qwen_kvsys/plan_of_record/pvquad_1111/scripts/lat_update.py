#!/usr/bin/env python3
"""lat_update.py PLAN_IN RESITE_REPORT PLAN_OUT DELTA_TSV : price station_resite's added forward-leg cycles.
A pv forward leg (internal_stations conn bus:o_X) is carried by the die lane whose first port is (partition of the type,
o_X): its fixed_cycles holds that leg's internal station count ("+N internal forward stations"). For every conn whose
count changed (final-old, once per conn), add the change to fixed_cycles of each such lane and note it.
ft-slot station changes need no edit: Plan.lane_latency() reads the slot's stations. Run gen.py latency --inplace after."""
import json, sys, collections
pin, rep, pout, tsv = sys.argv[1:5]
P = json.load(open(pin)); R = json.load(open(rep))
ports = P['ports']; ports = ports if isinstance(ports, dict) else {x['id']: x for x in ports}
parts = P['partitions']; parts = list(parts.values()) if isinstance(parts, dict) else parts
by_type = collections.defaultdict(list)
for p in parts: by_type[p['type']].append(p['name'])
first = collections.defaultdict(list)
for ln in P['lanes']:
    s = ports[ln['ports'][0]]['src']; first[(s['part'], s['bus'])].append(ln)
rows = []
for tn, t in R['types'].items():
    add = {}
    for c in t.get('chains_added_cycles', []):
        add[c['conn']] = max(add.get(c['conn'], 0), int(c['final']) - int(c['old']))
    for conn, a in add.items():
        bus = conn[4:]
        for part in by_type.get(tn, []):
            for ln in first.get((part, bus), []):
                old = int(ln.get('fixed_cycles', 0)); ln['fixed_cycles'] = old + a
                ln['note'] = (ln.get('note', '') + ' | ' if ln.get('note') else '') + \
                    'CPL-KV-PV-3 11-11 pv quad re-slot: forward leg %s %d -> %d internal stations (COORD approved pin cycles)' % (bus, old, old + a)
                rows.append((ln['id'], tn, part, bus, old, old + a))
json.dump(P, open(pout, 'w'), indent=1); open(pout, 'a').write('\n')
with open(tsv, 'w') as f:
    f.write('lane\ttype\tpartition\tbus\tfixed_before\tfixed_after\n')
    for r in rows: f.write('\t'.join(map(str, r)) + '\n')
print('lanes repriced', len(rows), 'cycles added', sum(r[5] - r[4] for r in rows))
