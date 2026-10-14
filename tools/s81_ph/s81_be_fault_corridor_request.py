#!/usr/bin/env python3
"""Check a data-only, unallocated nine-stage FE fault corridor request."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=R/'results/arch/s81_be_fault_corridor_1014'
def main():
 t=json.loads((B/'inputs/trace.json').read_text())
 fe=json.loads((B/'inputs/fe_candidate_s9.json').read_text())
 actual=json.loads((B/'inputs/f16_actual_pins.json').read_text())
 # Actual CLOSED leaf contacts are retained in an unallocated parent request.
 stages=[(545.6,3196.8)]+[(473.6,y) for y in [2830.032,2410.032,1990.032,1570.032,1150.032,730.032,360]]+[(220,204.144)]
 cells=[dict(instance=f'u_be.g_fault.g_stage[{i}].u_r',master='dsfd_be_f16',origin_VM_um=list(xy),outline_um=[32.4,32.4],bits=16,actual_LEF_sha256=actual['lef_sha256'],actual_view_commit='9375370dc',actual_parent_placement=None) for i,xy in enumerate(stages)]
 def pin(i,b,out=False):
  x,y=stages[i];r=actual['pins'][('o' if out else 'i')+f'[{b}]']['rects'][0];return [x+(r[1]+r[3])/2,y+(r[2]+r[4])/2]
 violations=[]
 # First stage is inside the actual S9 request; all other FE instances retain
 # their positions. Test true full rectangles and both channel clearances.
 x,y=524,32.4
 for name,v in fe['instances'].items():
  if x<v['x']+v['w']+20 and x+32.4>v['x']-20 and y<v['y']+v['h']+10.8 and y+32.4>v['y']-10.8:violations.append(name)
 pairs=[]
 for item in t['pairs']:
  b=item['bit'];src=item['unadopted_s9_cts_source_um'].copy();src[1]+=43.2
  points=[src]+[pin(i,b) for i in range(9)]
  for k in range(10):
   a=src if k==0 else pin(k-1,b,True)
   z=pin(k,b) if k<9 else item['requested_sink_contact_um']
   length=sum(abs(u-v) for u,v in zip(a,z))
   pairs.append(dict(bit=b,segment=k,source_requested_VM_um=a,destination_requested_VM_um=z,Manhattan_route_request_um=round(length,6),source_qualified=False,capture_qualified=False,actual_launch_clock_driver=None,actual_capture_clock_driver=None,actual_source_R_phase_slew=None,actual_capture_R_phase_slew=None,actual_routed_length_um=None,setup_available_ps=None,hold_available_ps=None,maximum_timing_length_um=None))
 maximum=max(p['Manhattan_route_request_um'] for p in pairs)
 # A shortest Manhattan length is not an obstacle-aware route proof. Check the
 # explicit horizontal-then-vertical first-stage path against real S9 outlines.
 obstacles=[]
 for p in pairs:
  if p['segment']!=0:continue
  a,z=p['source_requested_VM_um'],p['destination_requested_VM_um']
  for name,v in fe['instances'].items():
   if name=='fcn':continue # producer egress belongs to its unqualified pin view
   x0,x1=21.6+v['x'],21.6+v['x']+v['w'];y0,y1=3164.4+v['y'],3164.4+v['y']+v['h']
   vertical=x0<z[0]<x1 and max(min(a[1],z[1]),y0)<min(max(a[1],z[1]),y1)
   horizontal=y0<a[1]<y1 and max(min(a[0],z[0]),x0)<min(max(a[0],z[0]),x1)
   if vertical or horizontal:obstacles.append(dict(bit=p['bit'],macro=name,segment=0,requires_detour_or_new_stage=True))
 assert not violations and maximum<=500
 # Vertical seam crosses one 16-bit bundle. 20um full channel at M5 .096
 # pitch gives a geometric-only 16/(20/.096) receipt. It is not a total cut.
 record=dict(schema='opentallas.be_fault_corridor_request.v1',status='UNALLOCATED_UNROUTED_DATA_GEOMETRY_REQUEST',source_trace_epoch='55740b883',optional_RTL_source='73b52f789',enable_parameter='BE_FAULT_STAGES=9; default remains0',inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'inputs').iterdir()},cells=cells,pairs=pairs,added_FF=144,fault_status_cycles_added=9,hot_data_return_cycles_added=0,slot_request=dict(previous_VM_um=[1887.384,4013.256],requested_VM_um=[1952.184,4056.456],delta_width_um=64.8,delta_BE_height_um=43.2,requested_BE_height_um=239.76,requested_BGQ_FE_shift_y_um=43.2,BGQ_column01_seam_um=86.4,BGQ_column01_previous_seam_um=21.6,BGQ_later_columns_shift_x_um=64.8,seam_west_clearance_um=20,seam_east_clearance_um=34,first_stage_FE_local_um=[524,32.4],other_FE_instances_moved=False,placement_allocator_lattice_acceptance=None,manufacturing_grid_um=.001,actual_per_layer_global_contact_grid_acceptance=None,adopted=False),FE_first_stage_rectangle_channel_violations=violations,maximum_requested_data_segment_um=maximum,requested_data_segments=160,Manhattan_request_is_routed_reach_proof=False,FE_first_stage_requested_route_obstacles=obstacles,obstacle_aware_geometry_pass=False,cut_receipt=dict(scope='additional fault bundle only; existing full-parent cuts must be rerun',tracks=20/.096,bits=16,utilization=16/(20/.096),limit=.6,complete_parent_cut_proof=False),clock_reset=dict(serial_clock_R_phase_RC=None,rn_is_synchronous=True,rn_setup_hold_false_path=False,actual_rn_driver=None,actual_rn_routes=None,rn_register_relay_semantics_not_proved=True,additional_reset_consumers=9,additional_ACK_binding=None,root_2fd8_census_covers_new_state=False),required=['fresh N9 native gold/TP and observed mutant','bind actual CLOSED f16 9375370dc contacts/ETMs to requested parent','obstacle-aware FE escape path; extra stages/repack if required','current helper intake','actual FE output master/pin/launchclock binding','full parent all-net cuts and route length','ordinary synchronous rn reset distribution and reset latency proof','new ACK/census coverage','allocator source-slot/grant and global per-layer contact lattice'],requested_contact_grid=dict(layer='M4',pitch_um=.048,offset_um=.012,VM_global_y_requested_um=12804.48,all_y_centers_on_requested_tracks=all(abs(((12804.48+pin(i,b)[1]-.012)/.048)-round((12804.48+pin(i,b)[1]-.012)/.048))<1e-6 for i in range(9) for b in range(16)),actual_LEF_AP_pass=None,allocator_site_lattice_pass=None),partial_requested_data_geometry_pass=True,physical_qualified=False,parent_closed=False)
 (B/'request.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({k:record[k] for k in ['added_FF','maximum_requested_data_segment_um','requested_data_segments','partial_requested_data_geometry_pass','physical_qualified']}))
if __name__=='__main__':main()
