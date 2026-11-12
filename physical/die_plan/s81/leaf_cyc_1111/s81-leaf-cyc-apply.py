# S81-LEAF-CYC: apply the batch plan delta (lane permutation + quad station sites) -> plan_after.json + event.json
import json, sys, hashlib
plan, D, S, out, ev = sys.argv[1:6]
raw = open(plan, 'rb').read(); P = json.loads(raw)
d = json.load(open(D)); s = json.load(open(S))
for t, mv in d.items():
    T = P['partition_types'][t]
    for h in T['hard_cores']:
        if h['inst'] in mv:
            x, y, o = mv[h['inst']]; h['origin_um'] = [x, y]; h['orient'] = o
    T['internal_stations'] = s[t]
    T['note'] = (T.get('note', '') + ' | S81-LEAF-CYC 11-11: quad2 hi/ho station form (CS_HI/HO D2 GS2 G4, +4 vp write-back edges, '
                 'pin cycles 0) + positions-only lane permutation').lstrip(' |')
open(out, 'w').write(json.dumps(P))
E = dict(schema='opentallas.s81.leaf_cyc_event.v1', lane='S81-LEAF-CYC', advisory=False,
         base_plan=plan, base_plan_sha256=hashlib.sha256(raw).hexdigest(),
         plan_output=out, plan_output_sha256=hashlib.sha256(open(out, 'rb').read()).hexdigest(),
         rtl=dict(branch='claude/s81-leaf-cyc2-1111', sha='63676d718d59', base_merged='e46e22c3d777 + 237539f02426 (quad D1, on main)'),
         latency=dict(vp_hc_post_writeback_edges=+4, leaf_port_pin_cycles=0, compiler_reschedule='none (hc_post lowered PARTIAL, no fixed POST constant)',
                      tok='TOK-VERIFY-1 +2 edges AR -0.010% MTP -0.009% (upper bound); +4 edges linear -0.020% AR, -0.018% MTP'),
         eq='positions/orients of identical hcpost lane cores + internal_stations sites; RTL depth from the bind (63676d718d59)',
         types={t: dict(lanes_moved=len(d[t]), h_entries=sum('S81-LEAF-CYC' in e.get('note', '') for e in s[t])) for t in d})
json.dump(E, open(ev, 'w'), indent=1)
print(E['base_plan_sha256'][:12], '->', E['plan_output_sha256'][:12], len(d), 'types')
