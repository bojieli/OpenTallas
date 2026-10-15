#!/usr/bin/env python3
"""Validate actual IO-stage ODB dump against the die lead's Engram pin grant.

Source this repository's fp_margin_lint.tcl and run ot_fp_lint_dump on the
retained IO/final ODB first. This is real pin/PG geometry evidence, not route,
clock insertion, timing or production qualification.
"""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--dump',type=Path,required=True)
p.add_argument('--original-ports',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=json.loads(a.dump.read_text());old=json.loads(a.original_ports.read_text())
expected={}
for value in old['ports'].values():
 for name,layer,*rect in value['pins']:
  assert name not in expected
  expected[name]=(layer,rect)
for base,start in [('ck_hash',140.028),('ck_rows',160.044)]:
 for i in range(6):
  x=round(start+.480*i,3);expected[f'{base}[{i}]']=('M5',[round(x-.012,3),215.916,round(x+.012,3),216.0])
assert len(expected)==674
signals={row[0]:row for row in d['bterms'] if row[2] not in ('POWER','GROUND')}
pg=[(row[0],box[0],box[1]) for row in d['bterms'] if row[2] in ('POWER','GROUND') for box in row[4]]
missing=sorted(set(expected)-set(signals));unexpected=sorted(set(signals)-set(expected));mismatch=[];overlaps=[]
for name,(layer,rect) in expected.items():
 if name not in signals:continue
 boxes=signals[name][4]
 if len(boxes)!=1 or boxes[0][0]!=layer or any(abs(x-y)>.00051 for x,y in zip(boxes[0][1],rect)):
  mismatch.append(dict(pin=name,expected=[layer,rect],actual=boxes));continue
 for power,metal,box in pg:
  if metal==layer and min(rect[2],box[2])-max(rect[0],box[0])>1e-9 and min(rect[3],box[3])-max(rect[1],box[1])>1e-9:
   overlaps.append(dict(pin=name,power=power,metal=metal,power_box=box))
 for kind,lo,hi,box in d.get('pdn_edge',[]):
  if layer in (lo,hi) and min(rect[2],box[2])-max(rect[0],box[0])>1e-9 and min(rect[3],box[3])-max(rect[1],box[1])>1e-9:
   overlaps.append(dict(pin=name,power_shape=kind,metal=layer,power_box=box))
body_matches=len(d.get('die',[]))==4 and all(abs(x-y)<.00051 for x,y in zip(d['die'],[0,0,324,216]))
power_names=sorted({row[0] for row in d['bterms'] if row[2] in ('POWER','GROUND') and row[4]})
record=dict(body_matches_grant=body_matches,power_names=power_names,schema='opentallas.s81.engram_native_pin_audit.v1',scope='Actual ODB geometry only; no physical clock/timing/route/production qualification',dump_sha256=hashlib.sha256(a.dump.read_bytes()).hexdigest(),original_ports_sha256=hashlib.sha256(a.original_ports.read_bytes()).hexdigest(),expected_signals=674,actual_signals=len(signals),original_rectangles=662,new_clock_rectangles=12,actual_PG_boxes=len(pg),missing=missing,unexpected=unexpected,rectangle_mismatch=mismatch,same_layer_PG_overlaps=overlaps,passed=not(missing or unexpected or mismatch or overlaps) and body_matches and {'VDD','VSS'}.issubset(power_names))
a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ['passed','expected_signals','actual_signals','actual_PG_boxes']}));print('mismatch',len(mismatch),'PG overlaps',len(overlaps))
raise SystemExit(0 if record['passed'] else 1)
