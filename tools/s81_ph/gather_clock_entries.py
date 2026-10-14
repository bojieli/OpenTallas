#!/usr/bin/env python3
"""Draft 133 additional gather parent clock entries for die-lead review.
Preserves every existing pin. Selects nearest free native face track; no wire-R or phase qualification claim.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PITCH=.048;PHASE=.012;SEP=.192

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--assigned',required=True);ap.add_argument('--strip-plan',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 source=Path(a.assigned);parent=json.loads(source.read_text());plan=json.loads(Path(a.strip_plan).read_text());w,h=parent['outline_um'];occupied={(f,l):[] for f,l in [('N','M5'),('S','M5'),('E','M4'),('W','M4')]}
 for name,port in parent['ports'].items():
  assert name!='ck_r','parent already has authoritative relay clocks; do not overwrite them'
  for f,l,c,d in port['per_bit']:
   if (f,l) in occupied:occupied[(f,l)].append(c)
 forbidden={}
 for fl,values in occupied.items():
  blocked=set()
  for c in values:
   tick=round((c-PHASE)/PITCH)
   assert abs(PHASE+tick*PITCH-c)<1e-6,(fl,c)
   blocked.update(range(tick-3,tick+4))
  forbidden[fl]=blocked
 rows=[];bits=[None]*133
 for child in sorted(plan['relay_children'],key=lambda c:c['clock_index']):
  idx=child['clock_index'];cx,cy=child['clock_entry']['location_um'];choices=[]
  for face,layer in occupied:
   axis=cx if face in ('N','S') else cy;extent=w if face in ('N','S') else h
   near=round((axis-PHASE)/PITCH);low=math.ceil((SEP-PHASE)/PITCH);high=math.floor((extent-SEP-PHASE)/PITCH)
   for radius in range(high-low+1):
    possible=[]
    for tick in sorted({near-radius,near+radius}):
     if low<=tick<=high and tick not in forbidden[(face,layer)]:
      c=PHASE+tick*PITCH;x=c if face in ('N','S') else (0 if face=='W' else w);y=c if face in ('W','E') else (0 if face=='S' else h)
      possible.append((abs(cx-x)+abs(cy-y),face,layer,c,tick,[x,y]))
    if possible:choices.extend(possible);break
  if not choices:raise SystemExit('REFUSED no native free clock-entry track')
  length,face,layer,c,tick,location=min(choices)
  bits[idx]=[face,layer,round(c,6),.192];occupied[(face,layer)].append(c);forbidden[(face,layer)].update(range(tick-3,tick+4))
  ins=json.loads((ROOT/child['insertion']).read_text());rchild={corner:ins[corner]['boundary']['mean'] for corner in ('ss','tt','ff')}
  rows.append({'port':f'ck_r[{idx}]','index':idx,'domain':'serial' if idx==132 else 'stream','child_pin':child['instance']+'/ck','child_clock_location_um':[cx,cy],'parent_face':face,'layer':layer,'parent_location_um':location,'entry_wire_manhattan_um':round(length,6),'Rchild_ps':rchild,'Rwire_ps':None,'phi_minus_R_qualified':False,'child_insertion_sha256':child['insertion_sha256']})
 assert all(bits)
 clock_min=[]
 for b in bits:
  f,l,c,d=b
  clock_min.extend(abs(c-v) for v in occupied[(f,l)] if abs(c-v)>1e-9)
 assert min(clock_min)>=SEP-1e-6
 out={'schema':'opentallas.s81.gather.clock_entry_draft.v1','status':'DRAFT_REQUIRES_DIE_LEAD_ASSIGNMENT','authoritative_parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'preserved_port_sha256':{n:digest(p) for n,p in parent['ports'].items()},'preserved_existing_ports':list(parent['ports']),'ports_addition':{'ck_r':{'bits':133,'uniform':False,'per_bit':bits}},'clock_entries':rows,'native_track':{'phase_um':PHASE,'pitch_um':PITCH},'minimum_clock_to_same_face_layer_other_pin_um':round(min(clock_min),6),'max_entry_wire_manhattan_um':max(r['entry_wire_manhattan_um'] for r in rows),'Rwire_ps':None,'phase_qualification':False,'pending':['die lead approval and publication','routed entry-wire clock resistance/capacitance and insertion','phi minus (Rchild plus Rwire) qualification','root/ctl/relay corner setup/hold and related-domain phase checks']}
 Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(f"CLOCK_DRAFT 133 entries, min separation{out['minimum_clock_to_same_face_layer_other_pin_um']}um, max wire{out['max_entry_wire_manhattan_um']}um; phase OPEN")
if __name__=='__main__':main()
