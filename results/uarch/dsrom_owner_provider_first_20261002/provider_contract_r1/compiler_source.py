#!/usr/bin/env python3
"""Uniform compiled config debit and source tensor read contract; no hardware GO."""
import argparse, json, math
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V
import dsrom_owner_provider_first as P
import dsrom_owner_provider_first_readback as B

ROOT=Path(__file__).resolve().parents[1]


def uniform_control_contract(stage_stats):
    required=max(s['control']['required_PHW'] for s in stage_stats)
    nstages=len(stage_stats);np=4096;pages=1<<required;data=nstages*np*25*48*pages
    protected_bits=nstages*np*25*(48+C.secded_bits(48))*pages
    return {'compiled_NP':np,'stages':nstages,'uniform_required_PHW':required,
        'uniform_field_profile_selected_or_implemented':False,
        'uniform_source_cfg_data_bits_per_TP_rank':data,
        'uniform_cfg_data_plus_SECDED_bits_per_TP_rank':protected_bits,
        'uniform_source_cfg_data_bits_all4_ranks':4*data,
        'source_PHW6_cfg_data_bits_per_TP_rank':nstages*np*25*48*64,
        'per_stage_minimal_width_profile_bits_per_TP_rank':sum(s['control']['compiled_cfg_source_data_bits'] for s in stage_stats),
        'per_stage_minimal_width_profiles_not_adopted':True,
        'uniform_phase_key_table_bits_per_TP_rank':nstages*32*pages,
        'lookup_parallel_entry_count_per_stage':pages,'lookup_entry_bits':32,
        'cfg_loader_word_width':48,'cfg_loader_parallel_local_read_bits_per_cycle_per_stage':np*48,
        'cfg_boundary_bits':1+required+3,'cfg_broadcast_sites_per_stage':np,
        'cfg_load_cycles_per_phase_from_source_CW_plus2':27,
        'loader_address_width':math.ceil(math.log2(25*pages)),
        'loader_address_width_source_PHW6':math.ceil(math.log2(25*64)),
        'clock_target_stream_GHz':1.2,'clock_target_serial_chain_GHz':0.9,
        'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
        'actual_SS_FF_or_clock_calibration':False,
        'conditional_fixed4096_macro_screen_per_stage':B.control_debit(pages)['conditional_fixed4096_cfg_screen'],
        'config_macro_decoder_lookup_and_delivery_area_debit_mandatory':True,
        'original_pair_frame_inclusion_or_additional_area_not_bound':True,
        'no_free_config_bits_no_native_area_discount':True,'physical_fit_qualified':False}


def tensor_provider_address(provider,headers,alias,rank,row,col=0):
    if not 0<=rank<4:raise ValueError('rank')
    x=P.provider_tensor_address(provider,alias,row,col)
    d=next(d for d in provider['declarations'] if d['alias']==alias);h=headers[d['tensor']]
    if provider['kind']=='HE':
        srcrow,srccol=row,col
    else:
        spec=next((s for s in C.LC.die_slices(provider['layer'],rank,C.SHAPE,[],provider['layer'] in C.R.ENGRAM) if s[0]==alias),None)
        rr=spec[2] if spec else None;cc=spec[3] if spec else None
        if len(h['shape'])==1:
            srcrow=(rr[0] if rr else 0)+row;srccol=None
        else:
            cols=cc[1]-cc[0] if cc else math.prod(h['shape'][1:])
            srcrow=(rr[0] if rr else 0)+row//cols;srccol=(cc[0] if cc else 0)+row%cols
        if srcrow>=h['shape'][0]:raise ValueError('constant source slice')
    return {**x,'rank':rank,'source_row':srcrow,'source_col':srccol,'source_dtype':h['dtype'],
        'storage_expansion':'BF16_to_FP32_exact' if h['dtype']=='BF16' else 'native_FP32',
        'packing_reference':'pack_he_fp32 HHW8' if provider['kind']=='HE' else '8_expanded_FP32_per256bitword',
        'actual_native_consumer_provider_ABI_bound':False}


def generate(readback,journal,out):
    readback=readback.resolve();journal=journal.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    x=json.loads(readback.read_text());providers=list(C.readrows(journal/'immutable_provider_preallocation.jsonl.gz'))
    headers=C.load_headers(P.INPUTS/'tensor_headers.jsonl.gz');samples=[]
    for p in providers:
        for d in p['declarations']:
            for rank in range(4):
                if p['kind']=='HE':coords=[(0,0),(d['rows']-1,d['K']-1)]
                else:coords=[(0,0),(d['elements']-1,0)]
                for row,col in coords:samples.append(tensor_provider_address(p,headers,d['alias'],rank,row,col))
    C.gzrows(out/'tensor_provider_boundary_reads.jsonl.gz',samples)
    report={'schema':'opentallas.owner.provider-contract.v1','candidate':P.CANDIDATE,
        'storage_capacity_verdict':x['capacity_verdict'],'uniform_control':uniform_control_contract(x['stage_stats']),
        'immutable_provider_tensor_boundary_read_count':len(samples),
        'tensor_provider_boundary_gate':'PASS_SOURCE_SLICE_AND_PHYSICAL_ADDRESS',
        'exact_source_provider_ABI_required':'HE packing reference HCP8 is not automatically native HROM768; CROM256 storage is not the consumer64-bit port. Both require bound adaptation and causal delivery.',
        'matrix_provider_home_routes_need_calendar':True,'new_partition_or_count_selected':False,
        'whole_token_cycles':None,'hardware_admission':False,'payload_bytes_read':0,
        'source_pins':V.source_receipts(),'compiler_sha256':C.sha(Path(__file__).read_bytes()),
        'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in [readback,journal/'immutable_provider_preallocation.jsonl.gz',P.INPUTS/'tensor_headers.jsonl.gz']}}
    (out/'model.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'storage':x['capacity_verdict'],'uniform_PHW':report['uniform_control']['uniform_required_PHW'],
        'cfg_data_bits_per_rank':report['uniform_control']['uniform_source_cfg_data_bits_per_TP_rank'],
        'provider_boundary_reads':len(samples),'hardware_admission':False}))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--readback',type=Path,required=True);p.add_argument('--journal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    generate(a.readback,a.journal,a.out)
