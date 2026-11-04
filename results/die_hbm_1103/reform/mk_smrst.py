#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2 (4): registered reset tree INSIDE hard partition types that are assembled from hard cores
(q_sm0..3 = 32 hnx_rp3lp3h halves each).  reset_tree.for_type refuses hard types ("hard partitions carry no generated
reset tree"), so their core rst_n pins had no relay path from the partition reset tap (die wavefront HARD_DEPTH 1 = pin
register only).  This plans the same tree reset_tree builds for soft types (core_reset_targets -> topology -> assign,
plan relay reach, blockages + walls of the type) from reset.tap_um to every core rst_n, stores it in PLAN_DIR/hard_reset_trees.json (schema has no reset key for it) and
sets reset.depth = tree depth so the die wavefront counts the cycles.  python3 mk_smrst.py PLAN_DIR TOOLS_DIE_PLAN_DIR
(edits die_plan.json in place, unlinking first; writes smrst_event.json)"""
import json, sys
from pathlib import Path
d, tools = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, tools)
import schema as S, reset_tree as RT  # noqa: E402
pp = d / 'die_plan.json'
RAW = json.loads(pp.read_text()); P = S.Plan(S.load(str(pp)), str(pp))
ev, trees = [], {}
for tn, t in sorted(P.types.items()):
    if not t.get('hard') or not t.get('hard_cores') or (RAW['partition_types'][tn].get('reset') or {}).get('depth'):
        continue
    rs = t.get('reset') or {}
    if not rs.get('tap_um'):
        continue
    _ru = RT.relay_um
    RT.relay_um = lambda P_: 1e9          # last-mile site check reported below instead of raised (rules = targets)
    try:
        cr = RT.core_reset_targets(P, tn)
    finally:
        RT.relay_um = _ru
    lim = RT.relay_um(P) - RT.MARGIN_UM
    over = [dict(inst=c['inst'], last_mile_um=round(abs(c['pin_um'][0] - c['xy'][0]) + abs(c['pin_um'][1] - c['xy'][1]), 2))
            for c in cr]
    over = [o for o in over if o['last_mile_um'] > lim]
    if not cr:
        continue
    w, h = t['outline_um']; bo = (RT.CLEAR_UM, RT.CLEAR_UM, w - RT.CLEAR_UM, h - RT.CLEAR_UM)
    pts = []
    for k, c in enumerate(cr):
        c['tap'] = len(pts); pts.append((f'core_rst{k}', *c['xy']))
    root = tuple(rs['tap_um'])
    topo = RT.topology(pts, root, reach=RT.relay_um(P), boxes=RT.blockages(t), box_out=bo, walls=RT.walls(P, tn))
    T = RT.assign(topo, None, boxes=RT.blockages(t), box_out=bo, walls=RT.walls(P, tn))
    old = rs.get('depth')
    R = RAW['partition_types'][tn].setdefault('reset', {})
    trees[tn] = dict(source='DIE-HBM-61 d44v p2: reset_tree topology+assign from reset.tap_um to every hard-core '
                          'rst_n (hard type, no generated tree)', root=list(root), depth=T['depth'],
                          max_hop_um=T['max_hop_um'], reach_um=T['reach_um'], topology=T.get('topology'),
                          relays=[dict(r, xy=list(r['xy'])) for r in T['relays']], core_resets=cr)
    R['depth'] = int(T['depth'])
    ev.append(dict(type=tn, cores=len(cr), relays=len(T['relays']), depth=T['depth'], max_hop_um=T['max_hop_um'],
                   old_depth=old, last_mile_over_reach=over))
(d / 'hard_reset_trees.json').write_text(json.dumps(dict(schema='opentallas.hbm_hard_reset_trees.v1', types=trees), indent=1) + '\n')
pp.unlink(); pp.write_text(json.dumps(RAW, indent=1) + '\n')
(d / 'smrst_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-p2-hard-type-core-reset',
                                                    types=ev), indent=1) + '\n')
print(json.dumps(ev))
