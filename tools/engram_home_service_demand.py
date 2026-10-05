"""Row-aligned home alternatives and retained coefficient source audit; no checkpoint reads/RTL."""
import ast,hashlib,json,math,struct,subprocess
from pathlib import Path
import numpy as np
MODEL='64c6bffe0'
MP='results/quality/w16_w17_whole_dsrom_candidate_20261001/candidate.json'
EC='a9d1fad2835d96e4c0585a150b6a9d484b9791cc'
PIN='821709d3d88772edd88cba5e28039a1295dbc0fc'
OUT=Path('results/quality/w16_engram_home_service_demand_20261001')
def git(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 assert not OUT.exists(),'preserve prior receipts'
 mr=git(MODEL,MP);model=json.loads(mr);er=git(EC,'results/quality/w16_dsrom_engram_contract_20261001/contract.json');ec=json.loads(er)
 sr=git('9b5ca5767','results/quality/w16_engram_eight_scale_binding_20261001/spec.json');spec=json.loads(sr)
 columns=[]
 for L,t in ec['table_contracts'].items():
  for b in t['column_banks']:
   rows=b['rows'];words=rows*8;macros=(words+4095)//4096
   columns.append(dict(layer=int(L),column=b['column'],rows=rows,global_row_offset=b['global_row_offset'],useful264_payload_bytes=rows*264,word_container_bits=274,words=words,macro_rows=4096,macros=macros,capacity_words=macros*4096,padding_words=macros*4096-words,macro_capacity_bits=macros*4096*274,request_residue_bits=24,word_address_bits=27,word_address='residue*8+beat',macro='word_address//4096',macro_row='word_address%4096',bank_die_or_tile=None))
 rows=sum(c['rows'] for c in columns);words=sum(c['words'] for c in columns);macros=sum(c['macros'] for c in columns);bits=sum(c['macro_capacity_bits'] for c in columns)
 assert rows*264==202758032400 and len(columns)==48
 assert all(c['rows']<2**24 and c['words']<2**27 for c in columns)
 assert all((r*8)%4096<=4088 for r in range(512)) # no8wordrow crosses4096macro boundary
 HBM='rtl/hdc/kv/ot_hdc_hbm_model.sv';hb=git(PIN,HBM)
 actualmanifest='results/rtl/hdc_v41x_fullshape_200k_l14_rank0_image.json';ar=git(PIN,actualmanifest);old=json.loads(ar)
 retained={};pair=[]
 for name in ('q_weight','k_weight'):
  e=old['files']['w.engram.'+name];p=Path(old['scratch_path_at_generation'])/('w.engram.'+name+'.bin');st=p.stat();raw=p.read_bytes();assert len(raw)==40960 and sha(raw)==e['sha256']
  aft=p.stat();assert (st.st_size,st.st_mtime_ns,st.st_ino)==(aft.st_size,aft.st_mtime_ns,aft.st_ino)
  retained['layers.14.engram.'+name]=dict(path=str(p),dtype='BF16',logical_shape=[4,5120],bytes=40960,sha256=sha(raw),existing_manifest_commit=PIN,existing_manifest_path=actualmanifest,existing_manifest_sha256=sha(ar))
  values=np.frombuffer(raw,dtype='<u2').astype('<u4')<<16;pair.append(values.view('<f4'))
 gold=git(PIN,'tools/hdc_golden.py');tree=ast.parse(gold);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('z','mul')];assert len(nodes)==2
 ns=dict(np=np,F=np.float32);exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_G_mul_only','exec'),ns)
 with np.errstate(over='ignore',invalid='ignore',under='ignore'):product=ns['mul'](pair[0],pair[1]).astype('<f4')
 assert product.shape==(20480,);productbits=product.view('<u4');crombytes=b''.join(struct.pack('<II',int(v),0) for v in productbits)
 # Hash oracle only; Fermat owns constant image producer. No new images here.
 l14=dict(source_pair_complete=True,FP32_product_coefficients=20480,FP32_product_bits_sha256=sha(productbits.tobytes()),CROM64bit_product_slice_sha256=sha(crombytes),finite_coefficients=int(np.isfinite(product).sum()),nonfinite_coefficients=int((~np.isfinite(product)).sum()),zero_coefficients=int((product==0).sum()),negative_zero_bits=int((productbits==0x80000000).sum()),golden_mul_source_commit=PIN,golden_mul_source_sha256=sha(gold),golden_order='FP32mul(q,k) canonicalizeszero; dot=(h*wgt)*key; no reordering',physical_or_software_image_produced=False)
 out=dict(schema='opentallas.engram.rowaligned-home-service-demand.v1',status='PASS_METADATA_DEMAND_L14_RETAINED_SOURCE_L1_UNBOUND_NO_ADMISSION',model_commit=subprocess.check_output(['git','rev-parse',MODEL],text=True).strip(),model_path=MP,model_sha256=sha(mr),actual_contract_commit=EC,actual_contract_sha256=sha(er),eight_scale_spec_commit='9b5ca5767c4c03be4c587d77ad8c4ca8ff6f1f39',eight_scale_spec_sha256=sha(sr),generator_sha256=sha(Path(__file__).read_bytes()),ROM_candidate=dict(immutable_table_copies=1,table_rows=rows,stored_useful_bytes=rows*264,word_containers=words,physical4096x274_macros=macros,macro_capacity_bits=bits,macro_capacity_bytes=bits//8,padding_words=sum(c['padding_words'] for c in columns),per_row=dict(words=8,useful_bits=2112,container_bits=2192,no_row_crosses_macro=True),columns=columns,selected_requests_per_token=48,selected_word_reads_per_token=384,proposed_column_port_bits=274,decoder_payload_bits=264,per_layer_24to1_response_port_bits=264,per_layer_response_beats=192,per_layer_service_issue_cycles=192,per_layer_ideal_1p2GHz_serialization_ns=160,local_response_capture_required=True,bank_selector_size='up to31252macros/column; actualhierarchicalregisteredselect/route required',raw_response_boundary_bytes_per_layer=6336,decoded_BF16_buffer_write_bytes_per_layer=12288,table_macro_area_mm2=None,physical_die_count=None,SS_read_latency=None,registered_bank_route_latency=None,consumer_projection_location=None,CDC_broadcast_service=None,qualification=False),
 HBM_candidate=dict(immutable_table_copies=1,useful_backing_bytes=rows*264,existing_service_source_commit=PIN,existing_service_path=HBM,existing_service_sha256=sha(hb),existing_sector_bits=256,source_default_sector_address_bits=24,compact_whole_table_flat_sector_address_bits=33,whole_table_default_aperture_sufficient=False,required_address_binding='explicitstack/pseudochannel/region sharding; sourceAW24cannot silentlyaddress203GBtable',formats=dict(compact_interleaved8beats=dict(stride_bytes=264,backing_bytes=rows*264,sectors32_per_row=9,requires='base32aligned; residues rowstarts0/8/16/24; reassembly strips sectorpadding'),rowaligned9sectors=dict(stride_bytes=288,backing_bytes=rows*288,sectors32_per_row=9,padding_bytes_per_row=24),separate_code_scale_tables=dict(code_row_bytes=256,scale_row_bytes=8,backing_bytes=rows*264,command_regions_per_row=2,sectors32_per_row=9,requires='separate32aligned code/scale base bindings; code8sectors+scale1sector')),sectors_per_token=432,transferred32byte_sector_bytes_per_token=13824,transfer_overhead_bytes_per_token=1152,decoder_output264bit_beats_per_token=384,mandatory_reassembly_bytes_per_row=264,source_model_timing_ps=dict(BURST=1024,TCCDL=2560,CL=12500,RCDRD=19375,RP=16250),timing_scope='sourcebehavioralHBMservice assumptions; notphysicaltable admission orclock closure',one_PC_burst_serialization_floor_ns=432*1.024,one_PC_same_bank_tCCDL_issue_span_ns=(432-1)*2.560,per_layer_single_PC_burst_floor_ns=216*1.024,pseudochannel_bank_assignment=None,controller_command_return_ports=None,random_row_cache_state=None,physical_stack_count=None,measured_or_composed_latency=None,producer_or_adapter_binding=None,capacity_credit=False),
 shared_decoder_service=dict(input264bits_per_layer=264,output512bits_per_layer=512,layers=2,ports_per_layer=1,beats_per_row=8,response_beats_per_layer=192,nonstall_cycles_per_layer=192,minimum_row_group_bytes_per_layer=6336,buffer_bytes_two_slots_total=49152,held_tag_address_code_scale_atomic=True,corrected_RTL_admission=False,composed_token_latency=None),
 generated_constants=dict(required_each_layer_FP32_coefficients=20480,required_new_CROM64_words=40960,resulting_CROM64_words=549760,prior_capacity_excess_words=25472,model_selected_packed_banks_per_rank=45,packed_container_depth=4096,container_bits=274,logical20bit_address=True,logical_words_capacity=552960,spare_logical_words=3200,scalar_ports=1,unrelated_reads_serialized=True,physical_packing_writer_admitted=False,retained_sources=retained,L14_oracle=l14,L1=dict(source_pair_complete=False,raw_source_paths=None,product_SHA=None,reason='Retainedfilename inventory foundL14only; no newcheckpointreads authorized'),complete_generated_source_pair=False),
 routing_required=['48columnrequests withlayer/column/slot identity;2independent24wayresponsearbiters','hierarchical registeredROMmacro selection or HBMsector reassembly withheldresponse lease','2x264bit source->decoder,2x512bit decoder->buffer boundaries priced','location ofwkv producer and rawrow vskey/value consumerboundary must bind; no transferboth alternatives asoneproof','fullconsumer/doublebufferrelease and CDC/broadcast completion, notlastserializerbyte'],source_reads=dict(checkpoint_bytes=0,retained_L14_raw_source_bytes=81920,no_downloads=True,no_new_extraction=True),RTL_changes=False,RTL_or_PnR_runs=False,full_home_admission=False)
 OUT.mkdir(parents=True);(OUT/'demand.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');(OUT/'SHA256SUMS').write_text(sha((OUT/'demand.json').read_bytes())+'  demand.json\n')
 print(json.dumps(dict(ROM_macros=macros,ROM_capacity_bytes=bits//8,HBM_sectors=432,L14=l14,L1_complete=False)))
if __name__=='__main__':main()
