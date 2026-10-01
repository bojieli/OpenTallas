#!/usr/bin/env python3
"""Additive storage/TP-view and finite producer dependency input for the builder."""
import hashlib
import json
from pathlib import Path
import subprocess
import w11_dsrom_full_tp_program as F

CENSUS_PIN='db83b444c5c8f905e5f3903a605ea52190cc0f5e'
CENSUS='results/quality/w16_w17_nonexpert_header_census_20261001/census.json'
PHASE_PIN='d74a0bd4d475680b0d83b775d7733259a7f2d4eb'
PHASE='results/rtl/w17_connected_token_preparation_20261001/ckv_prelease_return_contract.json'

def read(pin,path):
    raw=subprocess.check_output(['git','show',pin+':'+path],cwd=F.ROOT)
    return json.loads(raw),{'commit':pin,'path':path,'sha256':hashlib.sha256(raw).hexdigest()}


CODEC_PIN='93431e3c56af686d7c52c5c06a9f5cae39fed609'
CODEC='results/quality/w16_dsrom_nonexpert_codec_views_20261001/contract.json'

def build_contract(program):
    F.validate_program(program)
    census,census_ref=read(CENSUS_PIN,CENSUS);phase,phase_ref=read(PHASE_PIN,PHASE)
    codec,codec_ref=read(CODEC_PIN,CODEC)
    assert codec_ref['sha256']=='d55ed4ea650b5275b4018465222f3d8e528151d7df3279bcae7616545e4218ab'
    assert codec['summary']['reference_word_totals_by_codec']['reference_HE_hplace_FP32']==1638400
    assert codec['summary']['HE_words_all_four_reference_copies']==6553600
    import rtl_v41_fullshape_layer_campaign as LC
    views=[];shape=dict(F.R.SHIPPED,ratio=F.R.RATIO)
    for L in range(40):
        for rank in range(4):
            for image,name,rr,cc in LC.die_slices(L,rank,shape,[],L in F.R.ENGRAM):
                t=census['tensors'].get(name)
                if t is None:
                    views.append({'layer':L,'rank':rank,'tensor':name,'header':None,'physical_home':None});continue
                reference={'rank':rank,'image_name':image,'rows':list(rr) if rr else None,'columns':list(cc) if cc else None}
                assert reference in t['reference_image_views'],('TP census mismatch',name,reference)
                dims=t['decoded_logical_shape'];local=list(dims)
                if rr:local[0]=rr[1]-rr[0]
                if cc:local[1]=cc[1]-cc[0]
                runtime='BF16_after_FP8_QDQ' if image=='wo_a' else t['dtype']
                rule=('FP32 HC chunk8 products and sums; replicated full24x20480' if image.endswith('_fn') else
                      'full K per output row, golden chunk8 quant32-dot/blocksum; BF16 output' if runtime=='F8_E4M3' else
                      'wo_a BF16 converted from checkpoint FP8+blockscales, grouped fullK and golden chunk8 thenBF16' if image=='wo_a' else
                      'BF16 operands, FP32 chunk8 products/sums; preserve source output rounding')
                if image=='wo_b':rule='input-column split, FP32 rank partial; ((r0+r1)+(r2+r3)), single finalBF16'
                model=None
                if len(local)==2 and not image.endswith('.scale'):
                    if runtime=='F8_E4M3':model={'model_point':'q1024','payload_bits':264,'word_bits':274,'codes_per_group':32,'groups':local[0]*((local[1]+31)//32),'word_address':None,'scope':'Ram field candidate group count only; no descriptor/placement/clock credit'}
                    elif runtime in ('BF16','BF16_after_FP8_QDQ'):model={'model_point':'BF1024','payload_bits':256,'word_bits':274,'BF16_per_group':16,'groups':local[0]*((local[1]+15)//16),'word_address':None,'scope':'Ram field candidate; existing ME packer uses FP32 bank containers, conversion/control unpriced'}
                    elif runtime=='F32':model={'model_point':None,'packing':'corrected93431 reference HROM 8Kchunks x3outputlanes x32bits, address k_prime*8+j;768bit word','scalar_bits':32,'port_bits_per_read':768,'words_per_reference_rank':20480,'actual_hardened_bank_binding':None,'physical_replica_count':None}
                ce=codec['tensors'].get(name,{})
                cv={'codec':ce.get('codec'),'layout':ce.get('codec_layout'),'word_bits':ce.get('codec_word_bits'),
                    'tensor_reference_word_count':ce.get('codec_word_count'),'tensor_count_scope':'per_reference_rank' if runtime=='F32' else 'all4reference_views',
                    'rank_word_view':next((x for x in ce.get('rank_word_views',[]) if x['rank']==rank),None),
                    'producer_gap':ce.get('producer_gap'),'current_whole_program_image_binding':None,'physical_owner':None}
                views.append({'layer':L,'rank':rank,'tensor':name,'image_name':image,'checkpoint_dtype':t['dtype'],
                    'checkpoint_stored_shape':t['stored_shape'],'logical_shape':dims,'rank_logical_shape':local,
                    'rows':reference['rows'],'columns':reference['columns'],'runtime_format':runtime,
                    'header_source':{'shard':t['shard'],'offsets':t['absolute_file_offsets']},
                    'round_order':rule,'reference_codec_contract':cv,'field_sizing_candidate':model,'physical_home':None,
                    'role':'replicated_HC' if image.endswith('_fn') else ('KV_source_producer' if image.startswith('compressor.') else ('index_source_producer' if image.startswith('indexer.') else 'layer_consumer'))})
    head=census['tensors']['head.weight']
    assert head['dtype']=='BF16' and head['decoded_logical_shape']==[129280,5120]
    for rank in range(4):views.append({'layer':'head','rank':rank,'tensor':'head.weight','checkpoint_dtype':head['dtype'],
        'runtime_format':'BF16','logical_shape':[129280,5120],'rank_logical_shape':[32320,5120],
        'rows':[rank*32320,(rank+1)*32320],'columns':None,
        'round_order':'full5120input dot per vocabulary row, FP32 logit; global max tie lowestID',
        'field_sizing_candidate':{'model_point':'BF1024','payload_bits':256,'word_bits':274,'groups':32320*320,'word_address':None},
        'physical_home':None,'scope':'new declared head output-row contract; census reference_image_views empty, not prior qualification'})
    return {'schema':'opentallas.w11.dsrom-full-tp4-home-and-producer-contract.v1',
        'source_pins':{'nonexpert_census':census_ref,'corrected_codec':codec_ref,'prelease_return':phase_ref,
            'HE_packer':{'commit':F.PIN,'path':'tools/v41_fullshape_weight_layout.py',
                'sha256':hashlib.sha256(subprocess.check_output(['git','show',F.PIN+':tools/v41_fullshape_weight_layout.py'],cwd=F.ROOT)).hexdigest()}},
        'program_canonical_sha256':hashlib.sha256(json.dumps(program,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'matrix_views':views,'corrected_reference_word_totals':codec['summary'],
        'word_count_policy':'FP8/BF16 totals already sum4referenceviews; HE1638400 perreferenceRANK,6553600 allfourcopies. No automatic physical allocation of reference replicas; Ram alone assigns physical homes. Do not sum these summary totals again with individual views.',
        'source_census_config_sha256':census['config_sha256'],
        'source_config_scope':'Checkpoint census config hash kept distinct from repo inference-config hash; only individual tensor/TP views validated here',
        'phase_dependencies':phase['corrected_phase_dependencies'],'reserved_return_endpoints':phase['actual_receiver_bindings'],
        'architectural_reservations':phase['explicit_architectural_reservations'],'prelease_pricing':phase['pricing'],
        'mandatory_order':['finish prior old jobs with return consumers enabled','freeze new admission','drain prior requests/readreturns/pendingwrites',
            'reserve all512 AG rank-row slots and finite peer hop credits','exclusive all32PC lease','9actual burstvisible writes',
            'publish row / read fence','f_job','final vector/collective/consumer drain','credit release'],
        'lifecycle_events':{'accepted':'request grant consumes slot; no visibility proof','visible':'actual backing commit after burst, held event accepted',
            'consumed':'final actual attention/vector output consumerdone, not serializer lastbyte or coreEND',
            'credit_release':'only after required persistence/publication and finalconsumerdone + reverseCDC'},
        'unbound_actuals':{'ROM_home':None,'Engram_codec_home':None,'writable_mux':None,'finite_hops':None,
            'full_tp4_ISA_numeric_execution':None,'head_argmax_collective':None,'consumer_done_calendar':None,'whole_token_cycles':None},
        'gain_credit':0,'hardware_admission':False,'adopt':False,'jobs_launched':0,
        'next_gate':'Full four-rank ISA executor: encoded command legality, image/constant/source-selected store binding, real collectives and persistent state; compare all40/head without golden activation injection. Functional interpreter test alone cannot pass this gate.'}
