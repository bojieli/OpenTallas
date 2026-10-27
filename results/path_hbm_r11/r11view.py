"""R11 render: hub nw+ne (cores, lanes, serialised cc links red, boundary) + die-level hub row after growth."""
import sys, json
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
P = json.load(open(sys.argv[1] + '/die_plan.json')); rep = json.load(open(sys.argv[1] + '/r11_delta_report.json'))
fig = plt.figure(figsize=(18, 17))
gs = fig.add_gridspec(3, 1, height_ratios=[1, 1, 1.1])
for row, tn in enumerate(("q_hub_nw", "q_hub_ne")):
    a = fig.add_subplot(gs[row]); t = P['partition_types'][tn]; W, H = t['outline_um']; r = rep['hubs'][tn]
    for h in t['hard_cores']:
        x, y = h['origin_um']; w, hh = h['outline_um']
        a.add_patch(plt.Rectangle((x, y), w, hh, fc='tab:orange' if '__q' in h['inst'] else 'tab:blue', alpha=.45, ec='k', lw=.4))
        a.text(x + w / 2, y + hh / 2, h['module'].replace('ot_', '').replace('hbm_', '')[:13], fontsize=4, ha='center')
    for s in t['internal_stations']:
        c = 'r' if s.get('r11_cc_serial') else ('m' if s.get('serial_k') else 'g')
        a.plot([s['from_um'][0], s['to_um'][0]], [s['from_um'][1], s['to_um'][1]], color=c,
               lw=.15 + min(1.2, s['bits'] / 1500), alpha=.45)
    a.axvline(r['bound_um'], color='k', ls='--')
    c = r['cut_per_sink_blocked']
    a.set_title(f"{tn} R11: S=2 y-demand boundary {r['bound_um']} um, H {r['height_um']}, k {r['k']}, cc_k {rep['cc_serial_k']} | "
                f"whole x {c['x']['max_use']} y {c['y']['max_use']} | seg (x,y) {[(s['cut_x'], s['cut_y']) for s in r['segments']]} | "
                f"green lanes/core-core, magenta inter-seg/WE serial, red cc serial x2 ({r['cc_serialised']})", fontsize=8)
    a.set_xlim(0, W); a.set_ylim(0, H); a.set_aspect('equal')
a = fig.add_subplot(gs[2]); T = P['partition_types']; D = P['die']['outline_um']
y0 = min(p['origin_um'][1] for p in P['partitions'] if p['type'] in ('q_hub_nw', 'q_hub_ne'))
for p in P['partitions']:
    w, h = T[p['type']]['outline_um']; x, y = p['origin_um']
    if y > y0 + 6000 or y + h < y0 - 2000: continue
    fc = 'tab:orange' if 'hub' in p['type'] else ('tab:purple' if p['name'] == 'root' else 'tab:cyan')
    a.add_patch(plt.Rectangle((x, y), w, h, fc=fc, alpha=.35, ec='k', lw=.5)); a.text(x + w / 2, y + h / 2, p['name'], fontsize=5, ha='center')
g = rep.get('die_growth') or {}
for gx0, gy0, gx1, gy1 in g.get('hub_row_gap_rects_um', []):
    a.add_patch(plt.Rectangle((gx0, gy0), gx1 - gx0, gy1 - gy0, fc='none', ec='r', hatch='///', lw=.6))
if g: a.axhline(g['insertion_y_um'], color='r', ls=':')
a.set_xlim(0, D[0]); a.set_ylim(y0 - 2000, y0 + 6000); a.set_aspect('equal')
a.set_title(f"die {D} after growth dH {g.get('dH_um')} at y {g.get('insertion_y_um')} (red hatch = hub-row strip above unchanged b0xx/io)", fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=100)
