"""Audit kept local landing selectors and per-chunk validity after Yosys synthesis."""
import argparse
from collections import Counter
import json
from pathlib import Path


def check(path):
    modules = json.loads(Path(path).read_text())['modules']
    report = {}
    for name, module in modules.items():
        if 'ot_pl_land_local_' in name:
            loads = Counter()
            for cell in module.get('cells', {}).values():
                for port, bits in cell['connections'].items():
                    if cell.get('port_directions', {}).get(port) == 'input':
                        loads.update(bit for bit in bits if isinstance(bit, int))
            targets = {net: max([loads[bit] for bit in value['bits'] if isinstance(bit, int)] or [0])
                       for net, value in module['netnames'].items()
                       if net in ('read_oh', 'write_oh', 'valid', 'vld', 'warm', 'rq')}
            assert any(net in targets for net in ('read_oh', 'write_oh')), (name, 'selectors disappeared')
            assert max(targets.values()) <= 32, (name, targets)
            report[name] = dict(target_max_loads=targets, cells=len(module['cells']))
        roles = {}
        for suffix in ('_w', '_r'):
            locals_ = [cell for cell in module.get('cells', {}).values()
                       if 'ot_pl_land_local' + suffix in cell['type']]
            if not locals_:
                continue
            # Wrappers flatten, so inspect the actual surviving local instances
            # in their parent rather than relying on wrapper module names.
            bits = [bit for cell in locals_ for bit in cell['connections']['vld']]
            assert len(set(bits)) == len(bits), (name, suffix, 'shared physical validity bits')
            roles[suffix] = set(bits)
            report.setdefault(name, {})['writer' if suffix == '_w' else 'reader'] = dict(
                chunks=len(locals_), physical_valid_bits=len(bits))
        if set(roles) == {'_w', '_r'}:
            assert roles['_w'] == roles['_r'], (name, 'missing chunk validity')
    assert report, 'no safe landing modules found'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist')
    parser.add_argument('--output')
    args = parser.parse_args()
    report = check(args.netlist)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
