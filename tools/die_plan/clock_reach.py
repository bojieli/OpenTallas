#!/usr/bin/env python3
"""Check actual clock cell-to-cell wires after legalisation/overlay.

This is an opt-in check of METHODOLOGY 12.1e's existing repeater reach,
not a timing sign-off or a check of the pre-legalisation topology.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sites_digest(sites):
    return hashlib.sha256(json.dumps(sites,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def freeze_sites(tree, reach_um):
    return dict(schema="opentallas.physical_clock_homes.v1", body_um=[1.62,.27],
                site_pitch_um=.054, r0_row_pitch_um=.54, reach_um=reach_um,
                frozen_sites_sha256=sites_digest(tree["sites"]))


def actual_reach(tree, max_um=450.0):
    if not math.isfinite(max_um) or max_um <= 0:
        raise ValueError('max_um must be finite and positive')
    sites = tree['sites']
    edges, missing = [], []

    def add(kind, child, parent, a, b):
        if (not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple))
                or len(a) != 2 or len(b) != 2
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                       for x in list(a) + list(b))):
            missing.append(dict(kind=kind, child=child, parent=parent))
            return
        length = abs(a[0] - b[0]) + abs(a[1] - b[1])
        edges.append(dict(kind=kind, child=child, parent=parent, length_um=round(length, 6)))

    for child, parent in tree['parent_of'].items():
        add('cell', child, parent, sites.get(child), sites.get(parent))
    buf = tree.get('node_buf', {})
    for t in tree.get('taps', []):
        driver = t.get('driver', buf.get(str(t['node']), buf.get(t['node'])))
        parity_driver = f"q{t['node']}_{t['port']}"
        if parity_driver in sites:  # final inverter restores true tap polarity after any pads
            driver = parity_driver
        add('tap', t['port'], driver, t.get('xy'), sites.get(driver))
    over = sorted((x for x in edges if x['length_um'] > max_um + 1e-6),
                  key=lambda x: (-x['length_um'], x['child']))
    result = dict(schema='ot_clk_actual_reach/1', max_um=max_um,
                  verdict='FAIL' if over or missing else 'PASS',
                  cell_edges=sum(x['kind'] == 'cell' for x in edges),
                  tap_edges=sum(x['kind'] == 'tap' for x in edges),
                  worst_um=max((x['length_um'] for x in edges), default=0.),
                  over_count=len(over), over=over, missing_sites=missing)
    frozen = (tree.get("meta") or {}).get("physical_dme")
    if frozen:
        match = frozen.get("frozen_sites_sha256") == sites_digest(sites)
        result["frozen_home_match"] = match
        if not match:
            result["verdict"] = "FAIL"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tree', help='final tree.json carrying actual sites and parent_of')
    ap.add_argument('--max-um', type=float, default=450.0)
    ap.add_argument('--json', help='new result path; existing records are never overwritten')
    a = ap.parse_args(argv)
    result = actual_reach(json.loads(Path(a.tree).read_text()), a.max_um)
    result['tree'] = a.tree
    text = json.dumps(result, indent=1) + '\n'
    if a.json:
        with open(a.json, 'x') as f:
            f.write(text)
    print(text, end='')
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
