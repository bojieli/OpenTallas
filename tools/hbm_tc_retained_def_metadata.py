#!/usr/bin/env python3
"""Bounded read-only text DEF extraction; never loads a physical checkpoint.

Coordinates remain integer DEF DBU. Raw special-net/via records retain their
geometry without assuming that route occupancy is spare channel capacity.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 320_000_000
MAX_RECORD_BYTES = 8_000_000
MAX_COMPONENTS = 500_000
SECTIONS = {'COMPONENTS', 'PINS', 'VIAS', 'SPECIALNETS', 'NETS'}


def classify(name):
    n = name.lower()
    if n.startswith('filler'): return 'filler_named'
    if 'clkbuf' in n or 'clkload' in n: return 'CTS_named'
    if 'hold' in n: return 'hold_named'
    if 'g_lane' in n: return 'lane_named'
    return 'other'


def extract(path):
    path = Path(path)
    if path.suffix != '.def': raise ValueError('only textual .def accepted')
    before = path.stat()
    if before.st_size > MAX_BYTES: raise ValueError('file budget exceeded')
    out = dict(path=str(path), stat=dict(bytes=before.st_size, mtime_ns=before.st_mtime_ns),
               header=[], components=[], pins=[], vias=[], specialnets=[], selected_nets=[],
               component_columns=['name', 'master', 'x_dbu', 'y_dbu', 'orient', 'status'],
               declared_counts={}, parsed_counts={}, category_counts={}, route_token_counts={})
    section = None
    buf = []
    size = 0
    counts = Counter()
    categories = Counter()
    route = Counter()
    sha = hashlib.sha256()
    def record(s, sec):
        counts[sec] += 1
        if sec == 'COMPONENTS':
            m = re.match(r'-\s+(\S+)\s+(\S+)', s)
            p = re.search(r'\+\s+(PLACED|FIXED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', s)
            if not m or not p: raise ValueError('unplaced/unparsed component')
            out['components'].append([m[1], m[2], int(p[2]), int(p[3]), p[4], p[1]])
            categories[classify(m[1])] += 1
            if counts[sec] > MAX_COMPONENTS: raise ValueError('component budget exceeded')
        elif sec == 'PINS': out['pins'].append(s)
        elif sec == 'VIAS': out['vias'].append(s)
        elif sec == 'SPECIALNETS': out['specialnets'].append(s)
        elif sec == 'NETS':
            name = re.match(r'-\s+(\S+)', s)[1]
            # Actual connection lists and route tokens for clocks/control and
            # named stage-one exponent/tree bypass endpoints. No cone inference.
            connections = s.split('+ ROUTED', 1)[0]
            if re.search(r'clk|v_q|v_ql|s1_e|bypass_code', connections):
                out['selected_nets'].append(s)
            for layer in re.findall(r'(?:ROUTED|NEW)\s+(M\d+)', s): route[layer] += 1
    with path.open('rb') as f:
        for raw in f:
            sha.update(raw)
            line = raw.decode('utf-8').strip()
            if not buf:
                m = re.fullmatch(r'(\w+)\s+(\d+)\s*;', line)
                if m and m[1] in SECTIONS:
                    section = m[1]; out['declared_counts'][section] = int(m[2]); continue
                if line.startswith('END '): section = None; continue
                if section is None:
                    if line.startswith(('DESIGN ', 'UNITS ', 'DIEAREA ', 'ROW ', 'TRACKS ')): out['header'].append(line)
                    continue
            buf.append(line); size += len(raw)
            if size > MAX_RECORD_BYTES: raise ValueError('record budget exceeded')
            if line.endswith(';'):
                record(' '.join(buf), section); buf = []; size = 0
    if buf: raise ValueError('unterminated record')
    for sec, n in out['declared_counts'].items():
        if counts[sec] != n: raise ValueError('section count mismatch: '+sec)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('source changed during extraction')
    out.update(sha256=sha.hexdigest(), stable_read=True, parsed_counts=dict(counts),
               category_counts=dict(categories), route_token_counts=dict(route),
               route_count_meaning='ROUTED/NEW layer-token census; not occupied tracks or spare capacity')
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('def_path')
    p.add_argument('--gzip-stdout', action='store_true')
    args = p.parse_args()
    data = json.dumps(extract(args.def_path), sort_keys=True, separators=(',', ':')).encode()
    if args.gzip_stdout: sys.stdout.buffer.write(gzip.compress(data, mtime=0))
    else: print(data.decode())


if __name__ == '__main__': main()
