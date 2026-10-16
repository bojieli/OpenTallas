"""Render the generated candidate coordinates, never routed metal."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
rep = json.loads((root / 'physical/s81_die_pins/candidate_mix4_vm_joint_1016/candidate_receipt.json').read_text())
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 10), gridspec_kw={'width_ratios': [1, 1.6]})
colors = ['#237da8', '#a76d19', '#518b39', '#954e95']
for band, color in zip(rep['bands'], colors):
    lo, hi = band['first_local_y_um'], band['last_local_y_um']
    for x in (0, 21.624):
        a.plot([x, x], [lo, hi], lw=3, color=color)
    a.text(40, (lo + hi) / 2, 'physical group ' + str(band['physical_VM_group']), fontsize=9)
lo = rep['bands'][0]['first_local_y_um']
for i in range(32):
    y = lo + .240 * i
    b.plot([0, 21.624], [y, y], c=colors[0], alpha=.65, lw=1)
    b.scatter([0, 21.624], [y, y], c=colors[0], s=8)
a.set_ylim(0, 3652.56)
a.set_xlim(-15, 380)
a.set_aspect('equal')
a.set_xticks([])
a.set_title('Four physical VM lane bands\n3183 bits each; 12732 paired pins')
b.set_ylim(lo - .2, lo + 7.7)
b.set_xlim(-1, 22.624)
b.set_aspect('equal')
b.set_title('First 32 candidate wires: 0.240 um pitch\nMIX4 E to VM W, post-shave gap 21.624 um')
for ax in (a, b):
    ax.set_ylabel('MIX4 local y (um)')
    ax.grid(alpha=.2)
b.set_xlabel('Facing edge distance (um)')
fig.suptitle('CANDIDATE: source-bound MIX4 / VM joint face assignment\nNo routing, clock, native or cut qualification; current GEN unchanged', fontsize=13)
fig.text(.06, .025, 'M4 horizontal tracks: offset 0.012 um, pitch 0.048 um; five-track pin spacing. Existing VM capture pins unchanged.\nBands are physical VM lanes, not isolated compute copies: H transpose and V broadcasts still require full parent routing.\nClock/reset/status/command roles, native child register placement, internal cuts/PG and actual pipeline stages remain open.', fontsize=10)
fig.tight_layout(rect=[0, .11, 1, .92])
fig.savefig(out / 'joint_face_candidate.png', dpi=160)
