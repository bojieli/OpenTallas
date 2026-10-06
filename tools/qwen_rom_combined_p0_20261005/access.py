#!/usr/bin/env python3
"""Reuse real macro/backing access resolution for the additive P0 root."""
import argparse
from pathlib import Path
import re
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
    parser.add_argument('--consumer-prefix', help='Exact generated consumer hierarchy, ending __DOT__')
    parser.add_argument('--backing-member', help='Exact producer-owned public backing member from generated header')
    args, extra = parser.parse_known_args()
    header = args.die_header.read_text()
    prefix = args.consumer_prefix or TOP+'__DOT__'
    backing = args.backing_member or TOP+'__DOT__u_hbm__DOT__mem'
    if not prefix.endswith('__DOT__') or prefix+'prog_mem' not in header or backing not in header:
        raise ValueError('actual generated consumer and producer-owned backing required')
    debt = prefix+'u_kv__DOT__w_valid'
    if not re.search(r'QData/\*63:0\*/\s+'+re.escape(debt)+r'\s*;', header):
        raise ValueError('actual 64-entry service write-ACK ownership bitmap required')
    if '--kv-ideal' not in extra or extra[extra.index('--kv-ideal')+1] != '0':
        raise ValueError('P0 forbids ideal KV access generation')
    if '--hbm-layers' not in extra or extra[extra.index('--hbm-layers')+1] != '36':
        raise ValueError('full P0 access requires all36 actual backing regions')
    normalized_backing = BASE+'__DOT__u_hbm__DOT__mem'
    with tempfile.TemporaryDirectory(prefix='p0-access-') as tmp:
        normalized = Path(tmp)/'die.h'
        normalized.write_text(header.replace(backing, normalized_backing)
                              .replace(prefix, BASE+'__DOT__'))
        output = Path(tmp)/'rm_access.hpp'
        subprocess.run(['python3', str(ROOT/'tools/qwen_rom_rt_rm_access.py'),
                        '--die-header', str(normalized), '--tile-header', str(args.tile_header),
                        '--out', str(output), *extra], check=True)
        access = output.read_text().replace(normalized_backing, backing)
        access = access.replace(BASE+'__DOT__', prefix)
        access += ('\nstatic_assert(sizeof(decltype(rm_hbm_mem(static_cast<Vdie___024root*>(nullptr))))'
                   ' == size_t(36)*131072*32, "P0 requires genuine 36-layer backing; MEM1 forbidden");\n')
        access += ('\n// Read-only original service ACK owners: only identity-valid ACKs clear a bit.\n'
                   'inline uint64_t rm_write_ack_owners(const Vdie___024root* r) { return r->'
                   +debt+'; }\n')
        args.out.write_text(access)


if __name__ == '__main__':
    main()
