#!/usr/bin/env python3
"""Candidate cap16 leaf pins and geometric capacity; parent seams remain unproved."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81'))
import v19_pins_1014 as V
out=ROOT/'physical/s81_die_pins/v20_vm_cap16_candidate';out.mkdir(parents=True,exist_ok=True)
ports={'f_c':V.run('N',.396,832),'ck':V.run('W',4.044,1),'rn':V.run('W',5.004,1),'gid':V.run('W',6.060,4),'flush':V.run('W',7.020,1)}
x=14.028
for p,n in [('o_v',1),('o_row',14),('o_m',16),('o_d',512),('flt',5)]:
 ports[p]=V.run('S',x,n);x+=n*.096
V.write(out,'dsfd_vm_static_cap_leaf',[80.64,230.04],ports,'ck','CANDIDATE N832 M5 ingress, S548 M5 egress, W clock/reset/gid/flush M4; nativepinreg92154feb6; no parent seam proof','v20_vm_cap16_candidate',{'source':'tools/s81_vm_cap16_sizing/pins.py','clock_entries':{'serial':['ck']},'reset_entries':{'serial':['rn']},'signal_layer_cap':'M5','adoption':'candidate geometry only; source mapped area, CTS, TT/FF/DRC, parent seams and composition required'})
# M5 native track centers .012 + n*.048; assigned signal pins use alternate tracks.
checks=[]
for face in ['N','S','W']:
 pp=[v for vals in ports.values() for v in vals if v[0]==face];coords=sorted(v[2] for v in pp);length=80.64 if face in 'NS' else 230.04
 assert all(abs((c-.012)/.048-round((c-.012)/.048))<1e-6 for c in coords)
 checks.append({'face':face,'bits':len(pp),'native_track_pitch_um':.048,'pin_pitch_um':min(round(b-a,3) for a,b in zip(coords,coords[1:])),'first_center_um':coords[0],'last_center_um':coords[-1],'full_face_track_capacity':int(length/.048),'demand_over_raw_capacity':len(pp)/int(length/.048),'cut_limit':.60,'raw_cut_pass':len(pp)/int(length/.048)<=.60})
report={'status':'CANDIDATE_LOCAL_PIN_CAPACITY_PASS','outline_um':[80.64,230.04],'source_commit':'92154feb6','checks':checks,'all_bits':sum(len(v) for v in ports.values()),'pin_pairs_to_parent_proven':False,'global_cut_proven':False,'pin_register_timing_proven':False,'qualification':'Only boundary spacing, native tracks and raw face track capacity. No parent seam/placement/CTS/timing qualification.'}
(out/'pin_capacity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
