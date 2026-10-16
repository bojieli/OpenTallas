#!/usr/bin/env python3
"""Necessary geometry screen of the actual eight-bank P.V column.

Uses routed slice pins and assigned join pins, preserving every bit identity.
This is a Manhattan lower bound, not an obstacle route or physical adoption.
"""
import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
from child_lint import parse_lef


def point(p, orient, width):
    x, y = p
    return ((width-x if orient in ('MY', 'R180') else x),
            (width-y if orient in ('MX', 'R180') else y))


def screen(slice_path, join_path, gap):
    width = 172.8
    sm = parse_lef(slice_path.read_text())
    sp = {}
    for i in range(512):
        r = sm['pins'][f'ts[{i}]']['rects'][0]
        sp[i] = ((r[1]+r[3])/2, (r[2]+r[4])/2)
    jp = {}
    for n, x, y in re.findall(r'place_pin -pin_name \{([^}]+)\}.*?-location \{([\d.-]+) ([\d.-]+)\}', join_path.read_text()):
        jp[n] = (float(x)+width+gap, float(y)+width+gap)
    sites = [(x, y) for y in range(3) for x in range(3) if (x, y) != (1, 1)]
    costs = {}
    for bank in range(8):
        for pos, (gx, gy) in enumerate(sites):
            options = []
            for orient in ('R0', 'MX', 'MY', 'R180'):
                lengths = []
                for i in range(512):
                    x, y = point(sp[i], orient, width)
                    x += gx*(width+gap)
                    y += gy*(width+gap)
                    tx, ty = jp[f'ts{bank//2}[{512*(bank%2)+i}]']
                    lengths.append(abs(x-tx)+abs(y-ty))
                options.append((max(lengths), sum(lengths)/512, orient))
            costs[bank, pos] = min(options)
    def score(order):
        c = [costs[b, p] for b, p in enumerate(order)]
        return max(x[0] for x in c), sum(x[1] for x in c)
    order = min(itertools.permutations(range(8)), key=score)
    banks = []
    for b, p in enumerate(order):
        gx, gy = sites[p]
        mx, mean, orient = costs[b, p]
        banks.append(dict(bank=b, x=gx*(width+gap), y=gy*(width+gap),
                          orient=orient, width=width, height=width,
                          join_bus=f'ts{b//2}', join_offset=512*(b%2),
                          worst_pin_manhattan_um=mx, mean_pin_manhattan_um=mean))
    return dict(gap_um=gap, block_outline_um=[3*width+2*gap]*2,
                worst_pin_manhattan_um=score(order)[0],
                banks=banks, join=dict(x=width+gap, y=width+gap,
                                      width=width, height=width, orient='R0'))


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    sl = ROOT/'physical/ref_tile/qkd_pv_slice/views/ot_qwen_tp8_pv_slice_t/ot_qwen_tp8_pv_slice_t.lef'
    jo = ROOT/'physical/ref_tile/qkd_pv_join/io_spread.tcl'
    candidates = [screen(sl, jo, g) for g in (0.0, 21.6)]
    frames = []
    width, gap = 172.8, 21.6
    for columns in (2, 3):
        rows = (32+columns-1)//columns
        nx, ny = columns*3, rows*3
        frames.append(dict(column_blocks=columns, row_blocks=rows,
                           outline_um=[nx*width+(nx-1)*gap,
                                       ny*width+(ny-1)*gap],
                           child_tiles=288, independent_clock_entries=289,
                           control_tile_um=[43.2, 43.2],
                           control_and_external_channels_included=False))
    out = dict(schema='opentallas.pv-parent-pin-screen.v1',
               scope='necessary matched-bit Manhattan screen; no obstacle route, PG, clock, native or die-home claim',
               source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (sl, jo)},
               candidates=candidates, parent_frames=frames,
               join_east_face=dict(bits=1538, length_um=172.8,
                                   guarded_one_layer_cut=1538*0.096/172.8,
                                   guarded_two_layer_cut=1538*0.096/(2*172.8)),
               open=['all incident V/e/command/output/reset and clock nets',
                     'actual upper-layer eligibility, obstacles and routing',
                     '625 current relay homes overlap enlarged die envelopes',
                     'source-bound mapped parent plus native child views'])
    Path(args.out).write_text(json.dumps(out, indent=2)+'\n')


if __name__ == '__main__':
    main()
