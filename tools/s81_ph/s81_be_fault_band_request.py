#!/usr/bin/env python3
"""Real-pin N10 fault route request with whole-macro FE repack and layer tracks."""
import hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=R/'results/arch/s81_be_fault_corridor_1014'
def main():
 fe=json.loads((B/'inputs/fe_candidate_s9.json').read_text())['instances']
 trace=json.loads((B/'inputs/trace.json').read_text())
 pins=json.loads((B/'inputs/f16_actual_pins.json').read_text())
 def right(x,b):return round(math.ceil((x+32.4+3.456-.060)/.096)*.096+.060+.096*b,6)
 def left(x,b):return round(math.floor((x-3.456-.060)/.096)*.096+.060-.096*b,6)
 places=[(600,3517.776),(200,3517.776)]+[(20,y) for y in [3300,2880,2460,2040,1620,1200,780,360]]
 def contact(i,b,output=False):
  rect=pins['pins'][('o' if output else 'i')+f'[{b}]']['rects'][0]
  return [round(places[i][0]+(rect[1]+rect[3])/2,6),round(places[i][1]+(rect[2]+rect[4])/2,6)]
 repacked={k:dict(v,x=v['x']+108,y=v['y']+3121.2+(54 if v['y']+v['h']>384 else 0)) for k,v in fe.items()}
 cells={f'fault{i}':dict(x=x,y=y,w=32.4,h=32.4) for i,(x,y) in enumerate(places)}
 outlines={**repacked,**cells,'BE0':dict(x=151.152,y=21.6,w=302.4,h=92.88)}
 overlap=[];clearance=[]
 def overlap_rect(a,b,gx=0,gy=0):return min(a['x']+a['w']+gx,b['x']+b['w'])>max(a['x']-gx,b['x'])+1e-7 and min(a['y']+a['h']+gy,b['y']+b['h'])>max(a['y']-gy,b['y'])+1e-7
 for k,a in repacked.items():
  for l,b in repacked.items():
   if k<l and overlap_rect(a,b):overlap.append([k,l])
 for k,a in cells.items():
  for l,b in repacked.items():
   if overlap_rect(a,b,20,10.8):clearance.append([k,l])
 pairs=[];blocked=[];tracks=[]
 def crossed(a,z,r):
  if abs(a[1]-z[1])<1e-7:return r['y']+1e-7<a[1]<r['y']+r['h']-1e-7 and max(min(a[0],z[0]),r['x'])<min(max(a[0],z[0]),r['x']+r['w'])-1e-7
  assert abs(a[0]-z[0])<1e-7
  return r['x']+1e-7<a[0]<r['x']+r['w']-1e-7 and max(min(a[1],z[1]),r['y'])<min(max(a[1],z[1]),r['y']+r['h'])-1e-7
 for item in trace['pairs']:
  b=item['bit'];src=item['unadopted_s9_cts_source_um'].copy();src[0]+=86.4;src[1]+=54
  dst=item['requested_sink_contact_um'].copy();dst[0]+=86.4
  for seg in range(11):
   a=src if seg==0 else contact(seg-1,b,True);z=dst if seg==10 else contact(seg,b)
   if seg==0:
    y=3557.100+.096*b;x=left(600,b)
    path=[a,[a[0],y],[x,y],[x,z[1]],z]
   elif seg in (1,2):
    x=right(places[seg-1][0],b);xx=left(places[seg][0],b)
    y=(3553.644 if seg==1 else 3551.724)+.096*b
    path=[a,[x,a[1]],[x,y],[xx,y],[xx,z[1]],z]
   elif seg<10:
    x=right(20,b);xx=left(20,b);y=places[seg][1]+35.868+.096*b
    path=[a,[x,a[1]],[x,y],[xx,y],[xx,z[1]],z]
   else:
    x=right(20,b);path=[a,[x,a[1]],[x,z[1]],z]
   nsource='fcn' if seg==0 else f'fault{seg-1}';ntarget='BE0' if seg==10 else f'fault{seg}'
   for j,(u,v) in enumerate(zip(path,path[1:])):
    layer='M4' if abs(u[1]-v[1])<1e-7 else 'M5'
    # Producer CTS contact is unqualified. Internal requested tracks are exact;
    # source-pin track/egress legality remains an independent prerequisite.
    if not(seg==0 and j==0):
     coord=(12804.48+u[1]-.012)/.048 if layer=='M4' else (14036.112+u[0]-.012)/.096
     if abs(coord-round(coord))>1e-6:tracks.append(dict(bit=b,segment=seg,edge=j,layer=layer))
    for name,r in outlines.items():
     if name==nsource and j==0 or name==ntarget and j==len(path)-2:continue
     if crossed(u,v,r):blocked.append(dict(bit=b,segment=seg,edge=j,macro=name))
   length=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(path,path[1:]))
   pairs.append(dict(bit=b,segment=seg,route_VM_um=path,route_layers=['M4' if abs(u[1]-v[1])<1e-7 else 'M5' for u,v in zip(path,path[1:])],requested_route_length_um=round(length,6),actual_routed_length_um=None,actual_clock_sources=None,actual_source_R_phase_RC=None,actual_capture_R_phase_RC=None,setup_available_ps=None,hold_available_ps=None,maximum_timing_length_um=None,physical_qualified=False))
 maximum=max(p['requested_route_length_um'] for p in pairs)
 good=not(overlap or clearance or blocked or tracks) and maximum<=500
 record=dict(schema='opentallas.be_fault_band_request.v1',status='N10_UNALLOCATED_LAYERED_ROUTE_REQUEST',optional_RTL_source='ae28133e8',master_view_commit='9375370dc',master_LEF_sha256=pins['lef_sha256'],input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'inputs').iterdir()},cells=[dict(instance=f'u_be.g_fault.g_stage[{i}].u_r',master='dsfd_be_f16',origin_VM_um=list(xy),actual_parent_placement=None) for i,xy in enumerate(places)],FE_whole_outline_repack=repacked,FE_repack_overlaps=overlap,relay_FE_channel_violations=clearance,requested_route_macro_crossings=blocked,internal_requested_track_violations=tracks,producer_pin_contact_qualified=False,producer_pin_global_track_binding=None,pairs=pairs,requested_segments=len(pairs),maximum_requested_route_length_um=maximum,added_data_FF=160,fault_status_serial_cycles_added=10,hot_data_return_cycles_added=0,additional_reset_distribution_FF=None,additional_consumer_ACK_FF=None,root_141_ACK_282_FF_covers_new_consumers=False,slot_request=dict(previous_VM_um=[1887.384,4013.256],requested_VM_um=[1973.784,4067.256],delta_width_um=86.4,delta_height_um=54,west_corridor_um=86.4,existing_VM_children_shift_x_um=86.4,FE_height_um=943.92,FE_cut_local_y_um=384,FE_rule='move whole every macro with top>384 up54; no child outline cut or scaled',BE_height_um=196.56,BE_original_54_ownstate_origin_y_phase_debt_retained=True,allocator_lattice_acceptance=None,adopted=False),cut_receipt=dict(scope='only added bundles, not complete parent cuts',outer_corridor_horizontal_cut_bits=16,outer_corridor_available_width_um=20,vertical_M5_pitch_um=.096,outer_corridor_utilization=16/(20/.096),FE_horizontal_channel_bits_upper_bound=48,FE_available_height_um=13.824,horizontal_M4_pitch_um=.048,FE_channel_utilization=48/(13.824/.048),limit=.6,full_parent_cut_proof=False),missing=['actual qualified FCN/FE pin/master/clock binding','actual parent pin access/wired routes/SPEF','full-parent changed FE seams/cuts','new synchronous rn reset driver/distribution/latency semantics','new reset-consumer ACK census/collector','actual source-clock per-corner phase/R/slew and pair budgets','allocator origin/grid/source-slot admission'],requested_obstacle_geometry_pass=good,actual_parent_closed=False,old_CLOSED_replaced=False)
 (B/'band10_request.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(pass_=good,maximum_um=maximum,blocked=len(blocked),tracks=len(tracks),clearance=len(clearance),FE_overlaps=len(overlap))))
 if not good:raise SystemExit(1)
if __name__=='__main__':main()
