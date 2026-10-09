#!/usr/bin/env python3
"""Capture the first failing r4c relay's actual occupancy before the expensive search."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--options', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args(Path(a.options).read_text().split()))
    original = F.Placer.near
    def capture(self, cx, cy, w, h, allowed, prev=None, **kwargs):
        if prev and abs(prev[0] - 12651.108) < 0.01 and abs(prev[1] - 4665.6) < 0.01:
            boxes = [dict(name=i.name, master=i.master, kind=i.kind, region=i.region,
                          box=list(i.box())) for i in self.m['insts']
                     if i.x < cx + 700 and i.x + i.w > cx - 700
                     and i.y < cy + 700 and i.y + i.h > cy - 700]
            Path(a.out).write_text(json.dumps(dict(source_commit=os.environ['DIAG_SOURCE_COMMIT'],
                previous=prev, target=[cx,cy], relay_size=[w,h], allowed=allowed, reach=kwargs,
                boxes=boxes), indent=2)+'\n')
            raise SystemExit(0)
        return original(self, cx, cy, w, h, allowed, prev=prev, **kwargs)
    F.Placer.near = capture
    F.build()
    raise SystemExit('target placement not reached')


if __name__ == '__main__':
    main()
