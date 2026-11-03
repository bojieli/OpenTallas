"""TOK-HBM-3: re-evaluate the bind's as-built landing groups (bus_groups.json 'landing', COORD R8) with the plan cycles
of two plans: a group is aligned when every as-built same-stage member class lands at the same bound depth offset.
Members: (lane, asbuilt_stages); bound depth = plan cycles(lane) (no extra landing pads in the HBM bind)."""
import json, sys
B, la, lb, out = sys.argv[1:5]
L = json.load(open(B + '/bus_groups.json'))['landing']
ca = {k: v['cycles'] for k, v in json.load(open(la))['lanes'].items()}
cb = {k: v['cycles'] for k, v in json.load(open(lb))['lanes'].items()}
def aligned(g, c):
    # as-built offset between members must be preserved: bound - asbuilt equal for all members
    vals = {c[m['lane']] - m['asbuilt_stages'] for m in g['members']}
    return len(vals) == 1
res = dict(groups=0, skipped_unknown_lane=0, mis_before=0, mis_after=0, new=[], healed=[], still_changed=[])
for g in L:
    lanes = {m['lane'] for m in g['members']}
    if not all(l in ca and l in cb for l in lanes): res['skipped_unknown_lane'] += 1; continue
    res['groups'] += 1
    a, b = aligned(g, ca), aligned(g, cb)
    res['mis_before'] += not a; res['mis_after'] += not b
    rec = dict(sink=g['sink'], sink_part=g['sink_part'], lanes={l: [ca[l], cb[l]] for l in sorted(lanes)},
               ports=sorted({m['sink_port'] for m in g['members']})[:8])
    if a and not b: res['new'].append(rec)
    elif b and not a: res['healed'].append(rec)
    elif not a and not b and any(ca[l] != cb[l] for l in lanes): res['still_changed'].append(rec)
json.dump(res, open(out, 'w'), indent=1)
print({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items()})
for k in ('new', 'healed', 'still_changed'):
    print(k)
    seen = set()
    for r in res[k]:
        key = (r["sink_part"], json.dumps(r["lanes"], sort_keys=True))
        if key in seen: continue
        seen.add(key); print('  ', r['sink_part'], r['sink'][:60], r['lanes'], r['ports'])
