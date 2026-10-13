#!/usr/bin/env python3
"""xp unit bench vectors from a sm_tput_bench meta.json (the price sheet): one line per record
{xr 1, xb 7, nxe 8, sec 15, nsec 11, cost x8 16, cls 4}.  x bases are 8-sector aligned (xp compiler obligation).
x-slot allocation (compiler side, liveness aware; the hardware only verifies): a load never overlaps a slot that a later
record still reuses, and avoids the slots of the two previous records (else one, else none), so it runs under them."""
import json, sys
d = json.load(open(sys.argv[1])); out = open(sys.argv[2], 'w'); base = 64; sec = {}; slot = {}; okey = {}; last = []; hist = []; cur = {}
nx = lambda q: 8 * (-(-q['K'] // (512 if q['fmt'] in ('BF16', 'INT8') else 1024 if q['fmt'] == 'FP8E4M3' else 2048)))
CLS = {}
for i, r in enumerate(d['records']):
    pf = r['fmt']; K = r['K']
    nxe = 8 * (-(-K // (512 if pf in ('BF16', 'INT8') else 1024 if pf == 'FP8E4M3' else 2048)))
    key = (r['XB'], nxe)
    if not r['XR']:
        sec[key] = base; base += 8 * (-(-K // 64)) + 8
        keep = [slot[j] for j in last if any(q['XR'] and (q['XB'], nx(q)) == okey[j] for q in d['records'][i:])]
        prev = []
        for j in reversed(hist):
            if slot[j] not in prev: prev.append(slot[j])
        for depth in (2, 1, 0):
            bad = keep + prev[:depth]
            xb = next((b for b in range(0, 129 - nxe) if all(b >= s + n or s >= b + nxe for s, n in bad)), None)
            if xb is not None: break
        assert xb is not None, i
        last = [j for j in last if slot[j][0] >= xb + nxe or xb >= slot[j][0] + slot[j][1]]
        slot[i] = (xb, nxe); okey[i] = key; last.append(i); cur[key] = i
    hist.append(cur[key]); r['XB2'] = slot[cur[key]][0]
    how = 'batched' if 'batched' in r['cost_how'] else 'barrier'
    c = CLS.setdefault((pf, K, how), len(CLS))
    v = r['XR'] << 61 | r['XB2'] << 54 | nxe << 46 | sec[key] << 31 | (-(-K // 8)) << 20 | int(round(r['cost'] * 8)) << 4 | c
    out.write(f'{v:016X}\n')
print(len(d['records']), ' '.join(f'{c}={k[0]}/K{k[1]}/{k[2]}' for k, c in CLS.items()))
