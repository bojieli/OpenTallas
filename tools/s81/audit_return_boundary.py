#!/usr/bin/env python3
"""Audit exact failed return-chain occupancy without loading model pickle.

This enumerates legal lattice origins in one supplied bay using the captured
placement obstacles, the actual relay envelope and Manhattan source reach.
It does not change placement/search, and supplies no PG, pin or STA proof.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def audit(record, bay_index=-1, grid=(.432, 2.16), gap=.432, reach=430.56):
    bay = record['allowed'][bay_index]
    w, h = record['native_outline_along'][str(record['local']['horiz'])]
    prev = record['local']['cur']
    # Bound the scan by both the bay and source reach. Every possible body
    # origin in this rectangle is considered, including a row absent from
    # the production search's transverse samples.
    lo = [max(bay[a], prev[a] - reach - (w, h)[a]/2) for a in (0, 1)]
    hi = [min(bay[a+2] - (w, h)[a], prev[a] + reach - (w, h)[a]/2) for a in (0, 1)]
    origins = []
    for iy in range(math.ceil((lo[1]-1e-7)/grid[1]), math.floor((hi[1]+1e-7)/grid[1])+1):
        y = iy*grid[1]
        for ix in range(math.ceil((lo[0]-1e-7)/grid[0]), math.floor((hi[0]+1e-7)/grid[0])+1):
            x = ix*grid[0]
            if abs(x+w/2-prev[0])+abs(y+h/2-prev[1]) > reach+1e-7:
                continue
            if any(o['x'] < x+w+gap-1e-6 and x-gap < o['x']+o['w']-1e-6
                   and o['y'] < y+h+gap-1e-6 and y-gap < o['y']+o['h']-1e-6
                   for o in record['nearby_obstacles']):
                continue
            if any(a < x+w and x < c and b < y+h and y < d
                   for a,b,c,d,*_ in record['reserved_sites']):
                continue
            origins.append([round(x,6), round(y,6)])
    return dict(scope='PARTIAL_CAPTURE_GEOMETRY_ONLY_NO_ROUTE_STA',
                chain=record['chain'], source_commit=record['source_commit'],
                bay=bay, grid_um=grid, gap_um=gap, reach_um=reach,
                envelope_um=[w,h], legal_origins=len(origins),
                first_last=[origins[0],origins[-1]] if origins else [],
                legal_rows=sorted({p[1] for p in origins}),
                limitation='Nearby captured placement only; no native pins, PG, reset, CTS, route or STA proof.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--bay-index',type=int,default=-1)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    raw=args.capture.read_bytes()
    result=audit(json.loads(raw),args.bay_index)
    result['capture_sha256']=hashlib.sha256(raw).hexdigest()
    text=json.dumps(result,indent=2)+'\n'
    if args.out: args.out.write_text(text)
    else: print(text,end='')


if __name__ == '__main__':
    main()
