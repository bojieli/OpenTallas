"""DIE-PROTO-3 HEAD prep: (1) kit variants mean/bound from kits_head/*.kit.json; (2) count-align bind = DIE-PROTO-2 ca2
bind_hp1.json + the FREG event K+1/sched_lat+1 on its 14 raised crossings (event.json changes.raise_and_mark) + freg mark
on all 18 FREG ports; NOT a re-planned bind (labelled)."""
import json, sys, glob, os, copy
kin, kout, bind_in, bind_out = sys.argv[1:5]
for v in ('mean', 'bound'):
    os.makedirs(f'{kout}_{v}', exist_ok=True)
for f in glob.glob(f'{kin}/*.kit.json'):
    m = json.load(open(f)); t = m['type']
    b = copy.deepcopy(m); b['variant'] = 'bound: lat = pin-flop min..max (type-wide, conservative)'
    json.dump(b, open(f'{kout}_bound/{t}.kit.json', 'w'), indent=1)
    a = copy.deepcopy(m); a['variant'] = 'mean: lat_min = lat_max = pin-flop mean (nominal per-type insertion)'
    for c in a['corners'].values():
        c['lat_min_ps'] = c['lat_max_ps'] = c['pinflops_mean']
    json.dump(a, open(f'{kout}_mean/{t}.kit.json', 'w'), indent=1)
B = json.load(open(bind_in))
raise_p = ['coll_WN3_u__0', 'coll_WN3_d__0'] + [f'ch{s}{i}_t__0' for s in 'EW' for i in range(6)]
mark_p = raise_p + ['coll_WN1_u__1', 'coll_WN1_d__0', 'coll_WN2_u__3', 'coll_WN2_d__0']
log = []
for p in raise_p:
    r = B['ports'].get(p)
    if r is None: log.append(f'MISSING {p}'); continue
    old = (r.get('K'), r.get('sched_lat'))
    r['K'] = r['K'] + 1
    if 'sched_lat' in r: r['sched_lat'] = r['sched_lat'] + 1
    log.append(f'RAISE {p} K/sched {old} -> {(r["K"], r.get("sched_lat"))} {r.get("src_part")}->{r.get("dst_part")}')
for p in mark_p:
    if p in B['ports']: B['ports'][p]['freg'] = 1
B['dieproto3_note'] = 'ca2 bind_hp1 (l48w bind re-hung on hp1 tree + 8 hp1 edits) + FREG K+1 on 14 crossings; NOT re-planned for lepB/FREG'
B['dieproto3_edits'] = log
json.dump(B, open(bind_out, 'w'))
print('\n'.join(log)); print('ports', len(B['ports']))
