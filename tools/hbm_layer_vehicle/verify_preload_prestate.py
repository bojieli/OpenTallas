#!/usr/bin/env python3
"""Check additive Qwen preload corrections against immutable NPZ pre-state words.

No model execution or RTL simulation. Commands, checks, cycles, expected outputs,
and preload address inventories must match the preserved original packet.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def verify(original, corrected, operands):
    result = {}
    for stage in ('L0', 'chain'):
        operand = operands / f'operands_{stage}.npz'
        with np.load(operand) as snapshots:
            for rank in (0, 5):
                old = original / stage / f'r{rank}'
                new = corrected / stage / f'r{rank}'
                manifest = json.loads((new / 'manifest.json').read_text())
                records = {r['i']: r for r in manifest['records']}
                checked = changed = padding = 0
                images = list(new.glob('images/r*_su/record.json'))
                assert images, (stage, rank, 'no emitted images')
                for path in images:
                    index = int(path.parent.name[1:-3])
                    data = json.loads(path.read_text())
                    prior = json.loads((old / 'images' / path.parent.name / 'record.json').read_text())
                    assert data['expect'] == prior['expect'], ('expected outputs changed', path)
                    assert data['preload'] == prior['preload'], ('input address inventory changed', path)
                    assert data['data'].keys() == prior['data'].keys(), ('input words omitted', path)
                    snap = snapshots[f'pre_r{rank}_j{records[index]["j"]}']
                    actual = dict(zip(map(int, snap[0]), map(int, snap[1])))
                    for address, bits in data['data'].items():
                        address = int(address)
                        expected = actual.get(address, 0)
                        padding += address not in actual
                        assert int(bits, 16) == expected, (path, address, bits, expected)
                        checked += 1
                        changed += bits != prior['data'][str(address)]
                old_replay = json.loads((old / 'replay.json').read_text())
                new_replay = json.loads((new / 'replay.json').read_text())
                assert [e for e in old_replay['events'] if e['k'] != 'M'] == [e for e in new_replay['events'] if e['k'] != 'M'], ('commands/checks/cycles changed', stage, rank)
                result[f'{stage}_r{rank}'] = dict(checked_preload_words=checked,
                    corrected_words=changed, inactive_sector_padding_words=padding,
                    prestate_mismatches=0, commands_checks_cycles_unchanged=True,
                    original_replay_sha256=hashlib.sha256((old / 'replay.json').read_bytes()).hexdigest(),
                    corrected_replay_sha256=hashlib.sha256((new / 'replay.json').read_bytes()).hexdigest(),
                    operand_sha256=hashlib.sha256(operand.read_bytes()).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--corrected', type=Path, required=True)
    parser.add_argument('--operands', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = verify(args.original, args.corrected, args.operands)
    text = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
