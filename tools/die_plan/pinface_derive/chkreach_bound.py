"""DIE-QC-97 11-11: stage -> relay reach on the BIND-RESOLVED names.  For every su type: the relays the bind emitted
(rtl/<type>.sv, reset_anchor.bound_tree), the plan's START stage / local reset names after the bind's anchor remaps
(bind_reset_anchor.json), hop = |dx|+|dy| from the stage xy_um to the bound relay.  usage: chkreach_bound.py SRC PLAN BIND_DIR"""
import json, sys
SRC, PL, BD = sys.argv[1:4]
sys.path.insert(0, SRC + '/tools/die_plan')
import reset_anchor as A
raw = json.load(open(PL))
rec = {r['type']: {m['name']: m['to'] for m in r['remaps']} for r in json.load(open(BD + '/bind_reset_anchor.json'))['receipts'] if r}
bad = 0
for tn, t in raw['partition_types'].items():
    if not any('su_lane' in c['module'] for c in t.get('hard_cores', [])):
        continue
    bt = A.bound_tree(open(f'{BD}/rtl/{tn}.sv').read()); R = {r['q']: r for r in (bt or {}).get('relays', [])}
    mp = rec.get(tn, {}); ck = t['clock']; hops = []; miss = []
    pts = [(s['raw_reset'], s['xy_um']) for k in ('landing_reader_start', 'landing_writer_start')
           for br in ((ck.get(k) or {}).get('branches') or {}).values() for s in br.get('stages', []) if s.get('raw_reset')]
    pts += [(s['raw'], s['xy_um']) for s in ck.get('landing_local_resets') or [] if s.get('raw')]
    for n, xy in pts:
        r = R.get(mp.get(n, n))
        if r is None: miss.append(mp.get(n, n)); continue
        hops.append(abs(r['xy'][0] - xy[0]) + abs(r['xy'][1] - xy[1]))
    over = sum(h > 405 + 1e-6 for h in hops); bad += over + len(miss)
    print(tn, 'bound relays', len(R), 'remapped', len(mp), 'refs', len(pts), 'missing', miss[:6], 'max hop %.1f' % max(hops or [0]), 'over405', over, flush=True)
print('TOTAL bad', bad)
