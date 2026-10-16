#!/usr/bin/env python3
"""Draw emitted DEF placement and generated port-to-port register flights, never GRT wires."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'budgets'))
from common import port_xy


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--placement', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    model = json.loads(gzip.decompress(a.model.read_bytes()))
    placed = json.loads(a.placement.read_text())
    by = {row[0]: list(row) for row in model['insts']}
    orientations = {'N': 'R0', 'FN': 'MY', 'FS': 'MX', 'S': 'R180'}
    changed, unmatched = 0, []
    for name, row in by.items():
        p = placed['placed'].get(name)
        if p is None or p[0] != row[1]:
            unmatched.append(name)
            continue
        orient = orientations.get(p[3], p[3])
        changed += (row[5:7] != p[1:3] or row[9] != orient)
        row[5:7], row[9] = p[1:3], orient
    # Show every generated hub/service bus, including low-width controls.
    buses = [b for b in model['buses'] if b[1] in ('hub', 'hbm_read', 'hbm_req')]
    missing, segments, wide = [], [], []
    for bus in buses:
        endpoints = []
        for inst, port, *_ in bus[3]:
            if inst not in by:
                missing.append([bus[0], inst, port, 'no_instance'])
                continue
            xy, known = port_xy(model, by[inst], port)
            if not known:
                missing.append([bus[0], inst, port, 'box_anchor'])
            endpoints.append(xy)
        for sink in endpoints[1:]:
            segment = [(v[0] / 1000, v[1] / 1000) for v in (endpoints[0], sink)]
            (wide if bus[2] >= 500 else segments).append(segment)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection, LineCollection
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 2, figsize=(16, 10), gridspec_kw={'width_ratios': [1.3, 1]})
    for ax in axes:
        boxes, labels = [], []
        for row in by.values():
            name, master, kind, _, _, x, y, w, h, orient = row
            if kind in ('stn', 'hstn', 'hend', 'xstg', 'lkck'):
                continue
            boxes.append(Rectangle((x / 1000, y / 1000), w / 1000, h / 1000))
            if name.startswith('sp_') or name in ('mix4', 'bk_selector', 'bk_collector'):
                labels.append((name, x, y, w, h))
        ax.add_collection(PatchCollection(boxes, facecolor='#e5e7eb', edgecolor='#64748b', linewidth=.18, alpha=.8))
        ax.add_collection(LineCollection(segments, colors='#527ea8', linewidths=.25, alpha=.18))
        ax.add_collection(LineCollection(wide, colors='#c03a32', linewidths=.7, alpha=.40))
        for name, x, y, w, h in labels:
            ax.add_patch(Rectangle((x / 1000, y / 1000), w / 1000, h / 1000, fill=False, ec='#111827', lw=.8))
            ax.text((x + w / 2) / 1000, (y + h / 2) / 1000, name.replace('sp_', ''), fontsize=6,
                    ha='center', va='center', rotation=90 if h > 3 * w else 0,
                    bbox=dict(fc='white', ec='none', alpha=.7, pad=.7))
        ax.set_aspect('equal'); ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')
        ax.set_ylim(0, 26)
    axes[0].set_xlim(0, 33); axes[0].set_title('c26b_r actual placed DEF, full 33 x 26 mm')
    axes[1].set_xlim(9.4, 22.4); axes[1].set_title('Same actual placement, hub detail')
    fig.suptitle('Generated register-flight overlay: red >=500 bits; blue smaller hub/control buses\n'
                 'Straight flight lines are connectivity diagnostics, not global or detailed routes.', fontsize=11)
    fig.text(.02, .02, f"{len(buses)} bus records; {len(wide) + len(segments)} flight segments; "
             f"{len(missing)} endpoints use missing/box anchors. RTL directions unqualified (extract real_blocks failed).", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, .94)); a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=140); plt.close(fig)
    receipt = dict(scope='ACTUAL_PLACEMENT_GENERATED_PORT_FLIGHTS_NOT_ROUTED_NOT_NATIVE',
                   model_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),
                   placement_sha256=hashlib.sha256(a.placement.read_bytes()).hexdigest(),
                   placement_source=placed['source'], model_instances=len(by), placed_components=placed['components'],
                   snapped_instances=changed, unmatched_instances=unmatched, selected_buses=len(buses),
                   segments=len(wide) + len(segments), endpoint_anchor_gaps=missing,
                   real_master_direction_coverage=len(model.get('real_masters', [])),
                   direction_failures=model.get('endpoint_dir_failures'))
    a.out.with_suffix('.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('endpoint_anchor_gaps', 'unmatched_instances')}))


if __name__ == '__main__':
    main()
