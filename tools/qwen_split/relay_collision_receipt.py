"""Failure-only provenance for the allocator's existing surviving-frame guard."""
import json
from pathlib import Path


def overlaps(a, b):
    return (b[0] < a[2] - 1e-6 and a[0] < b[2] - 1e-6 and
            b[1] < a[3] - 1e-6 and a[1] < b[3] - 1e-6)


def receipt(model, plans, index, frame_index, shave):
    plan = plans[index]
    f = plan['frames'][frame_index]
    rect = [f[0], f[1], f[0] + f[2] + shave, f[1] + f[3] + shave]
    owners = [dict(kind='instance', owner=i.name, master=i.master,
                   rect=[i.x, i.y, i.x + i.w, i.y + i.h]) for i in model['insts']]
    for ix, p in sorted(plans.items()):
        if ix > index:
            break
        for k, q in enumerate(p['frames']):
            if ix == index and k >= frame_index:
                break
            owners.append(dict(kind='relay_frame', owner=p['bid'], frame=k,
                               endpoints=p['eps'],
                               rect=[q[0], q[1], q[0] + q[2] + shave, q[1] + q[3] + shave]))
    near = [rect[0] - 1000, rect[1] - 1000, rect[2] + 1000, rect[3] + 1000]
    conflicts = [r for r in owners if overlaps(rect, r['rect'])]
    return dict(schema='opentallas.qwen.relay-collision.v1', qualified=False,
                gate='surviving_frames_before_inline_pads', die=model['die'],
                candidate=dict(owner=plan['bid'], frame=frame_index, bits=plan['bits'],
                               endpoints=plan['eps'], endpoint_pin_centers=[plan['P0'], plan['P1']], rect=rect),
                conflicting_owners=conflicts, nearby_owners=[r for r in owners if overlaps(near, r['rect'])],
                outside_die=rect[0] < 0 or rect[1] < 0 or rect[2] > model['die']['w'] or rect[3] > model['die']['h'],
                geometry_note='Exact allocator occupancy rectangles, including original SHAVE; no placement repair or gate change')


def write(path, report):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2) + '\n')


def render(report, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(10, 8))
    c = report['candidate']; r = c['rect']
    conflict = {(x['kind'], x['owner'], x.get('frame')) for x in report['conflicting_owners']}
    for owner in report['nearby_owners']:
        q = owner['rect']; bad = (owner['kind'], owner['owner'], owner.get('frame')) in conflict
        ax.add_patch(Rectangle((q[0], q[1]), q[2]-q[0], q[3]-q[1],
                               fc='#fb6a4a' if bad else '#ddd', ec='#444', alpha=.7))
        ax.text((q[0]+q[2])/2, (q[1]+q[3])/2,
                owner['owner'] + (f" [{owner['frame']}]" if 'frame' in owner else ''), fontsize=7, ha='center')
    ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc='none', ec='blue', lw=2))
    ax.text(r[0], r[3], f"{c['owner']} frame {c['frame']} ({c['bits']} bits)", color='blue')
    ax.set_xlim(r[0]-1000, r[2]+1000); ax.set_ylim(r[1]-1000, r[3]+1000)
    ax.set_aspect('equal'); ax.set_xlabel('x (um)'); ax.set_ylabel('y (um)')
    ax.set_title('Actual surviving-frame collision; allocator failure, no routing qualification')
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Render a captured actual allocator collision at true scale')
    ap.add_argument('receipt', type=Path); ap.add_argument('image', type=Path)
    args = ap.parse_args()
    render(json.loads(args.receipt.read_text()), args.image)
