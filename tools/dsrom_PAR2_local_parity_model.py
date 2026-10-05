#!/usr/bin/env python3
"""Same PAR2 candidate, storage-only parity replica and finite port screen.
Uses source metadata, no payload or implementation. A conflict screen is not an
engine calendar, synthesized area, routing proof or build admission.
"""
import collections,gzip,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_PAR2_shard_physical_binding_20261002'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):
 b=(BASE/'inputs'/n).read_bytes();return json.loads(gzip.decompress(b) if n.endswith('.gz') else b)
def address(provider,linear_bit):
 if not 0<=linear_bit<provider['bits']:raise ValueError('sidecar outside source allocation')
 word,bit=divmod(linear_bit,256);pair_index,local=divmod(word,16384);mb,a=divmod(local,8192)
 return provider['pairs'][pair_index],mb,a%2,a//2,bit

def service_batch(provider,requests):
 """One finite batch. Coalesce exact same leaf/row; each leaf reads once/round.
 No queue growth or second accepted batch before all terminal retirements.
 Input is (ownerpair, linear_bit) for its two8bit codeword sidecars.
 """
 if len(requests)>128 or len({x[0] for x in requests})!=len(requests):raise ValueError('finite128 pair seats')
 banks=collections.defaultdict(set)
 for pair,bit in requests:
  if bit%16:raise ValueError('source two8bit parity must be aligned16')
  a=address(provider,bit);z=address(provider,bit+15)
  if a[:4]!=z[:4]:raise ValueError('unexpected source word straddle')
  banks[a[:3]].add(a[3])
 return max(map(len,banks.values()),default=0),sum(map(len,banks.values()))
