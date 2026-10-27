import json, sys, collections
plans = sys.argv[1:]
for pp in plans:
    P = json.load(open(pp + '/die_plan.json'))
    for tn in ('q_hub_nw', 'q_hub_ne'):
        t = P['partition_types'][tn]; W, H = t['outline_um']
        hc = {h['inst']: h for h in t['hard_cores']}
        agg = collections.defaultdict(list)
        for s in t['internal_stations']:
            c = s['conn']
            if not c.startswith('bus:'): continue
            b = c[4:]
            if b.split('_')[0] not in ('L4', 'L96', 'L126', 'L51', 'L101', 'L4m', 'L96m', 'L126m', 'L51m', 'L101m'): continue
            other = s['capture'] if str(s['launch']).startswith('face') else s['launch']
            agg[b].append((len(s['regs_um']), s.get('serial_k'), str(other)[:40], [round(v) for v in s['from_um']], [round(v) for v in s['to_um']], s['bits']))
        print('==', pp.split('/')[-1], tn, 'W,H', W, H)
        for b, v in sorted(agg.items()):
            v.sort(reverse=True)
            print('  ', b, 'n', len(v), 'max regs', v[0][0], v[:2])
