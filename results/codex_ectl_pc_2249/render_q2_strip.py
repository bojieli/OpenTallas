from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

fig, ax = plt.subplots(figsize=(10, 7))
ax.add_patch(Rectangle((0, 0), 243.648, 172.8, fill=False, color='black'))
for x in [15.12, 133.488]:
    for y in [13.26, 127.404]:
        ax.add_patch(Rectangle((x, y), 94.824, 41.064, color='#c8c8c8', hatch='//', alpha=.65))
for tag, xs, ends in [('L', (15.12, 109.944), (11.34, 113.4)), ('R', (133.488, 228.312), (129.168, 230.472))]:
    ax.add_patch(Rectangle((xs[0], 4.32), xs[1]-xs[0], 13.26-4.32, color='#d9edf7', alpha=.7))
    for i, x in enumerate(ends):
        side = 'W' if i == 0 else 'E'
        ax.scatter([x, x], [57.24, 9.45], marker='s', color='#c12a2a', s=65)
        ax.annotate('', (x, 9.45), (x, 57.24), arrowprops=dict(arrowstyle='->', color='#c12a2a'))
        ax.text(x, 61, f'{tag}{side}', ha='center', fontsize=9)
        end = (xs[0]+xs[1])/2
        leafx = .75*x + .25*end
        ax.annotate('', (leafx, 7.97), (x, 9.45), arrowprops=dict(arrowstyle='->', color='#c12a2a'))
        ax.scatter([leafx], [7.97], marker='o', color='#204b71', s=20)
ax.scatter([62.96, 68.04], [7.97, 99.77], marker='o', color='#204b71', s=35)
ax.scatter([61.128, 64.476], [4.995, 104.085], marker='x', color='black', s=50)
ax.text(63, 18, 'measured failing leaf\nparent above macro', fontsize=9, ha='center')
ax.annotate('removed macro-crossing clock leg', (62.96, 7.97), (67, 69), color='#555555', fontsize=8,
            arrowprops=dict(arrowstyle='->', color='#777777', linestyle='--'))
ax.text(120, 88, 'clock parent candidates stay in the central corridor\nnearest equal-depth net chosen by geometry', fontsize=9, ha='center')
ax.set(xlim=(-5, 249), ylim=(-5, 178), aspect='equal', xlabel='x (um)', ylabel='y (um)')
ax.set_title('Q2 planned macro-shadow strip feeds: 8 BUFx24, unchanged depth\nNo pads, trims, timing-based parent choices, outline or pin change')
fig.tight_layout()
fig.savefig('/home/ubuntu/coord/tmp/ectl-pc-2249/q2_strip_plan.png', dpi=140)