def build():
 spec=importlib.util.spec_from_file_location('par2',ROOT/'tools/dsrom_PAR2_shard_physical_binding.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 parent,macros,obs,templates,field,escapes=m.build(1)
 directory=[json.loads(s) for s in gzip.decompress((BASE/'inputs/ECC_directory.jsonl.gz').read_bytes()).splitlines()]
 assert len(directory)==58 and all(len(r['pairs'])==103 and all(p<2048 for p in r['pairs']) for r in directory)
 provider=directory[0];census=read('shard1_parity_intervals.json.gz');calendar=read('capacity_calendar.json')
 assert census['source_records']==46509 and len(census['records'])==46080
 assert calendar['candidate_id']==parent['candidate']
 w,h=templates['ROM']['size_DBU'];halo=parent['geometry']['halo_DBU'];pw,ph=m.snap(w+2*halo),m.snap(h+2*halo);cols=(33000000-2*halo)//pw
 y=m.snap(parent['geometry']['last_field_cfg_return_repair_end_DBU']+2*halo);placed=[];translated=[]
 for index in range(412):
  pi,leaf=divmod(index,4);mb,pp=divmod(leaf,2);x=halo+(index%cols)*pw;z=y+(index//cols)*ph
  row=dict(name=f'candidate.shard1.parity_raw.source_pair{provider["pairs"][pi]}.mb{mb}.pp{pp}',origin_DBU=[x,z],bbox_DBU=[x,z,x+w,z+h],slot_DBU=[x-halo,z-halo,x-halo+pw,z-halo+ph],template='ROM',orientation='R0',source_pair_index=pi,source_stage0_pair=provider['pairs'][pi],mb=mb,PP=pp,source_pairs_all58=[p['pairs'][pi] for p in directory],q_compute_added=False,source_hierarchy_exists=False)
  placed.append(row)
  for shape in templates['ROM']['OBS']:translated.append(dict(instance=row['name'],layer=shape['layer'],bbox_DBU=[shape['bbox_DBU'][0]+x,shape['bbox_DBU'][1]+z,shape['bbox_DBU'][2]+x,shape['bbox_DBU'][3]+z]))
 end=max(r['slot_DBU'][3] for r in placed);assert end<16000000
 body=412*w*h/1e12;slots=412*pw*ph/1e12
 # Explicit conservative state/control allowance using retained FF50 price.
 # Gate bit-equivalents price a construction, never a synthesized netlist.
 seats=128;identity_bits=10+12+10+32+11+13+4+1
 capture_bits=412*(274+12+identity_bits+1)
 request_bits=seats*(identity_bits+544+16+2)
 # local perleaf arbitration128 onehot, request compare/select, two-level
 # 256bit gathering and two272bit SECDED lanes per pair incl sidecar SECDED.
 gate_equiv=412*(128*identity_bits+128*12)+seats*(103*16+3*272*10+544)
 ff_bits=capture_bits+request_bits
 ff50=read('price_terms.json')['declared_return_FF50_proxy']/2/34885504
 logic_allowance=(ff_bits+gate_equiv)*ff50
 total=slots+logic_allowance
 logic_height=m.snap(logic_allowance*1e12/33000000);logic_rect=[0,m.snap(end+2*halo),33000000,m.snap(end+2*halo)+logic_height]
 assert logic_rect[3]<16000000
 spec2=importlib.util.spec_from_file_location('disjoint_helpers',BASE/'inputs/parent_shapes_tool.py');helpers=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(helpers)
 helpers.disjoint([(r['name'],r['bbox_DBU']) for r in macros]+[(r['name'],r['slot_DBU']) for r in placed]+[('PARITY_GATHER_DECODE_CONTROL',logic_rect)])
 actual_rounding=33*logic_height/1e6-logic_allowance
 total+=actual_rounding
 witness=census['worst_first_address_witness'];rounds,words=service_batch(provider,witness['requests_pair_linearbit'])
 assert rounds==witness['distinct_rows']==64
 maxeligible=max(r['eligible_leaf_distinct_pair_upper'] for r in census['records']);assert maxeligible==128
 result=dict(schema='opentallas.dsrom.PAR2.local-raw-parity.v1',candidate=parent['candidate'],applicability={'DeepSeek_ROM':'Same PAR2 candidate analytical preparation only.','Qwen_ROM':'No transfer; different source inventory.','DeepSeek_HBM':'No ROM parity novelty or cost transfer.','Qwen_HBM':'No ROM parity novelty or cost transfer.'},variant='LOCAL_RAW_PARITY_SHARD1_SAME_PACKING',parent_model_sha256=digest(BASE/'model.json'),generator_sha256=digest(Path(__file__)),source_receipt_sha256=digest(BASE/'input_receipt.json'),source_capacity_calendar_commit='1679182779f2b5fd748f7152dc930cc45a0b5c07',
  conservation=dict(original_shard0_storage_retained=True,full_all58_replica=True,replica_useful_capacity_bits=412*4096*256,replica_gross_bits=412*4096*274,source_allocated_parity_bits_by_stage={str(p['stage']):p['bits'] for p in directory},leaves=412,total_added_leaves_all58_TP4_shard1=412*58*4,no_adjacent_q_BF_compute_added=True,no_NP_depth_stage_or_reduction_change=True),
  geometry=dict(raw_body_mm2=body,halo_grid_mm2=slots,logic_rectangle_DBU=logic_rect,last_y_DBU=logic_rect[3],parity_OBS_artifact='local_parity_OBS.json.gz',pin_shapes=412*len(templates['ROM']['pins']),pin_templates='macro_templates.json',layout_artifact='local_parity_placement.json.gz',parent_service_band_unchanged=True,actual_parent_PG_via_clock_exclusions_bound=False,raw_bodies_halos_logic_disjoint_from_parent_macros=True),
  area=dict(state_bits=ff_bits,control_gate_bit_equivalents=gate_equiv,retained_FF50_mm2_per_bit=ff50,logic_allowance_mm2=logic_allowance,logic_rectangle_rounding_mm2=actual_rounding,full_added_debit_mm2=total,against_original163_screen_remaining_mm2=parent['area']['original_extra_budget_mm2']-total,against_clearance_priced_screen_remaining_mm2=parent['area']['remaining_for_positive_endpoints_exclusions_mm2']-total,screen_with_variant_mm2=parent['area']['revised_conservative_screen_mm2']+total,logic_is_explicit_conservative_construction_allowance_not_synthesis=True,no_residual418_or47_credit=True,fit_certified=False),
  ports=dict(each_leaf={'clk':1,'ce_in':1,'addr_in':12,'rd_out':274,'read_ports':1},peak_local_raw_macro_return_bits_per_cycle=412*274,useful_parity_delivery_bits_per_active_pair=16,worst_pair_consumers=128,worst_useful_delivery_bits_per_cycle=2048,independent_leaf_commands_bits_per_cycle=412*13,aligned_16bit_gather_has_no_256bit_word_straddle=True,raw_word_SECDED_payload256_check10=True,weight_code_scale_payload272_check10='2inline+8sidecar each codeword; two codewords per pair. Must terminal before arithmetic.',address_formula=census['formula'],address_translation='divmod(linear_bit,256); divmod(word,16384) -> sidecar pair; divmod(localword,8192) -> mb; pp=a%2,row=a//2; keep global owner/phase/word/reset generation.'),
  finite_service=dict(source_FP4_matrices=len(census['records']),all_source_records=census['source_records'],source_metadata_only=True,maximum_eligible_pair_requests_per_single_leaf=maxeligible,first_address_batch_witness=witness,witness_single_leaf_read_rounds=rounds,witness_unique_reads=words,actual_simultaneous_engine_issue_proven=False,one_port_per_leaf=True,coalesce_only_identical_leaf_row=True,acceptance_rule='One batch of at most128 pair requests; freeze accepted identities; no next batch until all ECC terminal+ordered consumer ACK retire. Round robin one unique row perleaf perround; broadcast only matching row identities.',request_seats=128,macro_capture_seats=412,per_batch_read_round_upper=128,per_batch_conditional_issue_II_cycles=128,additional_latency='Macro SS cq743.963ps plus capture/setup/wire, sidecar SECDED, gather, weight ECC terminal and visible ACK. No cycles assigned until decoder/capture timing binds; 128 read rounds is a service bound conditional on stallable source, not total latency.',source_unbackpressured_engine_cannot_use_this_contract_without_owned_accept_ready_adapter=True,actual_epoch_fault_drain_required=True,remote_2048bit_cycle_dependency_removed_only_after_local_ECC_terminal=True,conflict_free_one_cycle_service=False,per_user_token_delta_not_yet_admitted=True),
  routing=dict(no_collector_track_debit_transfer=True,command_address_fanout='412 distinct12bit addresses+CE; raw read112888bits/cycle is distributed, not a single freebus.',gather='16bits*128 terminal lanes; source incidence map required for physical cut loads; retain allcodeword identities.',macro_CLK_added_cap_fF=412*read('ROM_timing.json')['timing']['ss']['clk_cap_ff'],local_raw_shoreline_pin_OBS_translated=True,pin_escape_PG_via_and_decoder_routes_not_qualified=True),
  decision='RAW_REPLICA_CAPACITY_AND_AREA_ALLOWANCE_PASS_SAME_PACKING_FINITE_CONFLICT_SCREEN_FAILS_ONE_CYCLE_ASSUMPTION',minimum_next_source_repair=['Owner exporter must produce real paired codeword+sidecar addresses and opt-in accept-ready/arithmetic ECC terminal fence; current ports absent.','Preserve exact parity values while binding128 seats,412 captures and source-owned SECDED decoders; bound capture/decode/visible latency and consumer deadlines.','Place named gather/decoder/controller instances within explicit allowance; bind pin escape/PG/vias/CTS and incidence routing before G0.'],physical_GO=False,new_engine_RTL_compile_PR_jobs=0)
 return result,placed,translated

def main():
 result,placed,obs=build()
 for name,obj in [('local_parity_model.json',result),('local_parity_placement.json.gz',placed),('local_parity_OBS.json.gz',obs)]:
  data=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();data=gzip.compress(data,mtime=0) if name.endswith('.gz') else data
  p=BASE/name
  if p.exists() and p.read_bytes()!=data:raise ValueError('immutable output changed '+name)
  p.write_bytes(data)
 print(json.dumps(result['area'],sort_keys=True))
if __name__=='__main__':main()
