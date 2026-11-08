#!/usr/bin/env python3
"""Render the sle_fw_v3 START/reset form of plan_qc53v4x_fws: 16 writer branches, stage resets, face leaves."""
import json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plan, tree, rep, out = sys.argv[1:5]
t = json.load(open(plan))['partition_types']['sle_fw_v3']; ck = t['clock']
pins = {p['name']: p['xy_um'] for p in ck['landing_contract']['pins']}
rel = {r['q']: r for r in json.load(open(tree))['tree']['relays']}
W, H = t['outline_um']
fig, ax = plt.subplots(figsize=(6, 12)); ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1))
o = pins['cland_rstart_in']; ax.plot(*o, 'k*', ms=14, label='START source cland_rstart_in')
col = {1: 'tab:green', 2: 'tab:orange', 3: 'tab:red'}
for bus, b in sorted(ck['landing_writer_start']['branches'].items()):
    new = bus in ('cws0_o', 'x_st_a_fe_o')
    pts = [o] + [s['xy_um'] for s in b['stages']] + [pins['cland_fstart_out_' + bus]]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], '-', color='tab:blue' if new else '0.6', lw=2 if new else 0.8)
    for s in b['stages']:
        r = rel[s['raw_reset']]
        ax.plot([s['xy_um'][0], r['xy'][0]], [s['xy_um'][1], r['xy'][1]], ':', color=col[r['depth']], lw=1.2 if new else 0.5)
        ax.plot(*s['xy_um'], 'o', color=col[r['depth']], ms=5 if new else 3)
for l in ck['landing_local_resets']:
    r = rel[l['raw']]; f = pins['cland_fstart_out_' + l['consumers'][0].removeprefix('u_cland_fstart_')]
    ax.plot([r['xy'][0], l['xy_um'][0], f[0]], [r['xy'][1], l['xy_um'][1], f[1]], '--', color='tab:purple', lw=0.8)
    ax.plot(*l['xy_um'], 's', color='tab:purple', ms=4)
ax.plot(311.04, 336.96, 'kx', ms=10, label='old shared face reset u_cland_rst_cmd_ei')
ax.plot(*json.load(open(tree))['tree']['root'], 'k^', ms=10, label='rst_root_n (arst_n pin reg)')
for d, c in col.items(): ax.plot([], [], 'o:', color=c, label=f'stage reset depth {d}')
ax.plot([], [], 's--', color='tab:purple', label='face leaf (depth 4 copy)')
ax.plot([], [], '-', color='tab:blue', lw=2, label='new S branches (W=3)')
ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect('equal'); ax.legend(fontsize=6, loc='upper right')
r = json.load(open(rep))
ax.set_title(f"sle_fw_v3 v4x_fws: START hops <= {r['max_start_hop_um']} um, stage raw <= {r['max_stage_raw_flight_um']} um,\nface leaf hops <= {r['max_leaf_hop_um']} um", fontsize=8)
fig.savefig(out, dpi=110, bbox_inches='tight')
