#!/usr/bin/env python3
"""Count actual mapped TT sequential cells; depth banks are not logic halves."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('netlist', type=Path)
    a = ap.parse_args()
    raw = a.netlist.read_bytes()
    cells = []
    for m in re.finditer(r'^\s*(\S*(?:DFF|SDFF)\S*)\s+([^\s(]+)\s*\(', raw.decode(), re.M):
        cells.append((m[1], m[2].lstrip('\\')))
    grouped = collections.Counter()
    depth = collections.Counter()
    for _, name in cells:
        bits = name.split('.')
        prefix = '.'.join(bits[:3]) if len(bits) > 3 else '.'.join(bits[:-1]) or 'tree_boundary'
        grouped[prefix] += 1
        bank = re.search(r'(.*(?:u_tag|u_pretag)\.g_mem\.g_b\[\d+\])', name)
        if bank:
            depth[bank[1]] += 1
    print(json.dumps({'schema': 'opentallas.tt_mapped_census.v1',
      'netlist': str(a.netlist), 'netlist_sha256': hashlib.sha256(raw).hexdigest(),
      'mapped_ff_total': len(cells), 'groups': dict(grouped.most_common()),
      'sram_depth_bank_capture_ffs': dict(depth),
      'qualification': 'mapped inventory only; no native/physical qualification',
      'finding': 'Depth-bank captures do not divide the issue/control/scale/result FFs.'}, indent=2))


if __name__ == '__main__':
    main()
