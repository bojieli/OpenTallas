from pathlib import Path
import json
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-core-union-1131/tools/die_plan')
import schema as S
import die_trial as DT
r = Path('/home/ubuntu/coord/tmp/codex-hbm-clock')
plan = S.Plan(S.load(r / 'current_C11E_plan.json'))
site_map = DT.SiteMap(plan)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
records = {}
for axis, side in zip(axes, ['NW', 'NE']):
    pilot = json.loads((r / 'halo_regen' / f'{side}.json').read_text())
    geometry = pilot['geom']
    ox, oy = geometry['origin']
    bad = []
    for core in geometry['cores']:
        x, y, xx, yy = core['rect']
        axis.add_patch(Rectangle((x, y), xx - x, yy - y, color='salmon', alpha=.35))
    for name, cell in pilot['cells'].items():
        driver = name in geometry['drivers']
        axis.scatter(cell['x'], cell['y'], s=7 if driver else 2,
                     color='royalblue' if driver else 'black')
        corners = [(ox + cell['x'] + dx, oy + cell['y'] + dy)
                   for dx, dy in [(0,0),(1.62,0),(0,.27),(1.62,.27)]]
        if not all(site_map.legal(point) for point in corners):
            bad.append(name)
    for x in geometry['vx']:
        axis.axvline(x, color='blue', lw=.3, alpha=.3)
    for y in geometry['hy']:
        axis.axhline(y, color='blue', lw=.3, alpha=.3)
    axis.set_xlim(0, geometry['W'])
    axis.set_ylim(0, geometry['H'])
    axis.set_aspect('equal')
    axis.set_title(f"{side}: physical-core union, 600 um siting search\n"
                   f"{len(pilot['cells'])} cells / 256 drivers; whole-body SiteMap 2.16 failures {len(bad)}")
    records[side] = dict(cells=len(pilot['cells']), drivers=len(geometry['drivers']),
                         SiteMap_2_16_fullbody_failures=bad)
fig.suptitle('Current C11E geometry prototype, 360 um repeater planning target. Not routed.\n'
             'Existing hub tap census only; current 14+6+ROOT/native endpoint event remains held.', fontsize=10)
fig.tight_layout()
fig.savefig(r / 'halo_regen_review.png', dpi=140)
(r / 'halo_regen_body.json').write_text(json.dumps(records, indent=2))
print(json.dumps(records))
