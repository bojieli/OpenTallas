#!/usr/bin/env python3
"""DIE-KV-35 KV-021: event bind on the proofA native plan (planner K, --start-prev native6) + the SAME ECTL equalisation
compose_native.py applies (equalised to the event26 target sched, never stacked), C.bind + C.verify, then the event26
sidecar with ONLY count_aligned.ports{K,depth,sched_lat,tree} / table added_cycles updated, + strap_ties diff."""
import json, sys, copy
from pathlib import Path
T = 833.; ap = T / 8
src, out, tools = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, tools)
import count_align_bind as C
C25 = Path('/srv/opentallas-scratch2/claude/codex-kv-25-1029')
SIDE = Path(sys.argv[4])          # the sidecar the kv27f recipe binds (clock_landing_table)
PLAN = Path(sys.argv[5])          # event27f plan.json (strap declarations / ports)
p = json.load(open(src / 'native_plan.json'))
ev26 = json.load(open(C25 / 'event26/bind.json'))
ex26 = json.load(open(C25 / 'event26/summary.json'))['ectl_equalisation_extra']
nb = json.load(open(src / 'native_bind.json'))
extra = {}
for x in p['crossings']:
    if x['port'] not in ex26: continue
    tgt = ev26['ports'][x['port']]['sched_lat']; cur = nb['ports'][x['port']]['sched_lat']
    d = tgt - cur
    assert d >= 0, (x['port'], tgt, cur)
    extra[x['port']] = d
    if not d: continue
    lo = x['L_lo_ps'] + d * T; hi = x['L_hi_ps'] + d * T
    depth = next(n for n in [4, 8, 16] if hi <= (n - .5) * T - ap)
    for k in ['K_eff', 'K', 'lat_cycles', 'rx_lat_counts']: x[k] += d
    x.update(L_lo_ps=lo, L_hi_ps=hi, depth=depth, margin_lo_ps=lo - .5 * T, margin_hi_ps=(depth - .5) * T - hi)
    x['rtl'].update(K=x['K'], DEPTH=depth, GUARD_HI=depth)
b = C.bind(p, parts={pid: (v['src_part'], v['dst_part']) for pid, v in ev26['ports'].items()})
v = C.verify(b, samples=int(sys.argv[6]) if len(sys.argv) > 6 else 32)
assert not v['identity_and_loop_errors'] and v['sim_window_violations'] == 0, v
out.mkdir(parents=True, exist_ok=True)
(out / 'bind.json').write_text(json.dumps(b, indent=1)); (out / 'verify.json').write_text(json.dumps(v, indent=1))
# diff vs event26 bind
chg = {pid: dict(K=(ev26['ports'][pid]['K'], c['K']), sched=(ev26['ports'][pid]['sched_lat'], c['sched_lat']),
                 depth=(ev26['ports'][pid]['depth'], c['depth']), src=c['src_part'], dst=c['dst_part'])
       for pid, c in b['ports'].items()
       if any(c[k] != ev26['ports'][pid][k] for k in ('K', 'sched_lat', 'depth', 'tree'))}
regchg = [k for k in b['regions'] if any(b['regions'][k].get(f) != ev26['regions'].get(k, {}).get(f)
                                         for f in ('parent', 'tree_port', 'edge_fall', 'pad', 'origin_part', 'n_nominal'))]
partchg = [k for k in b['parts'] if b['parts'][k] != ev26['parts'].get(k)]
side = json.load(open(SIDE)); side2 = copy.deepcopy(side)
ca = side2['count_aligned']
n_side = 0
for pid, c in b['ports'].items():
    if pid in ca['ports']:
        new = {k: c[k] for k in ('K', 'depth', 'sched_lat', 'tree')}
        if ca['ports'][pid] != new: n_side += 1; ca['ports'][pid] = new
for r in side2['ports']:
    if r['port'] in b['ports']: r['added_cycles'] = b['ports'][r['port']]['sched_lat']
(out / 'sidecar.json').write_text(json.dumps(side2, indent=1))
plan = json.load(open(PLAN))
s_old = C.strap_ties(side['count_aligned'], plan); s_new = C.strap_ties(side2['count_aligned'], plan)
(out / 'straps.json').write_text(json.dumps(s_new, indent=1))
idiff = {q: {k: (s_old['instances'][q]['values'].get(k), val) for k, val in s_new['instances'][q]['values'].items()
             if s_old['instances'][q]['values'].get(k) != val}
         for q in s_new['instances'] if s_new['instances'][q]['values'] != s_old['instances'][q]['values']}
tdiff = [t for t in s_new['types'] if s_new['types'][t]['straps'] != s_old['types'][t]['straps']]
vdiff = {t: (s_old['types'][t]['variants'], s_new['types'][t]['variants']) for t in s_new['types']
         if s_new['types'][t]['variants'] != s_old['types'][t]['variants']}
itype = sorted({s_new['instances'][q]['type'] for q in idiff})
summ = dict(ectl_extra_new={k: v for k, v in extra.items() if v != ex26[k] or True}, ectl_extra_changed={k: (ex26[k], extra[k]) for k in extra if extra[k] != ex26[k]},
            ports_changed_vs_event26=len(chg), sched_total=(sum(x['sched_lat'] for x in ev26['ports'].values()), sum(x['sched_lat'] for x in b['ports'].values())),
            regions_changed=len(regchg), parts_changed=len(partchg), sidecar_ports_changed=n_side,
            verify={k: v[k] for k in v if k not in ('sim_worst_ports',)},
            strap_type_pin_changes=tdiff, strap_variant_changes=vdiff, strap_instances_retied=len(idiff), strap_types_retied=itype,
            straps_summary_old=s_old['summary'], straps_summary_new=s_new['summary'])
(out / 'summary.json').write_text(json.dumps(dict(summ, ports=chg, instance_ties=idiff), indent=1))
print(json.dumps(summ, indent=0))
