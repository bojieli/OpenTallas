"""offline: retry the failed landing bands of a composed plan with the patched search (used = that type's placed bands)"""
import json, sys, collections
sys.path.insert(0, 'tools/die_plan')
import clock_landing_plan as CLP
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
T = P['partition_types']; F = S['collector']['placement_failures']
byt = collections.defaultdict(list)
for f in F: byt[f['type']].append(f)
fixed, still = 0, []
for tn, fs in sorted(byt.items()):
    t = T[tn]
    lc = t.get('clock', {}).get('landing_contract', {})
    used = [b['rect_um'] for b in (lc.get('bands') or {}).values() if b.get('rect_um')]
    for f in fs:
        b = CLP._bus_geom(t, f['bus']); wd = int(b.get('width') or 2)
        try:
            band = CLP._storage_band(t, f['bus'], wd if not f['bus'].startswith('monitor') else 2, used)
            used.append(band['rect_um']); fixed += 1
        except Exception as e:
            still.append(dict(type=tn, bus=f['bus'], width=wd, face=b.get('face'), err=str(e)[-50:]))
print(json.dumps(dict(failures=len(F), fixed=fixed, still=len(still), still_types=collections.Counter(s['type'] for s in still))))
json.dump(still, open(sys.argv[3], 'w'), indent=1)
