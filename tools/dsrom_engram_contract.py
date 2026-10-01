"""Engram metadata/access contract: pinned git objects only, no payload or model execution."""
import ast, hashlib, json, math, subprocess
from pathlib import Path
CENSUS='db83b444c5c8f905e5f3903a605ea52190cc0f5e'
HEAD='b81fca7a3786937f83b53b8a19ecded693147c71'
CAT='25631b8754f4ec295d5d6415ca85e75f38564664'
CP='results/quality/w16_w17_nonexpert_header_census_20261001/census.json'
OUT=Path('results/quality/w16_dsrom_engram_contract_20261001')
def read(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def bank_rows(vocab,layers,ngram,heads,prime):
 seen=set(); result={}
 for L in layers:
  banks=[];off=0
  for order in range(2,ngram+1):
   cur=vocab-1
   for head in range(heads):
    cur+=1
    while not prime(cur) or cur in seen:cur+=1
    seen.add(cur);banks.append(dict(column=len(banks),ngram_order=order,head=head,rows=cur,global_row_offset=off));off+=cur
  result[L]=banks
 return result

def port_budget(rows,row_bytes,width):
 return dict(packed_stream_cycles=math.ceil(rows*row_bytes/width),row_aligned_cycles=rows*math.ceil(row_bytes/width),bytes_per_cycle=width)
def main():
 raw=read(CENSUS,CP); census=json.loads(raw)
 cfgraw=read(CAT,'results/quality/w16_w17_checkpoint_header_catalogue_20261001/config.json');cfg=json.loads(cfgraw)['text_config']
 paths=['tools/hdc_golden_v41.py','tools/hdc_replay_v41.py','tools/rtl_v41_fullshape_layer_campaign.py','tools/uarch_model.py','tools/arch_budget_v41.py','tools/decode_critical_path.py','tools/v41_rack_design.py','tools/v41_die_placement.py','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/hdc/v41/ot_hdc_engram_hash.sv','results/rtl/hdc_v41_engram_rom_plan.json','results/arch/v41_rack.json','results/arch/v41_die_placement.json']
 sources={p:read(HEAD,p) for p in paths}
 tree=ast.parse(sources['tools/hdc_golden_v41.py'])
 prime=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_is_prime')
 ns={};exec(compile(ast.Module(body=[prime],type_ignores=[]),'pinned_prime_metadata','exec'),ns)
 layers=cfg['engram_layer_ids']; cols=(cfg['engram_max_ngram_size']-1)*cfg['engram_n_heads']; width=cfg['engram_head_dim'];D=cfg['hidden_size'];hc=cfg['hc_mult']
 banks=bank_rows(cfg['engram_vocab_size'],layers,cfg['engram_max_ngram_size'],cfg['engram_n_heads'],ns['_is_prime'])
 tensors={k:r for k,r in census['tensors'].items() if r['family']=='Engram'}
 tablebytes=0;constbytes=0;table_contracts={}
 for L in layers:
  prefix=f'layers.{L}.engram.';w=tensors[prefix+'embed.weight'];s=tensors[prefix+'embed.scale'];n=sum(b['rows'] for b in banks[L])
  assert n==w['stored_shape'][0]==s['stored_shape'][0] and w['stored_shape'][1]==width and s['stored_shape'][1]==width//32
  assert w['dtype']=='F8_E4M3' and s['dtype']=='F8_E8M0'
  for b in banks[L]:
   b['packed_backing_bytes']=b['rows']*(width+width//32)
   b['code_file_address_formula']='weight.absolute_file_offsets[0] + (global_row_offset + hash_residue)*256'
   b['scale_file_address_formula']='scale.absolute_file_offsets[0] + (global_row_offset + hash_residue)*8'
  tb=w['stored_bytes']+s['stored_bytes'];tablebytes+=tb
  cb=sum(r['stored_bytes'] for k,r in tensors.items() if k.startswith(prefix) and '.embed.' not in k);constbytes+=cb
  table_contracts[str(L)]=dict(rows=n,table_backing_bytes=tb,projection_and_constants_bytes=cb,column_banks=banks[L],table_logical_copies=1,physical_banks=None,physical_die_owners=None,lookups_per_token=cols,stored_lookup_bytes_per_token=cols*(width+width//32),decoded_BF16_lookup_bytes_per_token=cols*width*2,reference_TP4_image_selected_rows_copies=4,reference_TP4_projection_output_rows_per_rank=(hc+1)*D//4,reference_TP4_q_k_full_copies=4,table_TP4_copies_required=False)
 assert tablebytes+constbytes==203073076240
 rowb=width+width//32;totalrows=cols*len(layers);storage=totalrows*rowb;bf16=totalrows*width*2
 corrected264=dict(beat_bits=264,codes_per_beat=32,scale_bytes_per_beat=1,scale_byte_from_matching_32_column_block=True,beats_per_row=8,cycles_per_layer=cols*8,cycles_both_layers_serial=totalrows*8,cycles_both_layers_with_independent_ports=cols*8,decode_buffer_write_bits=512,qualification='required corrected candidate; no RTL implementation or timing credit')
 ports=port_budget(totalrows,rowb,32)
 for x in (ports,corrected264):
  x['serialization_at_1p2GHz_ns']=x.get('packed_stream_cycles',x.get('cycles_both_layers_serial'))/1.2
 old=json.loads(sources['results/arch/v41_rack.json'])
 result=dict(schema='opentallas.dsrom.engram.lookup-residency-contract.v1',status='PASS_METADATA_DEMAND_PHYSICAL_HOME_UNQUALIFIED',census_commit=CENSUS,census_path=CP,census_sha256=sha(raw),config_commit=CAT,config_sha256=sha(cfgraw),source_commit=HEAD,source_hashes={p:sha(b) for p,b in sources.items()},generator_sha256=sha(Path(__file__).read_bytes()),tensors=tensors,table_contracts=table_contracts,
 address_contract=dict(history_raw_tokens=cfg['engram_max_ngram_size'],compressed_vocab_size=cfg['engram_compressed_vocab_size'],hash='For each order2..4: XOR rolling compressed-token*odd-multiplier; modulo each of8 distinct primes; add column offset',integer_contract='64-bit bounded multiply, XOR, modulo; exact golden ordering',multiplier_recipe='numpy.random.default_rng(10007*layer_id).integers(0,max(1,(INT64_MAX//compressed_vocab_size)//2),size=(4,))*2+1',actual_multipliers=None,token_map_payload_hash=None,token_map_backing_bytes=None,token_map_requirement='compressed_token_map reads tokenizer; mapping must be separately pinned, no tokenizer/payload access here',pad_token_id=cfg['engram_pad_token_id'],prime_partition_matches_actual_header=True,addresses_prefetchable_from_token_start=True),
 demand=dict(total_checkpoint_engram_bytes=tablebytes+constbytes,full_table_backing_bytes=tablebytes,projection_and_constants_bytes=constbytes,lookups_per_layer=cols,lookups_per_token=totalrows,bytes_per_stored_row=rowb,stored_table_read_bytes_per_token=storage,decoded_BF16_rows_bytes_per_token=bf16,table_read_commands_with_fused_codes_and_scales=totalrows,separate_checkpoint_region_reads=2*totalrows,reference_int64_ids_bytes_per_token=totalrows*8,TP4_raw_row_delivery_bytes_if_four_copies=storage*4,TP4_BF16_delivery_bytes_if_four_copies=bf16*4,working_buffers_double_buffer_one_shared_copy_bytes=bf16*2,working_buffers_double_buffer_four_reference_copies_bytes=bf16*2*4,projection_MACs_per_layer=(hc+1)*D*cols*width,keys_and_value_BF16_per_layer_bytes=(hc+1)*D*2),
 residency_candidates=dict(immutable_ROM=dict(table_home='dedicated shared ROM table banks, optional explicit ROM spill',backing_logical_copies=1,backing_bytes_required=tablebytes,HBM_for_tables=False,bank_partition='48 prime regions;24 perlayer; actualdie placement NULL',projection_home='layer-start TP4 output-row slices, reference contract only',physical_capacity_and_word_packing=None,qualification=False),shared_HBM=dict(table_home='shared immutable HBM backing; demand lookup only, no fulltable replication across TP ranks',backing_logical_copies=1,backing_bytes_required=tablebytes,cache_residency=None,table_bandwidth_bytes_per_token=storage,stack_count=None,random_access_latency=None,qualification=False)),
 architecture_coordination=dict(owner='Ram 01a0f697-9c82-7572-8900-dd7b15d59ebf',decision='Compare immutable ROM vs shared HBM candidate; no current physically qualified home',actual24_column_partitions_bound=True,full_allocation_authority='Ram; additive demand only'),
 port_budget=dict(corrected_264bit_row_stream=corrected264,packed_256bit_stream=ports,slack_reference_us=3.57,quarter_slack_ns=892.5,required_bytes_per_cycle_1p2GHz_for_both_layers_quarter_slack=storage/(892.5*1.2),required_memory_bandwidth_Bps_at_user_token_rate='12672 * tokens_per_second',mandatory_decode_scale_bytes=8,SS_FF_port_closure=None,random_row_latency=None,physical_port_count=None),
 critical_path=dict(dependencies=['token/history -> compressed map -> hash -> rows+8scales -> BF16decode -> wkv -> key norm','residual h -> h norm; join(h,key) -> weighted dot -> signed sqrt -> sigmoid -> h+gate*value -> BF16'],prefetchable_branch='lookup, projection and key norm do not depend on residual h',inline_program='ShapeBuilder.engram: gather and wkv inline when engram_inline=True; no prefetch schedule credit',prefetched_candidate_join_delay_formula='max(residual_ready_s, engram_key_ready_s) + exact gate/add dependency cost',extra_wait_formula='max(0, engram_key_ready_s - residual_ready_s)',per_token_total_critical_path_seconds=None,legacy_model_paths=old.get('paths'),legacy_values_are_current_qualification=False,projection_location_conflict='DAG transfers51200B keys/value perlayer; rack transfers6336B rawrow packets perlayer; explicit producer/home/boundary required'),
 mandatory_gaps=['Current gather RTL latches scale onbeat0 and reuses it; actual header+golden requires8distinct scales perrow. Existing scaled-row exactness does not qualify checkpoint decoder.','Physical table home, banking to dies, mapping/multiplier ROM, memory read latency and SS/FF port throughput remain unqualified.','Legacy ROM plan codes_and_scale_257B omits7scale bytes perrow; padded264B total equals actual8scale bytes but byte meaning differs.','Small per-token working set is an access demand, not full immutable backing capacity.','TP4 reference image replication is not proof that four complete tables are required.','Historical rack slack and model on-critical-path verdict need replay after actual codec/home and boundary binding.'],physical_capacity_credit=False,admission_claim=False,adopt=False,payload_reads=0,downloads=0)
 OUT.mkdir(parents=True,exist_ok=True)
 for name,obj in [('contract.json',result),('summary.json',dict(demand=result['demand'],port_budget=result['port_budget'],mandatory_gaps=result['mandatory_gaps']))]:
  (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
 (OUT/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(OUT.glob('*.json'))))
 print(json.dumps(result['demand'],indent=2))
if __name__=='__main__':main()
