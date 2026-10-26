#!/usr/bin/env python3
"""Exact legal per-bit candidate pins from actual ODB track/PG context.

No automatic route-time shifting: direct ODB placement and exact readback required.
Other source profiles must re-check their own actual PG before qualification.
"""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CTX=ROOT/'results/arch/hbm_die_v15/vm_identity_track_context_1417.json'
x=json.loads(CTX.read_text());g=json.loads((ROOT/'results/arch/hbm_die_v15/vm_identity_grants_1417.json').read_text())
PG=x['power_bterm_rectangles'];phase=.012;pitch=.048;half=.012;space=.024

def legal(pos,layer):
 return all(not(pos+half+space>r[1][0 if layer=='M5' else 1] and pos-half-space<r[1][2 if layer=='M5' else 3]) for r in PG if r[0]==layer)
def available(lo,hi,layer,minsep=.192):
 out=[];k=math.ceil((lo-phase)/pitch)
 while phase+k*pitch<=hi+1e-8:
  p=round(phase+k*pitch,6);k+=1
  if legal(p,layer) and (not out or p-out[-1]>=minsep-1e-8):out.append(p)
 return out

def spread(items,lo,hi,layer):
 n=sum(len(i[1]) for i in items);slots=available(lo,hi,layer);assert len(slots)>=n,(layer,lo,hi,n,len(slots))
 selected=[slots[round(i*(len(slots)-1)/(n-1))] for i in range(n)] if n>1 else [slots[len(slots)//2]]
 cursor=0
 for p,bits in items:
  p['bit_offsets_um']=selected[cursor:cursor+len(bits)];cursor+=len(bits)
  p.pop('bit_pitch_um',None);p.pop('bit_centres_rule',None)
  p['bit_order']='ascending RTL bit index follows ascending face coordinate'
  p['span_um']=[round(p['bit_offsets_um'][0]-half,6),round(p['bit_offsets_um'][-1]+half,6)]
  p['offset']=sum(p['span_um'])/2

def bits(p):
 name=p['name'];return list(range(int(name.split('[')[1].split(':')[0])+1)) if '[' in name else [0]

for s in g['slots']:
 w,h=s['outline']['w'],s['outline']['h'];mid=w/2
 for face in 'WES':spread([(p,bits(p)) for p in s['pins'] if p['face']==face],2,(w if face=='S' else h)-2,'M5' if face=='S' else 'M4')
 for side,lo,hi in [('L',2,mid-2),('R',mid+2,w-2)]:
  spread([(p,bits(p)) for p in s['pins'] if p['face']=='N' and p['name'] not in ('clk','rst_n') and ((p['offset']<mid)==(side=='L'))],lo,hi,'M5')
 central=available(mid-1,mid+1,'M5');clk=min(central,key=lambda p:abs(p-mid));rst=min((p for p in central if abs(p-clk)>=.192-1e-8),key=lambda p:abs(p-(clk+.192)))
 for name,p0 in [('clk',clk),('rst_n',rst)]:
  p=next(p for p in s['pins'] if p['name']==name);p.update(bit_offsets_um=[p0],span_um=[round(p0-half,6),round(p0+half,6)],offset=p0,bit_order='scalar');p.pop('bit_pitch_um',None)
 s['clock_entry']['offset']=clk;s['pin_ranges']={p['name'].split('[')[0]:p['span_um'] for p in s['pins']};s['grant']='actual_track_PG_perbit_identity_diagnostic_1417'
 s['assigned_pin_rule']='bit_offsets_um is authoritative; do not infer evenly spaced positions from vector spans; direct ODB rectangles on these centres and strict postIOP readback required'
 s['track_context_sha256']=hashlib.sha256(CTX.read_bytes()).hexdigest();s['PG_qualification_scope']='Actual q1_b0 IOP PG/track template only; each distinct current source/profile must verify its own actual PG and ODB before qualification'
 for face in 'NSEW':
  pos=sorted(z for p in s['pins'] if p['face']==face for z in p['bit_offsets_um']);assert min(b-a for a,b in zip(pos,pos[1:]))>=.192-1e-6
 for p in s['pins']:
  assert len(p['bit_offsets_um'])==len(bits(p))
  assert all(abs((z-phase)/pitch-round((z-phase)/pitch))<1e-6 and legal(z,p['layer']) for z in p['bit_offsets_um'])
g.update(actual_track_context=str(CTX.relative_to(ROOT)),minimum_perbit_separation_um=.192,signal_rect_width_um=.024,source_same32_identity_masters=True,canonical_die_contract_mutated=False)
f=ROOT/'results/arch/hbm_die_v15/vm_identity_legal_grants_1417.json';f.write_text(json.dumps(g,indent=1)+'\n');print('legal PG-template-clear exact-bit slots',len(g['slots']))
