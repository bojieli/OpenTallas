#!/usr/bin/env python3
"""Audit actual L0 startup images without modifying the live source or images."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(images):
    ranks = []
    for rank in range(4):
        directory = images / f'r{rank}'
        config = {key: int(value, 0) for key, value in
                  (line.split() for line in (directory / 'cfg.txt').read_text().splitlines())}
        base = config['window_region_base']
        assert config['window_region_count'] == 128 * 17
        start = base + (config['pos'] % 128) * 17
        current = set(range(start, start + 17))
        prior_path = directory / 'hbm0_without_current_row.hex'
        full_path = directory / 'hbm0_with_current_row.hex'
        prior = [int(word, 16) for word in prior_path.read_text().split()]
        full = [int(word, 16) for word in full_path.read_text().split()]
        assert len(prior) == len(full) == base + 128 * 17
        assert all(prior[address] == 0 for address in current), 'current row injected'
        changed = [address for address, (a, b) in enumerate(zip(prior, full)) if a != b]
        assert changed and set(changed) <= current, 'fixture difference outside current row'
        pins = {name: sha(directory / name) for name in
                ['cfg.txt', 'hbm0_without_current_row.hex', 'hbm0_with_current_row.hex', 'vm_init.hex']}
        sparse_counts = []
        for stack in range(4):
            name = f'hbmsparse{stack}.hex'
            entries = [line.split() for line in (directory / name).read_text().splitlines() if line.strip()]
            addresses = [int(entry[0], 16) for entry in entries]
            assert len(set(addresses)) == len(addresses), 'duplicate sparse address'
            if stack == 0:
                assert not current.intersection(addresses), 'sparse input overwrites current row'
            pins[name] = sha(directory / name)
            sparse_counts.append(len(entries))
        ranks.append(dict(rank=rank, position=config['pos'], current_sector_start=start,
                          current_sector_count=17, zero_current_sectors=17,
                          differences_only_current_row=changed, sparse_entries=sparse_counts,
                          input_sha256=pins))
    return dict(schema='opentallas.w17.current_kv_fixture_audit.v1',
                verdict='PASS_L0_PRIOR_CONTEXT_ONLY_CURRENT_ROW_ABSENT',
                scope='L0 startup fixture audit only; no RTL writer, layer, full-token or physical PASS',
                images=str(images), ranks=ranks, adopt=False,
                full_token_requirement='Carry RTL-produced activations and KV through all layers; do not reinitialize from per-layer golden state.',
                source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                               [Path(__file__), ROOT / 'tools/v41_die_l0_images.py',
                                ROOT / 'tools/w17_current_L0_supervisor_v2.py']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = audit(args.images)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
