#!/usr/bin/env python3
"""Concrete source-geometry estimate for ES0/ES1 shoreline repair. No canonical edits/builds."""
import json,sys,math
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,gen_phys as G,die_trial as D
P=S.Plan(json.load(open(sys.argv[1])));tn=P.parts['lk_ES0']['type'];t=P.types[tn];w,h=t['outline_um'];guard=63.64;strip=32.4
macro=[strip+guard,strip+guard,strip+guard+2608.48,strip+guard+924.48]
domain=[strip,strip,macro[2]+guard,macro[3]+guard]
assert P.parts['lk_ES0']['origin_um'][1]+macro[1]<=200
pins={}
for bus,bit,layer,x,y,face in G.type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y)
report=dict(label='ESTIMATEONLY_NOBUILD',outline_um=[w,h],macro_um=macro,domain_um=domain,guard_um=guard,shoreline_um=103.68+macro[1],core_frame_um=dict(W=strip,S=strip,E=w-domain[2],N=h-domain[3]),route_limits_um=405,variants_required=['ES0-specific source t1 variant','ES1-specific source t2 variant'],unchanged_instances='WN1/WN2 t1/t2 keep current source; do not shift shared master globally',slots=[])
for slot in t['ft_slots']:
 name=slot['name'];n=13 if name=='ft0' else 8;Y=(domain[3]+h)/2 if name=='ft0' else strip/2;lx=strip/2;rx=(domain[2]+w)/2
 # Coherent centreline uses actual endpoint pin-window centres; each bank has real per-bit cell positions.
 A=pins[name+'_i'];B=pins[name+'_o'];ami=[sum(v[k] for v in A.values())/len(A) for k in (0,1)];bmi=[sum(v[k] for v in B.values())/len(B) for k in (0,1)]
 xa=lx if ami[0]<w/2 else rx;xb=lx if bmi[0]<w/2 else rx
 poly=[ami,[xa,ami[1]],[xa,Y],[xb,Y],[xb,bmi[1]],bmi]
 centres,L=D.polyline_points(poly,[(k+1)/(n+1) for k in range(n)])
 maxhop=0.;bad=0;banks=[]
 for c in centres:
  rect=[c[0]-11.88,c[1]-6.48,c[0]+11.88,c[1]+6.48];banks.append(rect)
  assert 0<=rect[0]<rect[2]<=w and 0<=rect[1]<rect[3]<=h
  assert rect[2]<=domain[0] or rect[0]>=domain[2] or rect[3]<=domain[1] or rect[1]>=domain[3],rect
 for bit in A:
  # DFFHQNx1 site budget1.08x.27,16columns; epoch/control reserve fits23.76x12.96bank.
  off=[(bit%16-7.5)*1.08,(bit//16-15.5)*.27]
  q=[A[bit]]+[[round((c[0]+off[0])/.054)*.054,round((c[1]+off[1])/.27)*.27] for c in centres]+[B[bit]]
  mh=max(D._man(a,b) for a,b in zip(q,q[1:]));maxhop=max(maxhop,mh);bad+=mh>405
 report['slots'].append(dict(name=name,width=slot['width'],before_stations=slot['stations'],stations=n,added_cycles=n-slot['stations'],centreline_um=poly,length_um=L,bank_centres_um=centres,bank_rects_um=banks,all_bit_max_hop_um=maxhop,over405_bits=bad))
# Explicit narrow-band reservation is required: ordinary .25 default does not suffice in32.4umW/S bands.
hden=sum(1/P.layers[L]['pitch_um'] for L in ['M4','M6']);vden=sum(1/P.layers[L]['pitch_um'] for L in ['M5','M7'])
report['track_allocation_estimate']=dict(narrow_W_S_share=.8,narrow_tracks_H=strip*hden*.8,narrow_tracks_V=strip*vden*.8,narrow_max_ratio=514/min(strip*hden*.8,strip*vden*.8),limit=.6,north_default_share=.25,north_tracks=(h-domain[3])*hden*.25,north_ratio=512/((h-domain[3])*hden*.25))
report['added_payload_flops']=sum(s['width']*s['added_cycles'] for s in report['slots']);report['added_lane_cycles']={'coll__s_7S_LP__lk_ES1':5}
report['open_before_build']=['Actual per-layer track reservation must be emitted/enforced in partition kit; no rawfraction-only adoption.','Recomposeclock/reset/monitor andlandingbands in four-sideframe; actualclockmodel/crossing gatesstillrequired.','Generate physical-typevariants for ES0/ES1 only; preserveactualsource/timing ofWN1/WN2.','Binder mustmaterialize5extraFTstages andmodel/compilerpricechangedlane; smallestwidth+mutant exactness gate.','PHYsignal/powerbumpsmustregenerateontypedmacro+guard; actualIRnotrun.','ES1coll/provider parallelPHYinterface pinsneedactualabstractsource beforephysicalclosure.']
json.dump(report,open(sys.argv[2],'w'),indent=2);print(json.dumps({k:v for k,v in report.items() if k not in ['slots','open_before_build']},indent=1));print('SLOTS',[(s['name'],s['stations'],s['all_bit_max_hop_um'],s['over405_bits']) for s in report['slots']])
