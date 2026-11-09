import json, re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

base = Path(__file__).parent
files = sorted(base.glob('*.full.json'))
fig, axes = plt.subplots(2, 3, figsize=(15, 15), dpi=140)
summary = {}
for row, p in enumerate(files):
    d = json.loads(p.read_text())
    width, height = d['outline_um']
    attention = [x for x in d['hard_cores'] if x['module'] == 'ot_s81c_attn_hcore']
    other = [x for x in d['hard_cores'] if x['module'] != 'ot_s81c_attn_hcore']
    memories = [x for x in d['contents'] if 'origin_um' in x and 'outline_um' in x]
    summary[p.stem] = dict(outline_um=d['outline_um'], other_cores=other,
                          memory_count=len(memories), attention_count=len(attention))
    for col in range(3):
        ax = axes[row, col]
        ax.add_patch(Rectangle((0, 0), width, height, fill=False, color='black'))
        for x in memories:
            ax.add_patch(Rectangle(x['origin_um'], *x['outline_um'], facecolor='#777777', edgecolor='white', linewidth=.3))
        for x in other:
            ax.add_patch(Rectangle(x['origin_um'], *x['outline_um'], facecolor='#e89b38', edgecolor='black', linewidth=.3))
        for x in attention:
            head = int(re.search(r'g_h\[(\d+)\]', x['inst']).group(1))
            pos = x['origin_um']
            if col == 0:
                size, color = x['outline_um'], '#2977ad'
            elif head >= 8:
                ax.add_patch(Rectangle(pos, *x['outline_um'], fill=False, edgecolor='#8ab78b', linestyle=':', linewidth=.6))
                continue
            elif col == 1:
                size, color = x['outline_um'], '#27894e'
            else:
                size, color = [157.68, 371.52], '#6d54ad'
            ax.add_patch(Rectangle(pos, *size, facecolor=color, alpha=.7, edgecolor='white', linewidth=.4))
        for bus in d.get('buses', []):
            if 'window_um' not in bus: continue
            a, b = bus['window_um']; face = bus['face']
            if face in ('E', 'W'):
                xx = width if face == 'E' else 0
                ax.plot([xx, xx], [a, b], color='#b42a8d', lw=.5+min(3, bus['width']/1000))
            else:
                yy = height if face == 'N' else 0
                ax.plot([a, b], [yy, yy], color='#b42a8d', lw=.5+min(3, bus['width']/1000))
        root = d.get('clock', {}).get('tap_um')
        if root: ax.plot(*root, '*', color='#d62424', ms=11)
        ax.set_xlim(-45, width+45); ax.set_ylim(-40, height+40); ax.set_aspect('equal')
        label = ['Current 64 head macros', 'H8: existing footprint (reuse / targeted)',
                 'H8: .40 body area, fixed old width'][col]
        if col == 1: label += '\nNative RT4 fill .568 is unproven'
        if col == 2: label += '\n157.68 × 371.52, aspect 2.36; unplaced'
        ax.set_title(p.stem.split('.')[0]+'\n'+label, fontsize=9)
        ax.set_xlabel('µm'); ax.set_ylabel('µm')
fig.suptitle('SVC candidate geometry — current hard-core / memory / bus positions; no plan changes or physical release\n'
             'blue/green/purple attention; orange existing score exchange; gray SRAMs; magenta bus faces; red clock root', fontsize=11)
fig.tight_layout(rect=[0,0,1,.955])
fig.savefig(base/'attention_geometry.png')
(base/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(base/'attention_geometry.png')
