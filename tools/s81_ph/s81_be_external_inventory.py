#!/usr/bin/env python3
"""Actual RTL ownership inventory, with unassigned physical source edges null."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C
import pinreg_audit as P
BASE=ROOT/'results/arch/s81_be_external_inventory_1014'
PLAN=ROOT/'results/arch/s81_be_pinface_successor_1014/selected_Efaces_slot48/parent_geometry_request.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def witness(path,text):
 lines=path.read_text().splitlines();found=[dict(line=i+1,text=s.strip()) for i,s in enumerate(lines) if text in s];assert found,text
 return dict(path=str(path.relative_to(ROOT)),sha256=sha(path),lines=found)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 parent=BASE/'inputs/55740b883_dsfd_sp_vm.sv';bgr=BASE/'inputs/55740b883_dsfd_vm_bgq_sys.sv';ack=BASE/'inputs/5ec865fb2_dsfd_sp_vm.sv'
 text=parent.read_text();assert 'dsfd_vm_bgr #(.NP(NP)' in text;assert '.c_l0r(c_l0r)' in text
 assert 'localparam integer FS = NR - 1' in bgr.read_text();assert 'localparam integer NR = NSTG + 2' in bgr.read_text()
 native=json.loads((BASE/'native207_receipt.json').read_text());assert set(native['VM_pin_manifest']['ports'])=={'f_capture'}
 plan=json.loads(PLAN.read_text());pending=plan['pending_source_pairs'];assert len(pending)==226
 views=json.loads((BASE/'closed_views/provenance.json').read_text());by={v['master']:v for v in views};models={};metrics={}
 for master in ['dsfd_be_r55','dsfd_die_r1','dsfd_die_rstsync']:
  v=by[master];models[master]=C.parse_lef((ROOT/v['paths'][master+'.lef']['snapshot']).read_text());ins=json.loads((ROOT/v['paths']['insertion.json']['snapshot']).read_text());metrics[master]={}
  for corner in ['tt','ss','ff']:
   p=ROOT/v['paths'][master+'_'+corner+'.lib']['snapshot'];lib=P.parse_lib(p);refs=P.clock_refs(lib,ins,corner);metrics[master][corner]=dict(pins=P.pin_metrics(lib,refs),refs=refs,lib_sha256=sha(p))
 cells={c['name']:c for c in plan['cells']};source_witnesses={
 'FE_fault_capture':witness(parent,'else c_fe <= fe_flt'), 'FE_fault_direct_link':witness(parent,'.fe_flt(gs == 0 ? fe_flt'), 'status_capture':witness(parent,'st_r <= st_i'), 'status_chain_head':witness(parent,"assign st[0] = 40'd0"), 'BGR_instance':witness(parent,'dsfd_vm_bgr #(.NP(NP)'), 'forward_selection':witness(parent,'.f_m5(f0d[5*128 +: 92])'),
 'request_FF':witness(bgr,'assign f_v = rb_v[FS]'), 'request_FF_clock':witness(bgr,'always @(posedge clk) begin : p_rb'),
 'ready':witness(parent,'.i(c_l0r[0])'), 'serial_reset':witness(parent,'dsfd_die_rstsync u_rs (.ck(clk), .rst(rst[0])'),
 'stream_reset':witness(parent,'dsfd_die_rstsync u_rss (.ck(cks[0]), .rst(rss[0])')}
 pairs=[];serial=0
 # pending entries are generated in four exact 55-bit blocks, each followed by
 # its shared ready input. No physical source is inferred from the search seed.
 for item in pending:
  kind=item['kind'];net=item['net'];source_clock=None;source_register=None
  if kind=='control_source':
   sl=serial//55;bit=serial%55;serial+=1;inst=f'g_s[{sl}].g_hard.g_ctl[0].u_r';master='dsfd_be_r55';pin=f'i[{bit}]'
   m=re.fullmatch(r'g_h\[0\]\.g_t\[3\]\.u_bg\.(f_(?:d|v|we))\[(\d+)\]',net);assert m
   source_port=f'{m[1]}[{m[2]}]';source_register=f"{ {'f_d':'rb_d','f_v':'rb_v','f_we':'rb_we'}[m[1]] }[5][{m[2]}]";source_clock='ck[0]'
   logical_source=dict(instance='g_h[0].g_t[3].u_bg',master='dsfd_vm_bgr',port=source_port,register=source_register,selected_FS=5,clock_parent_port=source_clock,witnesses=['BGR_instance','forward_selection','request_FF','request_FF_clock'])
  elif kind=='ready_source':
   sl=(serial//55)-1;assert serial%55==0;inst=f'g_s[{sl}].g_hard.u_ready';master='dsfd_die_r1';pin='i'
   logical_source=dict(instance=None,master=None,parent_input='c_l0r[0]',port=None,register=None,clock_parent_port=None,witnesses=['ready'])
  else:
   assert kind=='async_reset_source';stream=net.endswith('rss[0]');inst='g_hrst.u_rss' if stream else 'g_hrst.u_rs';master='dsfd_die_rstsync';pin='rst'
   logical_source=dict(instance=None,master=None,parent_input='rss[0]' if stream else 'rst[0]',port=None,register=None,clock_parent_port=None,driver_reference_clock=None,witnesses=['stream_reset' if stream else 'serial_reset'])
  c=cells[inst];assert c['master'].removesuffix('_m5')==master
  local_rects=models[master]['pins'][pin]['rects'];capture_clock='cks[0]' if c['clock']=='cks' else 'ck[0]'
  sink_metrics={}
  for corner,v in metrics[master].items():
   p=v['pins'].get(pin);sink_metrics[corner]=dict(pin_metrics=p,local_clock_references={k:v['refs'].get(k) for k in p['clk']} if p else {},lib_sha256=v['lib_sha256'],scope='actual CLOSED standalone ETM/local insertion; global capture source/R/phase is unbound')
  pairs.append(dict(pair_id=f'BE_EXTERNAL_{len(pairs):03d}',net=net,kind=kind,RTL_source=logical_source,
   actual_launch=dict(instance=None,master=None,pin=None,view_sha256=None,clock_port=None,clock_source_master=None,clock_source_pin=None,source_phase_per_corner=None,source_R_per_corner=None,source_slew_per_corner=None,xy_global_um=None,driver_reference_clock=None),
   RTL_capture=dict(instance='u_be.'+inst,master=master,pin=pin,clock_pin='ck',parent_clock_port=capture_clock,reset_reference_clock=None),
   actual_capture=dict(instance=None,master=master,pin=pin,leaf_view_commit=by[master]['view_commit'],leaf_LEF_sha256=by[master]['paths'][master+'.lef']['sha256'],leaf_pin_rectangles_um=local_rects,clock_pin='ck',parent_source_clock_master=None,parent_source_clock_pin=None,xy_global_um=None,global_clock_phase_per_corner=None,global_clock_R_per_corner=None),
   unallocated_destination_request=dict(instance='u_be.'+inst,origin_VM_um=[c['x'],c['y']],pin_VM_um=item['destination'],scope='own placement request only; native207 does not bind this actual instance'),
   capture_ETM=sink_metrics,setup_available_ps=None,hold_available_ps=None,actual_routed_length_um=None,maximum_timing_length_um=None,source_geometry_assumed=False,qualified=False,
   missing=['actual launch master/pin/view','native instance/net assignment','actual source clock driver/phase/R/RC','actual parent SPEF/load','actual reset driver reference clock' if kind=='async_reset_source' else 'actual launch ETM']))
 assert serial==220 and len(pairs)==226
 ack_ports=[]
 for sl in range(4):
  for name,clock in [('rst_ack','ck[0]'),('rst_ack_s','cks[0]')]:
   ack_ports.append(dict(RTL_source_instance=f'u_be.g_s[{sl}].u_sl',master='dsfd_vm_be_sl',new_output_port=name,parent_BE_output=f'{name}[{sl}]',RTL_launch_clock=clock,actual_launch_pin=None,actual_view=None,actual_collector_master=None,actual_collector_pin=None,actual_global_clock_source=None,actual_source_phase_R_RC=None,qualified=False))
 ack_candidate=json.loads((BASE/'inputs/5ec865fb2_be_candidate.json').read_text())
 record=dict(schema='opentallas.be_external_source_inventory.v1',status='RTL_OWNERSHIP_BOUND_PHYSICAL_SOURCE_OPEN',selected_parent=dict(epoch='55740b883',top='dsfd_sp_vm_m',configuration=dict(NP=28,NPR=10,NS=4,NT=4,EP=2,ED=3,QD=4,MD=12,DIE_D=6),selected_BGR='flat dsfd_vm_bgr; no MC define',requested_BE_hardening_define='OT_SPVM_BE_HARD_RELAYS',native_parent_source_slot_adopted=False),
 parent_snapshot_sha256={str(p.relative_to(ROOT)):sha(p) for p in [parent,bgr]},RTL_witnesses=source_witnesses,native207=dict(source_receipt='results/arch/s81_be_external_inventory_1014/native207_receipt.json',source_commit=None,SOURCE_SHA_label=native['SOURCE_SHA_label'],contract_sha256=native['contract_sha256'],plan_compressed_sha256=native['plan_compressed_sha256'],assigned_VM_ports=['f_capture'],authoritative_BE_source_or_clock_assignment=False,scope='old dev19 overlay geometry screen; not current native VM/FE/BE assembly'),
 closed_view_receipts=views,closed_view_scope='existing CLOSED views stand; local actual pins/ETMs do not qualify the unallocated parent or new ACK ABI',pairs=pairs,
 clock_inputs=[dict(parent_port=p,actual_source_master=None,actual_source_pin=None,actual_source_view=None,actual_phase_per_corner=None,actual_R_per_corner=None,routed_RC=None,qualified=False) for p in ['ck[0]','cks[0]']],
 collective_clock_reset_request=dict(packet='results/arch/s81_be_external_inventory_1014/inputs/source_clock_reset_packet.json',sha256=sha(BASE/'inputs/source_clock_reset_packet.json'),VM_connection_assigned=False,actual_VM_reset_driver_reference_clock=None,logical_candidate_reset_sampling_domain='refclk; cannot substitute CK/CKS capture clock',physical_PLL_buffer_view=None),
 consumer_ACK_dependency=dict(source_commit='5ec865fb2',enable_macro='OT_SPVM_RESET_ACK',source_sha256=sha(ack),status=ack_candidate['status'],new_leaf_outputs=['rst_ack','rst_ack_s'],added_FF_per_leaf=4,added_FF_all_four=16,actual_ports=ack_ports,old_closed_view_SUPPORTS_ACK=False,current_diagnostic_ACK_enabled=False,current_diagnostic_source='5b6ab0a5b',current_diagnostic_cannot_qualify_ACK=True,controller_individual_sync_or_reduction_binding=None),
 secondary_uncovered_interfaces=dict(FE_fault=dict(bits=16,RTL_source_master='dsfd_vm_fe; hard substitution dsfd_vm_fcn',RTL_source_clock='ck[0]',RTL_sink='u_be.g_s[0].u_sl.c_fe[15:0]',direct_registered_pair=True,existing_r55_chain_carries_fault=False,actual_source_view_pin_position=None,actual_source_clock_phase_R_RC=None,minimum_request_box_distance_um=3064.212,registered_reach_limit_um=500,minimum_relay_stages_lower_bound=6,lower_bound_is_selected_stage_count=False,structural_relay_successor_source='6d85cf313; default off; fresh native proofs pending',physical_qualified=False),status_peer=dict(bits_per_pair=40,pairs=120,slice0_head_constant=True,RTL_source='u_be.g_s[s-1].u_sl.st_o[39:0]',RTL_capture='u_be.g_s[s].u_sl.st_r[39:0], s=1..3',RTL_clock='ck[0]',actual_source_capture_roots=None,per_corner_R_slew_entrywire_spread=None,setup_available_ps=None,hold_available_ps=None,correlated_virtual_peer_credit=False,HOLD_FWD25_eligible=False,physical_qualified=False),bank_return=dict(bits=5188,in_partial_ownstate_cut_inventory=False,physical_qualified=False),partial_inventory_is_complete_parent_coverage=False),
 optional_H2_probe=dict(status='FULL_PARENT_PROBE_SEPARATE_PENDING_EXPANDED_CASES',replacement_master='dsfd_vm_bgq28h_mc24',FORWARD_HOP2=True,roots=24,all_roots_functionally_tied_to_ck=True,physical_source_views_qualified=False,not_selected_flat_ownership=True),
 optional_Bank_ACK_dependency=dict(source_commit='80ec5c5a9',default_off=True,selected_flat_acknowledgements=16,native_candidate_acknowledgements=384,physical_qualified=False),
 summary=dict(external_pairs=226,control=220,ready=4,async_reset=2,unique_control_launch_ports=len({p['RTL_source']['port'] for p in pairs if p['kind']=='control_source'}),physical_launch_assigned=0,qualified_pairs=0,additional_ACK_output_bindings=8),pass_=False)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record['summary'],indent=2))
if __name__=='__main__':main()
