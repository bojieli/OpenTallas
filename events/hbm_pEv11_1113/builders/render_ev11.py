"""DIE-HBM-102 pEv11 delta renders: before (pEv10) / after per changed type.  usage: render_ev11.py BEFORE AFTER OUTDIR"""
import json, sys, os, site
sys.path.append(site.getusersitepackages())
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
A, B, O = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]; os.makedirs(O, exist_ok=True)
col = {'L51_i': 'tab:red', 'L52_o': 'tab:blue', 'L101_i': 'tab:green', 'L126_o': 'tab:purple'}
def frame(ax, t, win):
    W, H = t['outline_um']; ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for h in t['hard_cores']:
        (x, y), (w, hh) = h['origin_um'], h['outline_um']
        ax.add_patch(plt.Rectangle((x, y), w, hh, color='0.85', ec='0.5'))
        if win[0] - w < x < win[1] and win[2] - hh < y < win[3]: ax.text(x + 3, y + hh / 2, h['inst'][-22:], fontsize=6)
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect('equal')
def io(ax, t, ttl):
    frame(ax, t, (-20, 668, 580, 1830))
    for s in t['internal_stations']:
        c = s['conn'][4:] if s['conn'].startswith('bus:') else None
        p = [s['from_um'][:2]] + [q[:2] for q in s['regs_um']] + [s['to_um'][:2]]
        xs, ys = zip(*p); big = (s.get('bits') or 0) >= 600
        ax.plot(xs, ys, '-o', color=col.get(c, '0.6'), lw=2.2 if big else 0.6, ms=4 if big else 2, label=(c + (' 612b' if big else ' slices')) if c else None)
    ax.add_patch(plt.Rectangle((118, 1088), 529, 224, fill=False, ec='orange', lw=2, ls='--'))
    hd, lb = ax.get_legend_handles_labels(); u = dict(zip(lb, hd)); ax.legend(u.values(), u.keys(), fontsize=7, loc='lower left'); ax.set_title(ttl, fontsize=9)
def slots(ax, t, names, win, ttl, rows):
    frame(ax, t, win)
    for i, s in enumerate([s for s in t['ft_slots'] if s['name'] in names]):
        xs, ys = zip(*[r[:2] for r in s['regs_um']]); ax.plot(xs, ys, '-o', lw=2, ms=4, label=f"{s['name']} ({s['width']}b)", color=['tab:red', 'tab:blue', 'tab:green'][i])
    for y, lab in rows: ax.axhline(y, color='orange', ls='--', lw=1); ax.text(win[0] + 5, y + 2, lab, fontsize=7, color='orange')
    ax.legend(fontsize=7, loc='lower left'); ax.set_title(ttl, fontsize=9)
f, ax = plt.subplots(1, 2, figsize=(13, 12))
io(ax[0], A['partition_types']['NW_io'], 'NW_io pEv10 (orange = a30 GRT-0232 hotspot x 118-647 y 1088-1312)'); io(ax[1], B['partition_types']['NW_io'], 'NW_io pEv11 (612b W-pin chains up the E channel, over the ep top; slices on own sites)')
plt.tight_layout(); plt.savefig(f'{O}/nwio_before_after.png', dpi=100); plt.close()
oy = [q for q in A['partitions'] if q['name'] == 'NW_b113'][0]['origin_um'][1]
f, ax = plt.subplots(2, 1, figsize=(14, 9))
rows = [(12019.2 - oy, 'die row 12019.2 (M6 1.181)'), (11971.2 - oy, 'die row 11971.2 (M6 1.054)'), (12048.0 - oy, 'die row 12048.0')]
for a, P, nm in ((ax[0], A, 'pEv10'), (ax[1], B, 'pEv11')):
    slots(a, P['partition_types']['q_b113'], ('L8350x3', 'L1271x7'), (0, 1860, 1250, 1600), f'q_b113 (NW_b113) top strip {nm}', rows)
plt.tight_layout(); plt.savefig(f'{O}/b113_rows_before_after.png', dpi=100); plt.close()
oy = [q for q in A['partitions'] if q['name'] == 'NW_hub'][0]['origin_um'][1]
f, ax = plt.subplots(2, 1, figsize=(14, 8))
rows = [(10416.0 - oy, 'die row 10416.0 (M8 1.025)'), (10348.8 - oy, 'die row 10348.8 (empty)')]
for a, P, nm in ((ax[0], A, 'pEv10'), (ax[1], B, 'pEv11')):
    slots(a, P['partition_types']['q_hub_nw'], ('L1219x1',), (4500, 6300, 3850, 4340), f'q_hub_nw (NW_hub) L1219x1 turnaround {nm}', rows)
plt.tight_layout(); plt.savefig(f'{O}/hub_l1219_before_after.png', dpi=100); plt.close()
print('ok')
