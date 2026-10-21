#!/usr/bin/env python3
"""Compose the selected r14 source before synthesising pin views or planning relays.

The h9c controller is selected before S3/S4, so the initial views, clock/reset
inventory and later contracts share that source. This source composition does
not confer native-view, strict-bind, GEN, routing, timing or IR qualification.
Run from the repository root; outputs go to a fresh directory.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

LAYERS = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compose(inp, out):
    # Pin the already selected GEN2e4 starting vehicle; do not silently port a
    # different contract through layers with different clock/port assumptions.
    if not sha(inp).startswith('9d1a3f20'):
        raise ValueError('r14 release requires the selected GEN2e4 pre_relay basis')
    out.mkdir(parents=True, exist_ok=False)
    steps = (
        ('l23_su_pretree.py', inp, out / 'pre_relay_l23.json'),
        ('l23q_qcore_r13.py', out / 'pre_relay_l23.json', out / 'pre_relay_l23q.json'),
        ('l25_h9c_fallback.py', out / 'pre_relay_l23q.json', out / 'pre_relay_release.json'),
    )
    for tool, src, dst in steps:
        args = [sys.executable, str(LAYERS / tool)]
        if tool.startswith('l25_'):
            args.append('swap')
        subprocess.run(args + [str(src), str(dst), '--report', str(out / (tool[:-3] + '.json'))], check=True)
    c = json.loads((out / 'pre_relay_release.json').read_text())
    source_paths = sorted({p for i in c['instances'].values()
                           for p in ([i.get('source')] + list(i.get('rtl_deps') or [])) if p})
    missing = [p for p in source_paths if not Path(p).is_file()]
    inventory = dict(schema='opentallas.hbm_release_source_inventory.v1',
                     contract_sha256=sha(out / 'pre_relay_release.json'),
                     input_sha256=sha(inp), source_complete=not missing,
                     source_sha256={p: sha(p) for p in source_paths if Path(p).is_file()},
                     missing_sources=missing,
                     instance_count=len(c['instances']), edge_count=len(c['edges']),
                     h9c_instances=[n for n, i in c['instances'].items()
                                    if i['master'] == 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b'],
                     clock_reset_rows=c.get('clock_resets'),
                     qualification='SOURCE_COMPOSITION_ONLY',
                     physical_qualification_eligible=False,
                     outstanding=['exact closed native views for every composed master and parameters',
                                  'source-bound strict unread manifest for the final contract and die',
                                  'actual clock/reset, ordered relay/tail, channel/cell and C1/C2/W1/W2 facts',
                                  'M8 signal and repeater RC, actual GRT, TT/FF STA, actual ODB IR'])
    (out / 'source_inventory.json').write_text(json.dumps(inventory, indent=1) + '\n')
    if len(inventory['h9c_instances']) != 64:
        raise ValueError('expected exactly 64 selected h9c controllers')
    if missing:
        raise ValueError(f'source inventory incomplete: {len(missing)} files; see source_inventory.json')
    print('R14_RELEASE_SOURCE PASS (source composition only)', inventory['contract_sha256'])
    return inventory


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output_dir', type=Path)
    a = p.parse_args()
    compose(a.input, a.output_dir)
