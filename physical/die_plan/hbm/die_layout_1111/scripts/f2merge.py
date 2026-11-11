"""DIE-LAYOUT-HBM F2 merge: take every ft_s0_resite slot with stations_after == stations_before (EQ by construction) from
the group plans and copy that ft_slot onto the target plan. Slots that needed added stations are NOT taken (listed for pricing)."""
import json, sys, glob
tgt, out, d = sys.argv[1], sys.argv[2], sys.argv[3]
SKIP = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else set()   # G0-new-error slots (root/L8101x2: moves the over-reach to the q_su30 L8101x1 boundary hop, 673 um)
P = json.load(open(tgt)); took, priced = [], []
for led in sorted(glob.glob(d + '/grp.0?.ledger.json')):
    L = json.load(open(led)); G = json.load(open(led.replace('.ledger.json', '.plan.json')))
    add = L['summary'].get('added_cycles', {})
    for s in L['slots']:
        if s.get('kept'): continue
        key = f"{s['type']}/{s['slot']}"
        if key in SKIP: priced.append((key, 'skipped: G0 new error', s.get('hop_before_um'))); continue
        if key in add: priced.append((key, add[key], s.get('hop_before_um'))); continue
        src = [x for x in G['partition_types'][s['type']]['ft_slots'] if x['name'] == s['slot']][0]
        dst = P['partition_types'][s['type']]['ft_slots']
        i = [k for k, x in enumerate(dst) if x['name'] == s['slot']][0]
        assert dst[i]['stations'] == src['stations'] and dst[i]['in_window_um'] == src['in_window_um'] and dst[i]['out_window_um'] == src['out_window_um']
        src = dict(src); src['note'] = src.get('note', '') + ' | DIE-LAYOUT-HBM 11-11 F2: ft_s0_resite count-kept re-derive'
        dst[i] = src; took.append((key, s.get('hop_before_um'), s.get('hop_after_um')))
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print('TOOK', took); print('PRICED (not taken)', priced)
