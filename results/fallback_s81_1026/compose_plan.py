#!/usr/bin/env python3
"""FALLBACK-S81: compose the landed fallback plan with the EXISTING main tool clock_landing_plan.compose
(real fclk/ready/fault pins, storage bands, reverse-wavefront monitor cohorts). Observer = reset wavefront root.
usage: compose_plan.py PLAN LANDED_CROSSINGS OUT_PLAN OUT_SIDECAR"""
import json, sys, time
sys.path.insert(0, 'tools/die_plan')
import schema as S, reset_tree as RT, clock_landing_plan as CLP
plan, table, outp, outs = sys.argv[1:5]
raw = json.load(open(plan)); tab = json.load(open(table))
P = S.Plan(raw, plan); W = RT.wf_plan(P)
root = W.get('root') or next(pn for pn, v in W['parts'].items() if v.get('release', 1) == min(x.get('release', 1) for x in W['parts'].values()))
t0 = time.time()
new, side = CLP.compose(raw, tab, plan_path=plan, observer_part=root)
new['note'] = (new.get('note', '') + '; FALLBACK-S81 10-26 landed regions ' + tab.get('mode', '') + ' g' + str(tab.get('block'))).strip('; ')
json.dump(new, open(outp, 'w'), indent=1); json.dump(side, open(outs, 'w'), indent=1)
c = side['collector']
print(json.dumps(dict(observer=root, types_before=len(raw['partition_types']), types_after=len(new['partition_types']),
    ports_before=len(raw['ports']), ports_after=len(new['ports']), infra_edges=len(new['clock']['landing_network']['edges']),
    placement_failures=len(c['placement_failures']), max_monitor_hop_um=c['max_die_hop_um'],
    boot_ready_cycles=c['boot_budget']['ready_at_glue_max_cycles'], secs=round(time.time()-t0, 1))))
