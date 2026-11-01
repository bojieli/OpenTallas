"""Finite native Tnode PREP. No source/parent adoption or CAD launch."""
import json,math,csv,hashlib,collections
from pathlib import Path
P=Path(__file__).parent
old=json.loads((P/'old_plan_pins.json').read_text())['pins']
W,H=125.28,95.04
macros=[dict(instance='u_pad.u_d',master='ot_sram_1r1w_128x256_m1_r2c2',old=[38.976,15.132],origin=[15.168,8.796],size=[94.824,41.064],orient='R0'),dict(instance='u_pad.u_c',master='ot_sram_1r1w2c_32x64_m1',old=[38.976,67.068],origin=[15.168,69.372],size=[31.992,17.304],orient='R0')]
for m in macros:
 for a,b in zip(m['old'],m['origin']):assert abs((b-a)/.192-round((b-a)/.192))<1e-7
 x,y=m['origin'];w,h=m['size'];m['rect']=[x,y,x+w,y+h];m['halo_rect']=[x-4.32,y-4.32,x+w+4.32,y+h+4.32]
face_groups={'W':['ua'],'E':['uo','da'],'N':['ub','pad_k','pad_b','rst_n'],'S':['dn','db']}
bybase=collections.defaultdict(list)
for p in old:bybase[p['name'].split('[')[0]].append(p)
new=[];counts={};windows={};capacity={}
for face,groups in face_groups.items():
 members=[p for group in groups for p in bybase[group]]
 span=H if face in 'WE' else W
 lo=math.ceil((8.64-.024)/.048);hi=math.floor((span-8.64-.024)/.048)
 ticks=[round(lo+i*(hi-lo)/(len(members)-1)) for i in range(len(members))]
 assert len(set(ticks))==len(ticks)
 for p,k in zip(members,ticks):
  pos=round(.024+k*.048,6)
  x,y=(.096,pos) if face=='W' else (W-.096,pos) if face=='E' else (pos,H-.096) if face=='N' else (pos,.096)
  new.append(dict(name=p['name'],layer='M4' if face in 'WE' else 'M5',x=round(x,6),y=round(y,6),face=face,role='LIVE_FREE_PAD_INPUT' if p['name'].startswith('pad_') else 'native_port'))
 positions=[.024+k*.048 for k in ticks];j=0;peak=0
 for i,t in enumerate(positions):
  while positions[j]<t-10-1e-8:j+=1
  peak=max(peak,i-j+1)
 counts[face]=len(members);windows[face]=peak;capacity[face]=dict(pins=len(members),usable_tracks=hi-lo+1,track_use=len(members)/(hi-lo+1),peak_pins_per_10um=peak)
 assert peak<=60
new.append(dict(name='clk',layer='M5',x=64.776,y=64.8,face='internal',role='clock_NEW_PARENT_EVENT_REQUIRED'))
assert len(new)==len(old)==1341 and {p['name'] for p in new}=={p['name'] for p in old}
assert sum(p['role']=='LIVE_FREE_PAD_INPUT' for p in new)==7
old_by={p['name']:p for p in old};deltas=[dict(name=p['name'],old=old_by[p['name']],new=p) for p in new]
macroarea=sum(m['size'][0]*m['size'][1] for m in macros);free=W*H-macroarea
parent_origin_delta_um={'R0':[21.6,21.6],'MY':[25.92,21.6],'MX':[21.6,56.16],'R180':[25.92,56.16]}
plan=dict(generic_child_orientation_origin_delta_um=parent_origin_delta_um,actual_parent_event=dict(child_orient='R0_ALL30_CONFIRMED_BY_CORES',child_origin_delta_in_parent_local_um=[21.6,21.6],parent_partition_orient='15R0_15MY_INHERITED_NOT_A_CHILD_ORIENTATION',instance_specific_proof='OWNED_BY_HBM_CORES_PENDING30_ROW_PACKET'),status='PREP_NOT_ADOPTED_NO_PNR',outline_um=[W,H],aspect=W/H,macro_area_um2=macroarea,free_area_um2=free,measured_std_only_um2=1670.38686,source_clean_std_um2=1574.28,fill_actual_std_of_free=1670.38686/free,fill_source_std_of_free=1574.28/free,empty_outline_fraction=1-(1670.38686+macroarea)/(W*H),macros=macros,macro_halo_um=4.32,west_signal_access_um=15.168-4.32,east_signal_access_um=W-(15.168+94.824)-4.32,h_cross_between_halos_um=69.372-(8.796+41.064)-8.64,clock=dict(old_pin_um=[86.376,86.4],new_M5_pin_um=[64.776,64.8],new_PG_anchor_um=[64.8,64.8],island_rect=[60.48,60.48,69.12,69.12],halo_rect=[56.16,56.16,73.44,73.44],contract='unchanged833ps/TT250+-40/FF202.5+-40/setup0/hold25/pair80',parent_clock_event='REQUIRED_NOT_ADOPTED'),face_capacity=capacity,pad_contract=dict(this_core_free_pad_bits=7,global_live_pad_producer_groups=60,global_tnode_instances=30,physical_reservation_rectangles='UNSUPPLIED_NOT_INVENTED',ties_or_case_constraints='NONE'),source_cycles='UNCHANGED_RAW_NATIVE_NO_OUTER_FACE_SHELL',holds=['root/parent outline+pin+clock event approval','all parent endpoints/station chains refreshed and G0/G0C','actual pin/macro-track generation checks','ordinary source/gate/PLACE/actualgeometry/channel/clock/timing gates'])
for m in macros:
 a=plan['clock']['halo_rect'];b=m['halo_rect'];assert not(a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1])
(P/'candidate.json').write_text(json.dumps(plan,indent=2)+'\n');(P/'pin_delta.json').write_text(json.dumps(deltas,indent=1)+'\n');(P/'candidate_plan_pins.json').write_text(json.dumps(dict(schema='opentallas.hbm_arch.core_plan_pins.PROPOSAL_ONLY',pins=new),indent=1)+'\n')
print(json.dumps({k:plan[k] for k in ['outline_um','aspect','macro_area_um2','fill_actual_std_of_free','fill_source_std_of_free','empty_outline_fraction','west_signal_access_um','east_signal_access_um','h_cross_between_halos_um','face_capacity']},indent=2))
