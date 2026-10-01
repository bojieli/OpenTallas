"""Source-bound additive reference codec word demands; no physical allocation authority."""
import ast,hashlib,json,subprocess
from pathlib import Path
PIN='b035f6977f590c0ff07cfc92885eb699a0b13803'
CENSUS='db83b444c5c8f905e5f3903a605ea52190cc0f5e'
CP='results/quality/w16_w17_nonexpert_header_census_20261001/census.json'
OUT=Path('results/quality/w16_dsrom_nonexpert_codec_views_20261001')
def read(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 raw=read(CENSUS,CP);cat=json.loads(raw)
 paths=['tools/rtl_v41_rom_array.py','tools/v41_rom_ksplit_bankmap.py','tools/rtl_v41_fullshape_layer_campaign.py','tools/hdc_program_v41.py','tools/hdc_replay_v41.py','tools/hdc_isa_v41.py','tools/hdc_golden_v41.py','rtl/chip/ot_chip_v41x_tile.sv','rtl/v41rom/ot_v41_rom_elem.sv']
 src={p:read(PIN,p) for p in paths}
 tree=ast.parse(src['tools/v41_rom_ksplit_bankmap.py']);phase=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PHASE' for t in n.targets))
 results={};totals={};gaps=[]
 for k,r in cat['tensors'].items():
  if r['scope']!='main_text':continue
  item=dict(stored_dtype=r['dtype'],stored_shape=r['stored_shape'],stored_bytes=r['stored_bytes'],family=r['family'],reference_views=r['reference_image_views'],physical_owner=None,physical_replica_count=None,physical_macro_count=None,physical_capacity_credit=False,codec_word_count=None,codec_word_bits=None,port_bits_per_read=None,qualified_current_image_writer=False)
  local='.'.join(k.split('.')[2:]) if k.startswith('layers.') else k
  if k.endswith('.scale'):
   item['accounting']='paired exponent embedded in weight block words when that weight codec is bound; not a second standalone allocation'
   item['paired_weight']=r['paired_tensor']
  elif local in ('hc_attn_fn','hc_ffn_fn'):
   n,K=r['stored_shape'];assert r['dtype']=='F32' and n==24 and K==20480
   item.update(codec='reference_HE_hplace_FP32',codec_word_bits=768,port_bits_per_read=768,codec_word_count=K//8*8,reference_rank_copies=4,words_all_four_reference_copies=K*4,qualified_current_image_writer=True,codec_layout='8 K-chunks x3 output lanes x32bits; address k_prime*8+j; lane c*3+l holds row j*3+l,column c*(K/8)+k_prime',contract='hdc_program_v41.Layout.hplace plus hrom.hex writer; current tile HS8,HNL3',allocation_note='Reference HROM contract only; no hardened bank/macro bound or placement credit')
  elif local in phase and r['kind']=='matrix_or_table':
   fmt='bf16' if local=='attn.wo_a.weight' or r['dtype']=='BF16' else 'fp8' if r['dtype']=='F8_E4M3' else None
   if fmt and r['qualified_reference_TP_assignment']:
    views=[]
    for v in r['qualified_reference_TP_assignment']:
     sh=list(r['decoded_logical_shape']);nr=v['rows'][1]-v['rows'][0] if v['rows'] else sh[0];K=v['columns'][1]-v['columns'][0] if v['columns'] else sh[1]
     width=16 if fmt=='bf16' else 32;assert K%width==0
     views.append(dict(rank=v['rank'],rows=nr,K=K,words=nr*(K//width),payload_bits=256 if fmt=='bf16' else 264,container_bits=274,paired_macro_row_word_count_per_macro=nr//2*(K//width) if nr%2==0 else None))
    is_woa=local=='attn.wo_a.weight'
    item.update(codec=fmt,codec_word_bits=274,port_bits_per_read=274,codec_word_count=sum(v['words'] for v in views),rank_word_views=views,qualified_current_image_writer=not is_woa,codec_layout='16BF16 lane entries h*128+lane*8+b' if fmt=='bf16' else '32FP8codes in bits255:0, matching UE8M0 exponent in bits263:256',contract='rtl_v41_rom_array.bf16_word / Mat.block_word; PHASE selection; census TP views',phase=phase[local],scale_expansion='FP8 scale duplicated per output row per32columns; header scale shared across32rows' if fmt=='fp8' else None)
    if is_woa:item.update(qualified_current_image_writer=False,conversion='LazyWeights wo_a FP8 QDQ -> BF16 established; bankmap selectsbf16; Mat(bf16) itself requiresstoredBF16',producer_gap='No bound actual FP8-checkpoint-to-BF16 ROM image producer in this reference Mat path; word demand candidate only')
  elif local=='engram.wkv.weight':
   item['codec_candidate']='FP8 32codes+matchingexp word264b in274container; reference TP rows in census'
   item['producer_gap']='Not selected by bound PHASE array campaign; fullprogram producer/array phase contract required'
  elif '.engram.embed.' in k:
   item['contract']='a9d1fad2835d96e4c0585a150b6a9d484b9791cc Engram actual264B/8scales;1ba8abc0 unchanged gather failure'
   item['producer_gap']='Immutabletablehome qualification pending Ram; corrected perbeat decoder not admitted'
  else:
   item['producer_gap']='No current ROM-array image codec binding established for this tensor; software/CROM use is not field-bank allocation'
  results[k]=item
  if item['codec_word_count'] is not None:
   f=item.get('codec');totals[f]=totals.get(f,0)+item['codec_word_count']
  elif not k.endswith('.scale'):gaps.append(k)
 out=dict(schema='opentallas.dsrom.nonexpert.reference-codec-views.v1',status='REFERENCE_WORD_DEMAND_ONLY_NOT_PHYSICAL_FIT',source_commit=PIN,source_sha256={p:sha(b) for p,b in src.items()},census_commit=CENSUS,census_path=CP,census_sha256=sha(raw),generator_sha256=sha(Path(__file__).read_bytes()),tensors=results,summary=dict(main_text_tensor_count=len(results),reference_word_totals_by_codec=totals,unbound_non_scale_tensor_count=len(gaps)),unbound_non_scale_tensors=gaps,full_allocation_authority='Ram',q1024_BF1024_assignment=None,HE_hardened_bank_geometry=None,current_product_complete=False,admission_claim=False,notes=['Reference TP copies differ from full physical residency; no historical46stagefit reused.','Counts are per matrix row across both paired row macros; per macro count explicit separately.','Layer norm/HC constants and embedding/head/index constants kept NULL unless actual codec binds; reference HROM counts separate768bitstorage class.','FP8wo_a expandedBF16 demand is candidate until actualimageproducer bound.','Companion scales absorbed into block words; no duplicate scale charge.'])
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'contract.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');(OUT/'summary.json').write_text(json.dumps(out['summary'],indent=2,sort_keys=True)+'\n')
 (OUT/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(OUT.glob('*.json'))))
 assert len(results)==1258 and sum(r.get('codec_word_count') is not None for r in results.values())>0
 print(json.dumps(out['summary']))
if __name__=='__main__':main()
