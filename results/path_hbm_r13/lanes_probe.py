import json, sys
W, plan = sys.argv[1:3]
sys.path.insert(0, W + '/tools/die_plan')
import hbm_r10_delta as R10, hbm_r13_mcast as M
P = json.load(open(plan + '/die_plan.json'))
mods = {h['module'] for tn in ('q_hub_nw', 'q_hub_ne') for h in P['partition_types'][tn]['hard_cores']}
D = M.port_dirs(mods)
print('no rtl', sorted(m for m, v in D.items() if v is None))
for part, tn in (('NW_hub', 'q_hub_nw'), ('NE_hub', 'q_hub_ne')):
    t = P['partition_types'][tn]; bi = R10.bus_intervals(P, part, t)
    _, r10 = R10.resolve_lanes(t, bi, log=lambda *a: None)
    st, r = M.resolve_lanes_mcast(t, bi, dirs=D, faces=M.bus_faces(P, part))
    print(tn, 'R10', {k: r10[k] for k in ('core_pin_bits', 'bus_supply_bits', 'unused_bus_bits', 'broadcast_bits')})
    print(tn, 'R13', {k: v for k, v in r.items() if not k.startswith('old_')})
