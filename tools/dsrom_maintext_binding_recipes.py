"""Metadata-only exact producer/consumer recipes, with deployed assignments NULL."""
import hashlib,json,math,subprocess
from pathlib import Path
PIN='18712a57ec5f55cd99bbcbe4cc6b64027d11bd20'
CENSUS='db83b444c5c8f905e5f3903a605ea52190cc0f5e'
CP='results/quality/w16_w17_nonexpert_header_census_20261001/census.json'
OUT=Path('results/quality/w16_dsrom_maintext_binding_recipes_20261001')
def read(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 raw=read(CENSUS,CP);cat=json.loads(raw)
 paths=['tools/v41_fullshape_weight_layout.py','tools/v41_fullshape_program_bind.py','tools/rtl_v41x_fullshape_l0_inputs.py','tools/hdc_program_v41.py','tools/hdc_replay_v41.py','tools/rtl_v41_fullshape_layer_campaign.py','tools/v41_die_l0_images.py','rtl/chip/ot_chip_v41x_tile.sv','results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json']
 sources={p:read(PIN,p) for p in paths};lp=paths[-1];layout=json.loads(sources[lp]);recipes={}
 def base(k,r):return dict(tensor=k,stored_dtype=r['dtype'],stored_shape=r['stored_shape'],stored_bytes=r['stored_bytes'],reference_TP_views=r['reference_image_views'],resident_home=None,physical_replica_count=None,physical_port_count=None,physical_macro_geometry=None,current_fullprogram_image_binding=None)
 names={'attn_norm.weight':'attn_norm','ffn_norm.weight':'ffn_norm','attn.q_norm.weight':'q_norm','attn.kv_norm.weight':'kv_norm','hc_attn_scale':'hc_attn_scale','hc_ffn_scale':'hc_ffn_scale','hc_attn_base':'hc_attn_base','hc_ffn_base':'hc_ffn_base','attn.attn_sink':'attn_sink','ffn.gate.bias':'gate.bias','attn.compressor.norm.weight':'compressor.norm','attn.indexer.k_norm.weight':'indexer.k_norm'}
 for k,r in cat['tensors'].items():
  if r['scope']!='main_text':continue
  local='.'.join(k.split('.')[2:]) if k.startswith('layers.') else k
  if local in names or k=='norm.weight':
   item=base(k,r);n=24 if local in ('hc_attn_scale','hc_ffn_scale') else math.prod(r['stored_shape'])
   if local=='attn.attn_sink':
    vv=r['qualified_reference_TP_assignment'];assert vv and vv[0]['rows'];n=vv[0]['rows'][1]-vv[0]['rows'][0]
   item.update(recipe='pack_constant_from_manifest',name=names.get(local,'final_norm'),source_compatible=r['dtype'] in ('BF16','F32'),output_format='FP32_lo_plus_zero_hi',output_word_bits=64,output_words_per_reference_view=n,output_bytes_per_reference_view=n*8,transform='BF16exact widen toFP32 orF32preserve; HCscale3 ->repeat4,4,16; high32bits+0',consumer='tile.crom port with SRC_CLO lowFP32 and SRC_CHI highFP32; CROM array reads4*SW streamports +aux +XS; declared behavior not hardened physical port proof',consumer_contract='ShapeLayout.constant_bases ->rmsnorm/hc_mix/sink/router instructions; binder admits onlyL0/L20 rank0',producer_scope='Named CROM tensors selected by assemble_token_layer; final_norm generic recipe only, absent current layer binder',recipe_application='requires source-image manifest schema, w.<name> file format/byte shape/SHA and outputSHA; no image read or repack here')
   if k.startswith('layers.0.') and item['name'] in layout['constants']:
    e=layout['constants'][item['name']];assert e['word_count']==n
    item['existing_L0_rank0_image_record']=dict(layout_path=lp,layout_sha256=sha(sources[lp]),**e)
   recipes[k]=item
  elif local=='attn.wo_a.weight':
   item=base(k,r);R,K=r['stored_shape'];rankR=R//4
   item.update(recipe='wo_a_fp8_to_bf16 ->pack_me_bf16 ->verify_me',output_format='FP8_QDQ_then_BF16_as_FP32_bank_word',scale_tensor=r['paired_tensor'],transform='32x32UE8M0 dequant thenBF16RNE, emittedasBF16bits<<16 in32bit MEbank',stored_BF16=False,decoded_BF16=True,reference_rank_shape=[rankR,K],reference_image_banks=64,reference_bank_word_bits=32,reference_address_count=rankR*(K//64),reference_image_bytes=rankR*K*4,consumer='ME KIND1 bank adapter, not274bitROMarray',existing_L0_rank0_image_record=layout['matrices']['wo_a'] if k.startswith('layers.0.') else None,producer_scope='Fullshape one-layer image packer explicitly supports wo_a; full40 resident bases and production274bitconversionpath unbound')
   if k.startswith('layers.0.'):assert item['reference_address_count']==layout['matrices']['wo_a']['word_count']
   recipes[k]=item
  elif local in ('hc_attn_fn','hc_ffn_fn'):
   item=base(k,r);R,K=r['stored_shape'];words=R*((K+63)//64)
   item.update(recipe='pack_he_fp32 HHW8 alternative',output_format='FP32_HCP_8bank',reference_banks=8,reference_bank_word_bits=256,reference_read_boundary_bits=2048,reference_address_count_per_rank=words,reference_image_bytes_per_rank=words*256,consumer='tile.hbank[8*depth] hb_re[8]/hb_q[8*HHW*32]; distinctfrom HROM768 path',existing_L0_rank0_image_record=layout['matrices'][local] if k.startswith('layers.0.') else None,qualification='source-declared alternative only, no hardenedbank adoption or physicalcopies',authoritative_HROM768_reference='93431e3c56af686d7c52c5c06a9f5cae39fed609;20480words/matrix/reference rank')
   if k.startswith('layers.0.'):assert words==layout['matrices'][local]['word_count']
   recipes[k]=item
 for k in ('embed.weight','head.weight'):
  r=cat['tensors'][k];item=base(k,r);R,K=r['stored_shape'];assert r['dtype']=='BF16'
  item.update(golden_consumer='embedding selects token row then replicates4HCstreams' if k.startswith('embed') else 'head final_normBF16 ->BF16weightmatvec ->logitargmax',software_image_recipe='hdc_program_v41.Layout embedding flat64BF16/1024bit word' if k.startswith('embed') else 'hdc_program_v41.Layout.place(head) ME64BF16/1024bit word',recipe_scope='reduced Layout declares format; no complete released checkpoint/fullTP4 image binding',candidate_full_table_WROM_words=R*K//64,candidate_vocab_quarter_WROM_words=(R//4)*K//64,declared_tile_WROM_depth_words=1<<19,declared_tile_WROM_word_bits=1024,default_depth_sufficient_even_for_vocab_quarter=False,consumer='tile ewrom streamports and XS32bit widened BF16 path' if k.startswith('embed') else 'ShapeLayout.mathead vocabquarter ->ME instruction withamax; actualwordbase unresolved',consumer_missing='embedding globaltoken->quarterowner/localaddress+broadcast schedule unbound; read-only array address truncation must notalias' if k.startswith('embed') else 'head imagewriter/base and complete rankargmax reduction unbound; currentShapeBuilder headnorm passesbase0',per_token_useful_weight_read_bytes=K*2 if k.startswith('embed') else (R//4)*K*2,per_token_read_scope='one token embeddingrow, physicalfanoutNULL' if k.startswith('embed') else 'perrankvocabquarter candidate, producer/residentbindingNULL')
  assert item['candidate_vocab_quarter_WROM_words']>item['declared_tile_WROM_depth_words'];recipes[k]=item
 summary=dict(bound_source_recipes=len(recipes),CROM_recipe_tensor_count=sum(r.get('recipe')=='pack_constant_from_manifest' for r in recipes.values()),CROM_reference_words_by_layer={str(L):sum(r['output_words_per_reference_view'] for k,r in recipes.items() if k.startswith(f'layers.{L}.') and 'output_words_per_reference_view' in r) for L in range(40)},existing_L0_rank0_image_records=sum(r.get('existing_L0_rank0_image_record') is not None for r in recipes.values()),complete_product_image_binding=False)
 out=dict(schema='opentallas.dsrom.maintext.producer-consumer-recipes.v1',status='PASS_SOURCE_RECIPES_COMPLETE_PRODUCT_BINDINGS_NULL',source_commit=PIN,source_sha256={p:sha(b) for p,b in sources.items()},census_commit=CENSUS,census_path=CP,census_sha256=sha(raw),generator_sha256=sha(Path(__file__).read_bytes()),recipes=recipes,summary=summary,owner_handoff='Fermat confirms tools/w11_dsrom_full_tp_program.py/_contract.py descriptorbuilder only; actualfullprogramimagewriter absent; physicalimage/constant/stagebasesNULL',full_allocation_authority='Ram',payload_reads=0,image_reads=0,RTL_changes=False,PnR=False,admission_claim=False,required_next_bindings=['Fermat full40+embed/head source-image manifests and imagewriter withperrankbase/owner','Ram actualhomes and ports for CROM,HROM768 orHCPalternative,ME vs274fieldcodec','Currentwo_a one-layer conversionproducerexists but complete274fieldproducer unresolved','Embedding vocabowner/localaddress and exactmulticast; head finalnormbase and rankargmaxcombine','No4referenceimagecopy count promoted to physicalreplica'])
 OUT.mkdir(parents=True,exist_ok=True)
 for name,obj in [('contract.json',out),('summary.json',summary)]: (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
 (OUT/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(OUT.glob('*.json'))));print(json.dumps(summary))
if __name__=='__main__':main()
