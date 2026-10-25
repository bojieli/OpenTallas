"""sidecar_from_bound.py REF_RTL_DIR REF_PARAM_REGEN BIND_NAMES BOUND_TOP OUT
Reconstruct the lost rtl6 GEN die.v.params.json (per-instance leaf parameters; KVJ-G2 / kv_expand / kv_health ledger) from
a bound top that was bound on it (kv41 bound_pv): every literal #(...) of a leaf instance in a partition module is the
as-built instance override, except the param_regen 'changed' values, which are reverted to their recorded as-built value.
Exactness is proven by re-binding and diffing against REF_RTL_DIR (not by this script)."""
import json, re, sys
from pathlib import Path
from collections import defaultdict
ref, preg, names, top, out = sys.argv[1:6]
ref = Path(ref)
nm = json.load(open(names))
# partition instance -> module
pm = {}
for m in re.finditer(r'^\s+(kv3_\w+)\s+(?:#\((?:[^()]|\([^()]*\))*\)\s*)?(\w+)\s*\(', Path(top).read_text(), re.M):
    pm[m.group(2)] = m.group(1)
def params(s):
    d, i = {}, 0
    for m in re.finditer(r'\.(\w+)\(', s):
        pass
    # balanced split
    k = 0
    while True:
        j = s.find('.', k)
        if j < 0: break
        mm = re.match(r'\.(\w+)\(', s[j:])
        if not mm: k = j + 1; continue
        p = j + mm.end(); depth = 1; q = p
        while depth:
            if s[q] == '(': depth += 1
            elif s[q] == ')': depth -= 1
            q += 1
        d[mm.group(1)] = s[p:q - 1]; k = q
    return d
leafp = {}
for mod in set(pm.values()):
    t = (ref / f'{mod}.sv').read_text()
    lp = {}
    for m in re.finditer(r'^\s+(\w+)\s+#\(((?:[^()]|\([^()]*\))*)\)\s+(u_\w+)\s*\(', t, re.M):
        if m.group(1).startswith(('ot_dp_', 'ot_reset_sync')):
            continue
        lp[m.group(3)] = params(m.group(2))
    leafp[mod] = lp
side = {}
miss = 0
for part, mod in pm.items():
    for loc, ps in leafp[mod].items():
        die = nm.get(f'{part}.{loc}')
        if die is None:
            miss += 1; continue
        side[die] = dict(ps)
for c in json.load(open(preg)).get('changed', []):
    side.setdefault(c['inst'], {})[c['param']] = c['asbuilt']
json.dump(side, open(out, 'w'), indent=1, sort_keys=True)
print(f'sidecar: {len(side)} instances, {sum(len(v) for v in side.values())} params, unmapped local leaves {miss}')
