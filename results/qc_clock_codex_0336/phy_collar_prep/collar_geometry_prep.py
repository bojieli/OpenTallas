import json,gzip,math
from pathlib import Path
p=json.load(gzip.open('/tmp/qcclock0336/phy_native_to_outer_bits.json.gz','rt'))
rows=[]
for b in p['bits']:
 if b['type'] not in ('phy_serdes','phy_serdes_b'): continue
 x,y=b['native_xy_um'];x+=.270;ox,oy=b['outer_xy_um']
 if b['type']=='phy_serdes_b':
  ox+=69.12;track_y=2324.16+34.56;ex=1563.84+34.56
  path=[[x,y],[x,track_y],[ex,track_y],[ex,oy],[ox,oy]]
 else:
  oy+=69.12;path=[[x,y],[x,oy-2.16],[ox,oy-2.16],[ox,oy]]
 lens=[abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(path,path[1:])];length=sum(lens)
 rows.append(dict(type=b['type'],bus=b['outer_bus'],bit=b['bit'],native_pin=b['native_pin'],polyline_um=path,length_um=length,minimum_405um_hops=math.ceil(length/405),minimum_120um_sections=math.ceil(length/120)))
summary={}
for typ in ['phy_serdes','phy_serdes_b']:
 r=[z for z in rows if z['type']==typ]; maxlen=max(z['length_um'] for z in r); hops=math.ceil(maxlen/405)
 # uniform all buses stages preserves grouping, compiler must later price directions/epochs exactly.
 sections=math.ceil((maxlen/hops)/120)
 buffers_per_bit=hops*sections # launch isolation buffer per hop plus intermediate repeats
 summary[typ]={'payload_bits':len(r),'max_polyline_um':maxlen,'min_polyline_um':min(z['length_um'] for z in r),'uniform_reach_hops':hops,'max_hop_um':maxlen/hops,'data_BUF24_perbit_upper':buffers_per_bit,'total_data_BUF24_upper':buffers_per_bit*len(r),'data_buffer_reserved_um2':buffers_per_bit*len(r)*.4374/.4,'full_payload_plus_epoch_FF_perbank':1202,'candidate_fullbank_count':hops,'candidate_new_data_FF':hops*len(r),'semantics_status':'Cycle delta is proposal only; actual direction/native-boundary semantics and epoch alignment must be implemented and mitered before pricing as adopted.'}
out={'status':'PREP NOT APPROVED; routing/cell/PG capacity construction constraints, no route or native timing claim','geometry_option':{'N_S_usable_collar_um':69.12,'E_usable_collar_um':69.12,'native_body_x_offset_um':.270,'preserves':'licensed N-face M5 geometry and dimensions','paired_lower_stack_added_height_um':138.24,'coll_s_candidate_new_height_um':665.28,'coll_n_candidate_new_height_um':717.12,'CBleft_margin_before_um':86.4,'CBleft_margin_after_um':17.28,'neighbor_softlogic_repack_status':'UNPROVEN; source plan inventory must fit, no assumption of free space'},'trackcut':{'signals':1202,'pitches_um':[.048,.064],'occupancy_guard':.6,'usable_height_um':69.12,'capacity':.6*69.12*(1/.048+1/.064),'required_width_um':1202/(.6*(1/.048+1/.064)),'excludes':'PG/clock and layer direction changes must be reserved explicitly; capacity is upper planning bound'},'types':summary,'bits':rows}
Path('/tmp/qcclock0336/collar_geometry_prep.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps({k:v for k,v in out.items() if k!='bits'},indent=2))
