#!/usr/bin/env python3
"""Build NEW assumed PHY access-contract candidates; never edits historical inputs.

This is a modeled licensed-PHY interface reservation, not evidence of foundry IP.
The old abstract encloses all M4 supplies below M5 OBS. Reserve two 0.4um M5
columns for actual 0.12um PG straps and 0.14um side keepout. M4 pins, M1-M4
OBS, signal interfaces, dimensions and all other M5 OBS remain byte-identical.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
from decimal import Decimal as D, ROUND_FLOOR

SCHEMA = 'opentallas.assumed-phy-pg-access.v1'

def build(text):
    width, height = map(D, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', text).groups())
    left = ((width-D('2'))/D('.048')).to_integral_value(rounding=ROUND_FLOOR)*D('.048')
    centers = [left+D('.06'), left+D('1.068')]
    windows = [(c-D('.2'), c+D('.2')) for c in centers]
    obs_start = text.index('  OBS\n')
    body = text[obs_start:]
    match = re.search(r'(    LAYER M5 ;\n)    RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;', body)
    if not match:
        raise ValueError('expected one rectangular M5 obstruction')
    x0,y0,x1,y1 = map(D,match.groups()[1:])
    if not (x0 < windows[0][0] < windows[-1][1] < x1):
        raise ValueError('access columns outside M5 OBS')
    # Fail if the declared reserved columns intersect an existing signal pin.
    signal_part = text[:text.index('  PIN VDD\n')]
    for layer, geometry in re.findall(r'LAYER (M\d+) ;\n(.*?)(?=    END)', signal_part, re.S):
        if layer != 'M5': continue
        for r in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', geometry):
            a,b,c,d = map(D,r)
            if any(a < hi and c > lo for lo,hi in windows):
                raise ValueError('reserved PG column overlaps M5 signal access')
    rects=[]; cursor=x0
    for lo,hi in windows:
        rects.append((cursor,y0,lo,y1)); cursor=hi
    rects.append((cursor,y0,x1,y1))
    replacement=match[1]+''.join('    RECT '+' '.join(map(str,r))+' ;\n' for r in rects).rstrip('\n')
    body=body[:match.start()]+replacement+body[match.end():]
    out=text[:obs_start]+body
    out='# ASSUMED PHY PG ACCESS CONTRACT v1; candidate only; no licensed-layout/foundry qualification.\n'+out
    receipt=dict(schema=SCHEMA,status='ASSUMED_UNQUALIFIED',source_sha256=hashlib.sha256(text.encode()).hexdigest(),
      candidate_sha256=hashlib.sha256(out.encode()).hexdigest(),width_um=str(width),height_um=str(height),
      area_delta_um2=0,interface_delta='none; original M4 PG pins preserved',
      m5_reserved_columns_um=[[str(a),str(b)] for a,b in windows],m5_reserved_area_um2=str(D('.8')*(y1-y0)),
      strap_width_um='.12',strap_spacing_um='.888',strap_pitch_um='2.016',
      offset_r0_mx_um=str(left+D('.06')),offset_my_r180_um=str(width-left-D('1.068')),
      claim='Modeled PHY access reservation only; needs actual PDN connectivity, short/obstruction checks and eventual vendor confirmation.')
    return out,receipt

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('input',type=Path); ap.add_argument('output',type=Path)
    args=ap.parse_args()
    if args.input.resolve()==args.output.resolve(): raise SystemExit('refusing historical input mutation')
    out,receipt=build(args.input.read_text()); args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(out); args.output.with_suffix('.access.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__': main()
