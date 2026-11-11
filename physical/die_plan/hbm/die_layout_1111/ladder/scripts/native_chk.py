"""Replicates native_istations.annotate's fixed_cycles rule over ALL lanes (bind stops at the first).
usage: native_chk.py TOOLS_DIR ASBUILT.json PLAN.json [PLAN ...]"""
import json, sys
sys.path.insert(0, sys.argv[1])
import native_istations as NI
ab = json.load(open(sys.argv[2]))
sel = set(ab.get('internal_stations_types', []))
for pl in sys.argv[3:]:
    P = json.load(open(pl)); T = P['partition_types']; parts = {p['name']: p for p in P['partitions']}
    pm = {p['id']: p for p in P['ports']}
    outb = {}
    for ln in P['lanes']:
        a, z = pm[ln['ports'][0]], pm[ln['ports'][-1]]
        outb.setdefault((a['src']['part'], a['src']['bus']), []).append((ln, z['dst']['part'], z['dst']['bus']))
    bad, req = [], {}
    for part, p in parts.items():
        if p['type'] not in sel: continue
        t = T[p['type']]
        for e in NI.source_entries(t, NI.selected_buses(ab, p['type'], t.get('split_of', p['type']))):
            name = e['conn'][4:]; count = len(e['regs_um'])
            m = outb.get((part, name), [])
            if len(m) != 1: bad.append(('nolane', part, name, len(m))); continue
            ln, dpart, dbus = m[0]
            tgt = T.get(parts.get(dpart, {}).get('type'), {})
            rows = [r for r in tgt.get('internal_stations', []) if r.get('conn') == 'bus:' + dbus]
            rcv = max({len(r['regs_um']) for r in rows}, default=0)
            fx = int(ln.get('fixed_cycles', 0)); req[ln['id']] = count + rcv
            if fx != count + rcv: bad.append((ln['id'], 'fixed', fx, 'need', count, rcv))
    print(pl, 'lanes under rule', len(req), 'violations', len(bad))
    for b in bad: print('  ', b)
    json.dump(req, open(pl + '.native_req.json', 'w'))
