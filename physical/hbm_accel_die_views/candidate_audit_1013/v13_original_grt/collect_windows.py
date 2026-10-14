#!/usr/bin/env python3
"""Aggregate the router's 4x4 gcell usage blocks; preserve pooling limitations."""
import argparse, collections, hashlib, json
from pathlib import Path

def collect(path):
    gx = gy = None
    bins = collections.defaultdict(float)
    layers = collections.defaultdict(float)
    for line in path.open():
        if line.startswith('GRIDX'):
            gx = [int(v)/1000 for v in line.split()[1].split(',')]
        elif line.startswith('GRIDY'):
            gy = [int(v)/1000 for v in line.split()[1].split(',')]
        elif line.startswith('L '):
            row = line.split(); layer, j = row[1], int(row[2])
            if layer in ('M2', 'M3'): continue
            y = gy[min(j+2, len(gy)-1)]
            for n, token in enumerate(row[3:]):
                cap, use = map(float, token.split('/'))
                excess = max(0.0, use-cap)
                if excess:
                    x = gx[min(4*n+2, len(gx)-1)]
                    bins[int(x//2000)*2000, int(y//2000)*2000] += excess
                    layers[layer] += excess
    total = sum(bins.values())
    hub = sum(v for (x,y),v in bins.items() if 10000<=x<20000 and 8000<=y<18000)
    return dict(source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                bin_um=2000, pooled_block_overflow_sum=total, pooled_by_layer=dict(layers),
                note='Sums positive usage-capacity on 4x4 pooled blocks; pooling can hide fine-gcell excess. This is spatial diagnostic, not the exact signoff overflow. Coordinates are block centers; bins are 2 mm.',
                hub_binned_share=hub/total if total else 0,
                top_bins=[dict(x_um=x,y_um=y,pooled_excess=v,share=v/total) for (x,y),v in sorted(bins.items(), key=lambda kv:-kv[1])[:20]])

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();a.out.write_text(json.dumps(collect(a.source),indent=2)+'\n')
