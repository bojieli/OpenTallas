#!/usr/bin/env python3
"""PG-aware conditional root pin scenario and VM transport register lower bounds.
All repaired ranges are candidates. No native ABI, routing grid or pin assignment.
"""
import collections,hashlib,json,math
from pathlib import Path
from vm_lef_pins import read
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 rf=A/'vm_band_die_root_candidate_input_codex.json';die=json.loads(rf.read_text());gf=A/'vm_cluster_layer_grant_1013.json';grant=json.loads(gf.read_text());comp=json.loads((A/'vm_band_composition_codex.json').read_text());pg=grant['die_pg'];pitch=pg['pitch_um'];phases=pg['net_center_phases_um'];half=pg['width_um']/2;pinhalf=.02;clearance=.04
 def pg_hit(x,guard=0):
  return[(net,round(ph+round((x-ph)/pitch)*pitch,4))for net,ph in phases.items()if abs(x-(ph+round((x-ph)/pitch)*pitch))<half+guard-1e-9]
 rows=[];allhits=[]
 for slot in die['slots']:
  fields=[]
  for r in slot['pin_ranges_candidate']:
   if r['layer']not in ('M8','M9'):continue
   bad=[]
   for bit in range(r['bits']):
    x=(slot['x']if r['layer']=='M9' else slot['y'])+r['first']+.16*bit;hits=pg_hit(x)
    if hits:bad.append(dict(bit=bit,x_um=round(x,4),PG_stripes=hits));allhits.append(dict(slot=slot['n'],face=r['face'],layer=r['layer'],field=r['name'],bit=bit,axis='x'if r['layer']=='M9'else'y',coordinate_um=round(x,4),PG_stripes=hits))
   fields.append(dict(face=r['face'],layer=r['layer'],field=r['name'],bits=r['bits'],center_overlap_count=len(bad),center_overlaps=bad))
  # Provisional globalroutinggrid phase0, pitch.08; maintain >=2tracks(.16)
  # between adjacent signal centers while skipping actual PG metal + guard.
  available=[];prev=-math.inf
  lo=slot['x']+1.6;hi=slot['x']+slot['w']-1.6
  for t in range(math.ceil(lo/.08),math.floor(hi/.08)+1):
   x=t*.08
   if x-prev<.16-1e-8 or pg_hit(x,pinhalf+clearance):continue
   available.append(round(x,4));prev=x
  response=available[:233];request=available[243:352] #10 signal-center positions separation
  side_centers=[];prev=-math.inf
  for t in range(math.ceil((slot['y']+1.6)/.08),math.floor((slot['y']+slot['h']-1.6)/.08)+1):
   y=t*.08
   if y-prev<.16-1e-8 or pg_hit(y,pinhalf+clearance):continue
   side_centers.append(round(y,4));prev=y
  repaired=dict(qualified=False,assigned=False,response_M9_N_centers_global_um=response,request_M9_N_centers_global_um=request,
    instruction_layer_scenario='M7 on N/S, separatefrom live fill/paused compute consumption; actual localPG/OBS/trackphase pending',
    instruction_M7_N_centers_global_um=[round((math.ceil((slot['x']+1.6)/.064)+2*i)*.064,4)for i in range(380)],
    side_M8_PG_guarded_centers_global_um=side_centers,M8_full233_response_complete=len(side_centers)>=233,
    side_split_layer_scenario=dict(M8_data128_centers_global_um=side_centers[:128],M6_literal_metadata105_centers_global_um=[round((math.ceil((slot['y']+1.6)/.064)+2*i)*.064,4)for i in range(105)],scope='candidate literal96+phase8+valid metadata split; actualmasterABI/M6OBS/PG/gridpending'),
    total_PG_guarded_M9_two_track_centers=len(available),M9_response_request_complete=len(response)==233 and len(request)==109,
    global_grid_phase_um=0,grid_phase_scope='provisional routinggrid; PGphase actual measuredcore0',
    PG_guard=dict(pin_half_width_um=pinhalf,clearance_um=clearance,scope='explicit screening scenario; technology/interface rules and actual OBS must confirm'))
  rows.append(dict(slot=slot['n'],original_field_PG_exclusions=fields,repaired_candidate=repaired))
 view=ROOT/'physical/ref_tile/qfd_vm_xcol_roots/views/ot_qfd_vm_xcol_roots';lef=next(view.glob('*.lef'));pins=read(lef)[1];columns={int(c['inst'][3:]):c for c in comp['children']if c['inst'].startswith('u_c')};x0,y0=comp['origin_um'];wallY=die['wall']['y'];bounds=[]
 for root,slot in enumerate(die['slots']):
  distances=[];registers=0
  for col in range(32):
   c=columns[col]
   for k in range(4):
    p=pins[f'q[{4*root+k}]'];x=x0+c['at'][0]+p['x'];y=y0+c['at'][1]+p['y'];distance=max(slot['x']-x,0,x-slot['x']-slot['w'])+abs(y-wallY)
    hops=math.ceil(distance/500);registers+=max(0,hops-1);distances.append(distance)
  maxhop=math.ceil(max(distances)/500)
  bounds.append(dict(root=root,minimum_bit_distance_sum_um=round(sum(distances),4),max_optimistic_path_um=round(max(distances),4),
    min_unbuffered_wire_hops_500=maxhop,minimum_intermediate_register_bits_unbalanced=registers,
    minimum_intermediate_register_bits_if_same_source_edge_and_equalized_root=128*max(0,maxhop-1)))
 unbalanced=sum(r['minimum_intermediate_register_bits_unbalanced']for r in bounds);balanced=sum(r['minimum_intermediate_register_bits_if_same_source_edge_and_equalized_root']for r in bounds)
 out=dict(schema='opentallas.qwen.vm-root-PG-export-capacity-scenario.v1',qualification=False,assigned=False,native_ABI_adopted=False,
  source_die_commit='8e043d021',source_inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (rf,gf,lef)},
  source_point_view='eeb5c1dc5 pointroot diagnostic only; routed snapshot stillpending',
  original_M8_M9_center_PG_collisions=len(allhits),original_N_M9_center_PG_collisions=sum(h['face']=='N'and h['layer']=='M9'for h in allhits),all_original_PG_exclusions=allhits,slots=rows,
  repaired_candidate_layer_budget=dict(M9_response=233,M9_request=109,M7_instruction=380,scope='literal96key+phase8 conditional scenario; full context/version/fill-fire/epoch dictionary or reset-drain proof absent'),
  VM_transport_lower_bound=dict(source_data_bits=4096,reach_um=500,scope='Optimistic data-only rectangle-to-VM Sface bound; tags/control/pairreach/endpointbuffer FF, obstacles and actualpins excluded',root_bounds=bounds,
   minimum_data_register_bits_unbalanced=unbalanced,minimum_P2_tiles_by_FF_count=math.ceil(unbalanced/960),
   data_register_bits_equalized_per_root_same_launch_edge=balanced,minimum_P2_tiles_by_equalized_FF_count=math.ceil(balanced/960),
   chosen_band_slot_pressure=dict(spares=114,XPR14_raw_added_band_tile_lower_bound=69,control_station_candidate_slots=32,remaining_slots=13,
    conclusion='Chosen69+32 candidate leaves13slots, below even optimistic data-only transportFFcount lowerbound. NewVMownedregionaltransport slots orchangedband/control/equalization contract needed; not a global impossibility proof.')),
  external_escape_OBS_correction=dict(source='qwen_die lead004717381/windowaudit actualg8elements.lef',surrounding_frame_OBS='M1-M7; M8/M9escape potentiallyavailable, VMwallM1-M9stillforbidsdie traffic',M6_metadata105='No freeM6canopy overcurrentM7frames. CandidateM6face needs explicitclearchannel oractuallyrecappednativeview.',M7_instruction380='Pinfacecandidate only; localPG/OBS/upperlayer transition/channel proofpending'),
  required_checks=['All26externalrelay collisions replanned; actualmaster functionalcensus/CTS/nativeABI.','M7 localPG/regionOBS, N/Sface availability, actualroutinggridphase andpinshape/spacingrule.','VM-owned registered horizontalgather+verticalexport, truepairreach/SSwire/hold/equalization costs.','load_step independentof core_step; heldq_v consumedexactlyonce viafill-fire/token.','Actual fullcombinedroot+lane+control cut andend-to-end cost.'])
 (A/'vm_band_export_capacity_codex.json').write_text(json.dumps(out,indent=1)+'\n');print(dict(PG_center_collisions=len(allhits),all32repaired_M9_complete=all(r['repaired_candidate']['M9_response_request_complete']for r in rows),minimum_dataFF=unbalanced,minP2tiles=math.ceil(unbalanced/960),equalizedFF=balanced,equalizedP2=math.ceil(balanced/960)))
if __name__=='__main__':main()
