"""Price a uniform four-input/two-output C4 transport candidate from the real mapped interface."""
import argparse,json,hashlib
from pathlib import Path

def run(mapped,inventory,placement,out):
 d=json.loads(mapped.read_text())['modules']['qkd_kvs_emb_rope'];inv=json.loads(inventory.read_text());geometry=json.loads(placement.read_text())
 used=set()
 for c in d['cells'].values():
  typ=c['type'];pins=c.get('connections',{})
  if not pins:continue
  outputs={'rd_out'} if typ.startswith('ot_sram_') else {'QN'} if typ.startswith('DFF') else {'Y'}
  assert outputs<=set(pins),(typ,outputs,list(pins))
  for n,bits in pins.items():
   if n not in outputs:used.update(b for b in bits if isinstance(b,int))
 for p in d['ports'].values():
  if p['direction']=='output':used.update(b for b in p['bits'] if isinstance(b,int))
 inputs={n:dict(declared_bits=len(p['bits']),used_bits=sum(isinstance(b,int) and b in used for b in p['bits'])) for n,p in d['ports'].items() if p['direction']=='input' and n not in ['ck','rst_n']}
 outputs={n:dict(declared_bits=len(p['bits']),nonconstant_bits=sum(isinstance(b,int) for b in p['bits'])) for n,p in d['ports'].items() if p['direction']=='output'}
 raw_i=sum(p['declared_bits'] for p in inputs.values());used_i=sum(p['used_bits'] for p in inputs.values());raw_o=sum(p['declared_bits'] for p in outputs.values());used_o=sum(p['nonconstant_bits'] for p in outputs.values())
 ff=4*used_i+2*used_o;rawff=4*raw_i+2*raw_o
 result=dict(schema='opentallas.qwen-kv-context-transport-candidate.v1',state='ANALYTICAL_ONLY_NOT_BUILD_READY',opt_in_default=False,selected=False,hardware_implemented=False,
 source_mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),input_ports=inputs,output_ports=outputs,
 input_stages=4,output_stages=2,added_component_latency_cycles=6,added_component_latency_ps=6*833,
 raw_input_bits_per_cycle=raw_i,used_input_bits_per_cycle=used_i,output_bits_per_cycle=raw_o,nonconstant_output_bits_per_cycle=used_o,
 transport_FF_declared_upper=rawff,transport_FF_observed_used_bits_floor=ff,
 output_bank_policy='keep distinct physical output banks; do not share aliased px_tok/px_tep with service seam bits across different faces',
 transport_data_FF_area_floor_um2=ff*.2916,transport_FF_CLK_cap_TT_floor_fF=ff*.474736,
 epoch_control_FF_logical=6,epoch_control_FF_candidate=len(inputs)*4+len(outputs)*2,epoch_control_FF_area_floor_um2=(len(inputs)*4+len(outputs)*2)*.37908,
 source_component_mapped_FF=inv['rows']['context']['FF'],source_component_logic_area_um2=inv['rows']['context']['mapped_cell_area_um2'],macro_count=2,macro_memory_bytes_per_cycle_each=dict(read=64,write=64),
 compute=dict(macs_per_cycle=0,added_rounding_points=0),replicas=1,mux_demux_added=0,throughput=dict(pipe_items_per_cycle=1,component_demonstrated_request_spacing_cycles=1270,new_composed_request_spacing_qualified=False),
 source_dates=dict(first_header=1193,first_rope=1258,last_packet=1265),candidate_dates=dict(first_header=1199,first_rope=1264,last_packet=1271),
 physical_service_boundary=dict(existing_cycles=2,with_wrapper_cycles_from_original_inputs=8,bits_per_cycle=174,extra_epoch_bits=1),
 placement_scope=dict(producer_geometry=geometry['status'],internal_direct_max_um=geometry['macro_to_logic_all_corners_Manhattan_max_um'],transport_stage_sites_unplaced=True),
 admission=dict(measured_prior_component='oth-ubuntu-986963-1794903354, Verilator -j2 PASS; new simulator measured CPU/RAM not yet available',next_vehicle='actual same production component plus opt-in uniform-delay wrapper and latency-aligned lockstep; port-delay bypass mutant must fail',CPU_threads=2,RAM_GB=None,capacity_policy='derive from retained prior ot-heavy peak/admission before launch; no guessed protective limit or wall-time cap'),
 open_requirements=['Four input stages must delay every used input including the slot/CTL/config/host-context and passthrough-service bits consistently.',
 'Place per-port transport registers on actual source-to-consumer paths, including shared valid/epoch with payload; four stages only establish capacity for five <=380um hops, not obstacle-aware reach.',
 'Determine reset assertion/release treatment explicitly and prove complete reset epochs; a uniform delay does not authorize silently changing reset behavior.',
 'Global calendar and QC word-provider lifetime must consume the +6-cycle delivery event before source adoption.',
 'Per-tap new sink inventory,44per-portbankepochFF realization and TT/FF/route qualification remain open.'])
 assert (raw_i,used_i,raw_o,used_o,rawff,ff)==(1996,1507,758,747,9500,7522),(raw_i,used_i,raw_o,used_o,rawff,ff)
 macro_area=171.288*77.784;epoch=len(inputs)*4+len(outputs)*2
 result['area_accounting']=dict(source_baseline_logic_um2=inv['rows']['baseline']['mapped_cell_area_um2'],source_baseline_macro_count=1,source_candidate_logic_um2=inv['rows']['context']['mapped_cell_area_um2'],source_candidate_macro_count=2,each_macro_body_LEF_um2=macro_area,source_baseline_total_floor_um2=inv['rows']['baseline']['mapped_cell_area_um2']+macro_area,source_candidate_total_floor_um2=inv['rows']['context']['mapped_cell_area_um2']+2*macro_area,additional_transport_data_FF_floor_um2=ff*.2916,additional_transport_epoch_FF_floor_um2=epoch*.37908,additional_service_boundary350FF_floor_um2=102.23496,total_composed_candidate_floor_um2=inv['rows']['context']['mapped_cell_area_um2']+2*macro_area+ff*.2916+epoch*.37908+102.23496,total_candidate_minus_baseline_floor_um2=inv['rows']['context']['mapped_cell_area_um2']-inv['rows']['baseline']['mapped_cell_area_um2']+macro_area+ff*.2916+epoch*.37908+102.23496,unpriced='CTS,hold,signalbuffers andwire/PDN channels; floor values are not placed silicon utilization')
 result['FF_accounting']=dict(source_baseline=inv['rows']['baseline']['FF'],source_candidate=inv['rows']['context']['FF'],transport_data=ff,transport_epoch_candidate=epoch,service_boundary=350,total_composed_candidate=inv['rows']['context']['FF']+ff+epoch+350,total_candidate_minus_baseline=inv['rows']['context']['FF']+ff+epoch+350-inv['rows']['baseline']['FF'])
 result['clock_accounting_TT_fF']=dict(source_baseline=inv['rows']['baseline']['FF_CLK_cap_fF']+9.3458,source_candidate=inv['rows']['context']['FF_CLK_cap_fF']+2*9.3458,transport_data=ff*.474736,transport_epoch_candidate=epoch*.462899,service_boundary=166.133926,total_composed_candidate=inv['rows']['context']['FF_CLK_cap_fF']+2*9.3458+ff*.474736+epoch*.462899+166.133926,total_candidate_minus_baseline=inv['delta']['FF_CLK_cap_fF']+9.3458+ff*.474736+epoch*.462899+166.133926)
 result['internal_pin_cone_placement']='R0-only successor; direct allcorners518.4 retained, actual mappedD/Q cone site candidate separately required; no internal extra cycle assumed ready'
 out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:result[k] for k in ['state','used_input_bits_per_cycle','nonconstant_output_bits_per_cycle','transport_FF_observed_used_bits_floor','transport_data_FF_area_floor_um2','candidate_dates']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mapped',type=Path,required=True);a.add_argument('--inventory',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();run(p.mapped,p.inventory,p.placement,p.out)
