#!/usr/bin/env python3
"""Readonly check of a standard-export TA15 body's real signal pin set and geometry."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True);p.add_argument('--view',required=True);p.add_argument('--out',required=True);a=p.parse_args()
rtl=Path(a.rtl).read_text();v=Path(a.view);expected={}
header=rtl.split('module ot_hbm_production_clock_digital_body (',1)[1].split(');',1)[0]
for m in re.finditer(r'(input|output)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?([\w,\s]+?)(?=(?:input|output)\s+wire|$)',header):
 direction,hi,lo,names=m.groups()
 for name in re.findall(r'\b\w+\b',names):
  for bit in (range(int(lo),int(hi)+1) if hi is not None else [None]):
   expected[name if bit is None else f'{name}[{bit}]']=direction
assert expected
lef=(v/'ot_hbm_production_clock_digital_body.lef').read_text()
size=tuple(map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups()));assert size==(100.224,99.36),size
pins={};layers=set()
for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n',lef,re.M):
 name=m.group(1);block=lef[m.end():].split('END '+name,1)[0]
 if name in ('VDD','VSS'):continue
 direction=re.search(r'\bDIRECTION\s+(INPUT|OUTPUT)',block).group(1).lower()
 ls=re.findall(r'\bLAYER\s+(\w+)\s*;',block);assert ls and set(ls)<={'M4','M5'},(name,ls);layers.update(ls)
 rects=[tuple(map(float,x)) for x in re.findall(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',block)]
 assert rects and all(0<=x0<x1<=size[0] and 0<=y0<y1<=size[1] for x0,y0,x1,y1 in rects),(name,rects)
 pins[name]=direction
assert pins==expected,dict(missing=sorted(set(expected)-set(pins)),extra=sorted(set(pins)-set(expected)))
for corner in ('ss','tt','ff'):
 lib=(v/f'ot_hbm_production_clock_digital_body_{corner}.lib').read_text()
 names=set(re.findall(r'\bpin\s*\(\s*"?([^"\s()]+)"?\s*\)',lib))-{'VDD','VSS'}
 assert names==set(expected),(corner,sorted(set(expected)-names),sorted(names-set(expected)))
Path(a.out).write_text(json.dumps(dict(status='PASS',signal_pins=len(expected),outline_um=size,signal_layers=sorted(layers),corners=['ss','tt','ff'],scope='actual source bits, LEF pin bounds/directions/layers and Liberty pins; no die integration claim'),indent=1)+'\n')
