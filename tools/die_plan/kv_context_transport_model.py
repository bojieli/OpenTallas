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
 epoch_control_FF_candidate=6,epoch_control_FF_area_floor_um2=6*.37908,
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
 'Per-tap new sink inventory,6controlFF realization and TT/FF/route qualification remain open.'])
 assert (raw_i,used_i,raw_o,used_o,rawff,ff)==(1996,1507,758,747,9500,7522),(raw_i,used_i,raw_o,used_o,rawff,ff)
 out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:result[k] for k in ['state','used_input_bits_per_cycle','nonconstant_output_bits_per_cycle','transport_FF_observed_used_bits_floor','transport_data_FF_area_floor_um2','candidate_dates']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mapped',type=Path,required=True);a.add_argument('--inventory',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();run(p.mapped,p.inventory,p.placement,p.out)
