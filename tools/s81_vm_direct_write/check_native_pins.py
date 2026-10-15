#!/usr/bin/env python3
"""Check exported native LEF signal pin positions against exact assigned Tcl.
A green timing/child-lint record alone does not establish source pin identity.
"""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--lef',type=Path,required=True);ap.add_argument('--assigned',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 assert not a.out.exists(),'write fresh immutable evidence'
 text=a.lef.read_text();size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text);w,h=map(float,size.groups())
 pins={}
 for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text,re.M|re.S):
  name,body=m.groups();rects=[]
  for q in re.finditer(r'\bLAYER\s+(\S+)\s*;(.*?)(?=\bLAYER\s+|\Z)',body,re.S):
   for b in re.finditer(r'\bRECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*;',q[2]):rects.append((q[1],list(map(float,b.groups()))))
  pins[name]=rects
 assigned=re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}',a.assigned.read_text());assert assigned
 bad=[];rows=[]
 for n,layer,x,y in assigned:
  x=float(x);y=float(y);face='W' if abs(x)<.001 else 'E' if abs(x-w)<.001 else 'S' if abs(y)<.001 else 'N' if abs(y-h)<.001 else None
  assert face,(n,x,y,w,h)
  candidates=[]
  for l,b in pins.get(n,[]):
   if l!=layer:continue
   along=(b[0]+b[2])/2 if face in 'NS' else (b[1]+b[3])/2
   edge=b[1] if face=='S' else b[3] if face=='N' else b[0] if face=='W' else b[2]
   expect=x if face in 'NS' else y;boundary=h if face=='N' else w if face=='E' else 0
   candidates.append(max(abs(along-expect),abs(edge-boundary)))
  error=min(candidates) if candidates else None
  if error is None or error>.00101:bad.append(dict(pin=n,face=face,error_um=error,assigned=[x,y,layer],actual_rects=pins.get(n)))
  rows.append(dict(pin=n,face=face,max_coordinate_error_um=error))
 d=dict(schema='opentallas.s81.vm-direct-write-native-assigned-pin-check.v1',status='PASS' if not bad else 'FAIL',scope='Every actual exported signal pin checked at assigned native face/layer/along-edge coordinate; no proof of global parentreach/CTS/timing',lef=str(a.lef),lef_sha256=hashlib.sha256(a.lef.read_bytes()).hexdigest(),assigned=str(a.assigned),assigned_sha256=hashlib.sha256(a.assigned.read_bytes()).hexdigest(),outline_um=[w,h],assigned_bits=len(assigned),checked_bits=len(rows),mismatches=bad,max_coordinate_error_um=max((r['max_coordinate_error_um'] or 0) for r in rows),pins=rows)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(f"NATIVE_ASSIGNED_PIN_{d['status']} checked {len(rows)} mismatches {len(bad)} max_um {d['max_coordinate_error_um']}");raise SystemExit(bool(bad))
if __name__=='__main__':main()
