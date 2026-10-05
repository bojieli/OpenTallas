#!/usr/bin/env python3
"""Reuse real macro/backing access resolution for the additive P0 root."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOP = 'ot_qwen_rom_combined_p0_20261005'
BASE = 'ot_qwen_rom_rt_die_w12_rm'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--die-header', type=Path, required=True)
    parser.add_argument('--tile-header', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args, extra = parser.parse_known_args()
    header = args.die_header.read_text()
    if TOP+'__DOT__' not in header or 'u_hbm__DOT__mem' not in header:
        raise ValueError('actual P0 root with producer-owned logical backing required')
    if '--kv-ideal' not in extra or extra[extra.index('--kv-ideal')+1] != '0':
        raise ValueError('P0 forbids ideal KV access generation')
    with tempfile.TemporaryDirectory(prefix='p0-access-') as tmp:
        normalized = Path(tmp)/'die.h'
        normalized.write_text(header.replace(TOP+'__DOT__', BASE+'__DOT__'))
        output = Path(tmp)/'rm_access.hpp'
        subprocess.run(['python3', str(ROOT/'tools/qwen_rom_rt_rm_access.py'),
                        '--die-header', str(normalized), '--tile-header', str(args.tile_header),
                        '--out', str(output), *extra], check=True)
        args.out.write_text(output.read_text().replace(BASE+'__DOT__', TOP+'__DOT__'))


if __name__ == '__main__':
    main()
