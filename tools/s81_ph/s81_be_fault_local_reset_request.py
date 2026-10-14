#!/usr/bin/env python3
"""Actual CLOSED contact local raw-epoch conditioner placement request, never adoption."""
import json,hashlib,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/hier_contract'));import child_lint as C
B=R/'results/arch/s81_be_fault_corridor_1014'
def main():
 base=json.loads((B/'band10_request.json').read_text());p=R/'results/arch/s81_be_external_inventory_1014/closed_views/dsfd_die_rstsync_dsfd_die_rstsync.lef';rst=C.parse_lef(p.read_text());fp=C.parse_lef((B/'closed_f16/dsfd_be_f16.lef').read_text());cells=[];pairs=[];bad=[]
 data=[c['origin_VM_um'] for c in base['cells']]
 resets=[[x+52.4,y] if i<2 else [x,y+43.2] for i,(x,y) in enumerate(data)]
 outlines=dict(base['FE_whole_outline_repack']);outlines.update({f'data{i}':dict(x=x,y=y,w=32.4,h=32.4) for i,(x,y) in enumerate(data)});outlines.update({f'reset{i}':dict(x=x,y=y,w=32.4,h=32.4) for i,(x,y) in enumerate(resets)})
 for i,(x,y) in enumerate(resets):
  for name,o in outlines.items():
   if name==f'reset{i}':continue
   if min(x+32.4+20,o['x']+o['w'])>max(x-20,o['x'])+1e-6 and min(y+32.4+10.8,o['y']+o['h'])>max(y-10.8,o['y'])+1e-6:bad.append(dict(stage=i,macro=name,reason='W/E20_N/S10.8_channel'))
 def point(origin,model,name):
  r=model['pins'][name]['rects'][0];return [round(origin[0]+(r[1]+r[3])/2,6),round(origin[1]+(r[2]+r[4])/2,6)]
 def crosses(a,z,r):
  if abs(a[1]-z[1])<1e-6:return r['y']+1e-6<a[1]<r['y']+r['h']-1e-6 and max(min(a[0],z[0]),r['x'])<min(max(a[0],z[0]),r['x']+r['w'])-1e-6
  return r['x']+1e-6<a[0]<r['x']+r['w']-1e-6 and max(min(a[1],z[1]),r['y'])<min(max(a[1],z[1]),r['y']+r['h'])-1e-6
 for i,(xy,rx) in enumerate(zip(data,resets)):
  source=point(rx,rst,'rn');target=point(xy,fp,'rn');right=round(math.ceil((rx[0]+32.4+3.456-.060)/.096)*.096+.060+17*.096,6);left=round(math.floor((xy[0]-3.456-.060)/.096)*.096+.060-17*.096,6);y=round(xy[1]+38.316,6);route=[source,[right,source[1]],[right,y],[left,y],[left,target[1]],target]
  layers=[]
  for j,(a,z) in enumerate(zip(route,route[1:])):
   layer='M4' if abs(a[1]-z[1])<1e-6 else 'M5';layers.append(layer);phase=(12804.48+a[1]-.012)/.048 if layer=='M4' else (14036.112+a[0]-.012)/.096
   if abs(phase-round(phase))>1e-6:bad.append(dict(stage=i,edge=j,reason='track'))
   for name,o in outlines.items():
    if name==f'reset{i}' and j==0 or name==f'data{i}' and j==4:continue
    if crosses(a,z,o):bad.append(dict(stage=i,edge=j,macro=name,reason='macro_interior'))
  length=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(route,route[1:]));assert length<=500
  cells.append(dict(instance=f'u_be.u_fault_path.g_stage[{i}].g_local.u_rs',master='dsfd_die_rstsync',CLOSED_commit='626202850',origin_VM_um=rx,actual_placement=None,logical_clock='parent clk serial',raw_rst_input='parent raw rst[0]',raw_rst_physical_driver_pin=None,actual_launch_reference_clock=None,ACK_output=f'u_be.fault_conditioner_ack[{i}]',controller_capture_clock=None,controller_capture_pin=None))
  pairs.append(dict(stage=i,source_master='dsfd_die_rstsync',source_pin='rn',source_contact=source,destination_master='dsfd_be_f16',destination_pin='rn',destination_contact=target,route_VM_um=route,layers=layers,requested_length_um=round(length,6),actual_routed_length_um=None,actual_launch_capture_clock_R_phase_RC=None,setup_available_ps=None,hold_available_ps=None,registered_pair_limit_um=500,qualified=False))
 req=dict(schema='opentallas.be_fault_local_reset_request.v1',status='REQUESTED_UNALLOCATED_UNROUTED',optional_RTL_source='2e054e8e9',source_CLOSED_LEF_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),data_request='band10_request.json',cells=cells,pairs=pairs,requested_route_violations=bad,geometry_pass=not bad,added_data_consumer_FF=160,added_conditioner_consumer_FF=20,consumer_total_FF=180,consumer_ACK_signals=10,extra_controller_individual_twoFF_capture_FF=20,total_new_consumer_plus_controller_FF=200,controller_capture_structure='individual ordinary two-flop captures before reduction; no shared synchronizer, no conditioner used as collector',raw_reset_stopped_clock_gate='source2e unit positive and common-RN/pre-AND mutants observed; native local gold/TP running',raw_driver_distribution_RC=None,whole_parent_cut_proof=False,allocator_grid_source_slot_binding=None,old_CLOSED_replaced=False,parent_adopted=False)
 (B/'local_reset10_request.json').write_text(json.dumps(req,indent=2)+'\n');print(json.dumps(dict(pass_=not bad,violations=bad,maximum_requested_length_um=max(x['requested_length_um'] for x in pairs))))
 if bad:raise SystemExit(1)
if __name__=='__main__':main()
