#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: clock_landing_plan.compose with the HEAD l48uo settings (region monitor, ring_ff bands, spread
2.0, observer = the sidecar collector observer). On l48uo itself this reproduces every type up to the HEAD post-compose
fields; on the split plan it leaves the 24 other types byte-identical. Writes OUT_plan.json / OUT_side.json."""
import json, sys, time
sys.path.insert(0, 'tools/die_plan')
import clock_landing_plan as CLP
plan_path, side_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
p = json.load(open(plan_path)); s = json.load(open(side_path))
obs = s['collector']['observer']
observer = {k: obs[k] for k in ('module', 'instance_suffix', 'fault_port', 'ready_port')}
t0 = time.time()
r = CLP.compose(p, s, plan_path=plan_path, observer_part=obs['part'], observer=observer, monitor='region',
                band_reserve='ring_ff', band_spread=2.0, band_ring='ff')
json.dump(r[0], open(out + '_plan.json', 'w'), indent=1); json.dump(r[1], open(out + '_side.json', 'w'), indent=1)
print('COMPOSE_OK', round(time.time() - t0, 1))
