#!/usr/bin/env python3
"""Correct the retained rank3 final-count preload for the native I36 append.

Input is the existing 262143-key image placed at final count 262144. Move
only the six eight-key groups to their PRE-append owners. The native writer
then performs its original append/migration; no key is encoded or synthesized.
Original images and the original placer remain untouched.
"""
import argparse
import importlib.util
from pathlib import Path


def restore_preappend(stacks):
    """Raw sector relocation for the exact retained L20 rank3 boundary."""
    c = 65568
    moves = []
    for q in range(1, 4):
        for g in range(q):
            first = q * 65528 + 8 * g
            slot = first % c
            scale = 17 * (slot // 1024) * 128 + (slot % 1024) // 8
            code = (17 * (slot // 1024) + 1 + (slot % 1024) // 64) * 128 + 2 * (slot % 64)
            sectors = [scale] + list(range(code, code + 16))
            if any(stacks[q].get(a, 0) for a in sectors):
                raise ValueError('migration source is populated; not the failed final-count preload')
            if not stacks[q - 1].get(scale, 0):
                raise ValueError('missing retained eight-key scale group; refuse fabricated input')
            moves.extend((q - 1, q, a, stacks[q - 1].get(a, 0)) for a in sectors)
    for old, new, address, word in moves:
        stacks[old].pop(address, None)
        if word:
            stacks[new][address] = word
    return stacks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior-rank-dir', type=Path, required=True)
    p.add_argument('--output-rank-dir', type=Path, required=True)
    a = p.parse_args()
    if a.output_rank_dir.exists():
        raise ValueError('fresh output required; preserve historical failed input')
    placer = Path(__file__).with_name('w11_idx_ring_place.py')
    spec = importlib.util.spec_from_file_location('ring', placer)
    ring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ring)
    stacks = restore_preappend({q: ring.read_sparse(a.prior_rank_dir / f'ikring_s{q}.hex') for q in range(4)})
    a.output_rank_dir.mkdir(parents=True)
    for q, sectors in stacks.items():
        (a.output_rank_dir / f'ikring_s{q}.hex').write_text(
            ''.join(f'{address:x} {word:064x}\n' for address, word in sorted(sectors.items())))
    print('rank3 preappend count262143 restored: 48 existing keys / 102 raw sectors relocated; current key remains absent')


if __name__ == '__main__':
    main()
