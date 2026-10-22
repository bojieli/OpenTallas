#!/usr/bin/env python3
"""Enumerate actual paired child pin distances of a diagnostic placement."""
import argparse,json,hashlib,math
from pathlib import Path
from qc_safe_graph import ROOT
p=argparse.ArgumentParser();p.add_argument('witness');p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=json.loads(Path(a.witness).read_text());plan=json.loads(Path(a.plan).read_text());positions={v['inst']:v['at']for v in d['placement']};assets={}
for master,v in plan['native_pin_assets'].items():
 raw=(ROOT/v['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==v['sha256'];assets[master]=json.loads(raw)['pins']
rows=[];unqualified=[]
for bus in plan['bindings']:
 src,dst=bus['src'],bus['dst']
 if src.get('master')not in assets or dst.get('master')not in assets:
  unqualified.append(dict(net=bus['net'],src=src,dst=dst));continue
 starts=[ep.get('range',[0,bus['bits']-1])[0]for ep in [src,dst]];longest=-1;bad=0;badbit=None
 for i in range(bus['bits']):
  coords=[]
  for ep,lo in zip([src,dst],starts):
   pin=assets[ep['master']][ep['port']+f'[{lo+i}]'];assert len(pin['centers_um'])==1
   coords.append([x+y for x,y in zip(positions[ep['inst']],pin['centers_um'][0])])
  length=sum(abs(x-y)for x,y in zip(*coords))
  if length>longest:longest=length;badbit=i
  if length>405+1e-7:bad+=1
 rows.append(dict(net=bus['net'],kind=bus['kind'],src=src,dst=dst,bits=bus['bits'],max_native_manhattan_um=round(longest,6),bits_over405=bad,worst_physical_bus_bit=badbit,ordinary_timing=bus['ordinary_timing'],minimum_405um_intermediate_stages=max(0,math.ceil(longest/405)-1),stage_scope='distance-only lower bound; NO stage/calendar/clock/reset adoption implied'))
rows.sort(key=lambda r:-r['max_native_manhattan_um']);out=dict(schema='opentallas.cb16.native_reach_audit.v1',diagnostic_only=True,release_ready=False,witness_sha256=hashlib.sha256(Path(a.witness).read_bytes()).hexdigest(),plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),native_bus_bindings=len(rows),native_bits=sum(r['bits']for r in rows),native_bus_over405=sum(bool(r['bits_over405'])for r in rows),native_bits_over405=sum(r['bits_over405']for r in rows),max_native_manhattan_um=max(r['max_native_manhattan_um']for r in rows),unqualified_bindings=unqualified,rows=rows,scope='All known child paired-bit Manhattan distances enumerated; A0/boundary pin references remain unqualified; no obstacle route/clock/reset/timing/calendar proof')
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print('NATIVE_REACH_AUDIT',out['native_bus_bindings'],'buses',out['native_bits'],'bits',out['native_bus_over405'],'buses_over405','max',out['max_native_manhattan_um'])
