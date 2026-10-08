#!/usr/bin/env python3
"""Count physical-intent capture copies in a Yosys generic hierarchy.

This is a structural gate, not mapped-cell or extracted timing qualification.
The caller supplies a post-proc/flatten/opt/memory_map/opt JSON netlist.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def census(netlist, top):
    modules = netlist['modules']
    root = modules[top]
    counts = collections.Counter()

    def walk(name):
        for cell in modules[name]['cells'].values():
            kind = cell['type']
            if kind in modules:
                walk(kind)
            elif kind in ('$dff', '$adff', '$dffe', '$adffe'):
                polarity = cell['parameters']['CLK_POLARITY']
                polarity = int(polarity, 2) if isinstance(polarity, str) else polarity
                counts['posedge' if polarity else 'negedge'] += len(cell['connections']['Q'])

    walk(top)
    instances = collections.Counter(c['type'] for c in root['cells'].values())
    data_copies = instances['ot_window_capture128']
    enable_copies = instances['ot_window_capture4']
    if data_copies or enable_copies:
        data_bits = data_copies * 128
        enable_bits = enable_copies * 4
    else:
        data_bits = len({b for n, v in root['netnames'].items() if n.endswith('.wd') for b in v['bits']})
        enable_bits = len({b for n, v in root['netnames'].items() if n.endswith('.we') for b in v['bits']})
    expected = dict(data_capture_bits=1024, enable_capture_bits=256,
                    posedge_bits=1923, negedge_bits=4096)
    observed = dict(data_capture_bits=data_bits, enable_capture_bits=enable_bits,
                    posedge_bits=counts['posedge'], negedge_bits=counts['negedge'])
    return dict(status='PASS' if expected == observed else 'FAIL',
                expected=expected, observed=observed,
                capture_leaf_instances=dict(data128=data_copies, enable4=enable_copies),
                adopted=False, scope='generic synthesis only; mapped cells, clocks, SS/FF and placement pending')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--netlist', type=Path, required=True)
    p.add_argument('--top', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = census(json.loads(a.netlist.read_text()), a.top)
    result['netlist_sha256'] = hashlib.sha256(a.netlist.read_bytes()).hexdigest()
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.out.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps(result))
    return result['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
