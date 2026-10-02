#!/usr/bin/env python3
"""Exact symbolic 622 phase/key/config-provider interface export.

The corrected hard-provider screen is7depth-sliced4096x72 macros/pair, not the
older speculative packed274-bit screen. No hard provider, ECC, fault or timing
implementation is inferred from this table/API. All old receipts remain intact.
"""
from __future__ import annotations
import argparse, collections, gzip, json, math
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_owner_provider_first as P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_owner_cfg_interface_20261002'
JOURNAL=ROOT/'results/uarch/dsrom_owner_provider_first_20261002/r1'
READBACK=ROOT/'results/uarch/dsrom_owner_provider_first_20261002/readback_r1/model.json'
PHW=10;CW=25;NP=4096;PAGES=1024
PARENT='a7d981d65c4961052dd58af32e7a5a9c0212dbe2'
OWNER='622dbc897fd5ecb5a5b691e1ae39bea0ad751524'


def config_address(phase,word):
    if not (0<=phase<PAGES and 0<=word<CW):raise ValueError('configuration coordinate')
    logical=phase*CW+word;slice_,row=divmod(logical,4096)
    return {'logical_address':logical,'logical_address_bits':15,'macro_depth_slice':slice_,
            'macro_address':row,'macro_address_bits':12,'depth_select_bits':3,
            'payload_bit_range':[0,48],'candidate_ECC_bit_range':[48,55],
            'ECC_layout_proposal_only':True,'physical_word_bits':72}


def key_word(m):
    k=m['key']
    if not 0<=k<1<<30:raise ValueError('phase key overflow')
    return (1<<31)|((m['format']=='bf16')<<30)|k


def config_word(m,pair,word):
    if not 0<=pair<NP or not 0<=word<CW:raise ValueError('compiled pair/word')
    if m is None:return 0
    x=C.phase_cfg(m,pair)[word]
    if not 0<=x<1<<48:raise ValueError('configuration payload overflow')
    return x


def sidecar_address(provider,linear_bit):
    if provider['kind']!='ECC_FP4_SIDECAR' or not 0<=linear_bit<provider['bits']:
        raise ValueError('FP4 sidecar bit')
    physical_word,bit=divmod(linear_bit,256);pidx,local_word=divmod(physical_word,16384)
    mb,a=divmod(local_word,8192)
    return {'stage':provider['stage'],'pair':provider['pairs'][pidx],'mb':mb,'parity':a%2,
        'physical_row':a//2,'data_bit':bit,'protected_sidecar_word_data_bits':256,
        'candidate_sidecar_word_SECDED_bits':10,'decoder_or_port_implemented':False}


def loader_journal(phase,pair):
    """Required identity for25 reads; this is not an actual accepted service trace."""
    if not 0<=pair<NP:raise ValueError('pair')
    return [{'pair':pair,'phase':phase,'word':a,**config_address(phase,a),
             'accept_cycle':None,'return_cycle':None,'actual_delivery_fence':None} for a in range(CW)]


def generate(out):
    if out.exists():raise ValueError('fresh export directory required')
    out.mkdir(parents=True)
    parent=json.loads((OUT/'inputs/containment_model.json').read_text())
    check=json.loads((OUT/'inputs/containment_verification.json').read_text())
    receipts=json.loads((OUT/'inputs/source_receipt.json').read_text())
    if C.sha((OUT/'inputs/containment_model.json').read_bytes())!=check['model_sha256']:
        raise ValueError('parent containment hash')
    for n in ('ot_rom_4096x72_m8.v','ot_rom_4096x72_m8.json','ot_rom_4096x72_m8.lef',
              'ot_v41_pair_w17w10_rne_wake_prepare.sv','ot_v41_rom_adapt.sv'):
        if C.sha((OUT/'inputs'/n).read_bytes())!=receipts['sources'][n]['sha256']:
            raise ValueError('source snapshot '+n)
    expansion=parent['configuration_expansion']
    if (expansion['prospective_per_pair_4096x72_depth_slices'],expansion['prospective_macro_instances'],
        expansion['expanded_physical_macro_pin_count'])!=(7,28672,2523136):raise ValueError('hard provider shape')
    readback=json.loads(READBACK.read_text())
    if not readback['all40_all384_placed']:raise ValueError('owner prerequisite')
    counts=collections.Counter();keys=[[0]*PAGES for _ in range(58)];seen=set();phase_records=[]
    for ordinal,m in enumerate(C.readrows(JOURNAL/'assignments.jsonl.gz')):
        s=m['stage']
        if s is None:raise ValueError('unallocated matrix')
        phase=counts[s];counts[s]+=1
        if phase>=PAGES:raise ValueError('PHW10 overflow')
        kw=key_word(m);identity=(s,kw)
        if identity in seen:raise ValueError('duplicate source phase key')
        seen.add(identity);keys[s][phase]=kw
        phase_records.append({'stage':s,'phase':phase,'source_key_word':kw,'matrix_journal_ordinal':ordinal,
            'layer':m['layer'],'alias':m['alias'],'format':m['format'],'source_tensor':m['tensor'],
            'rank_slices':m['rank_slices'],'immutable_provider_home':m['immutable_provider_home'],
            'rows_per_rank':m['rows'],'K_per_rank':m['K'],'active_pair_count':len({r[1] for r in m['plans']}),
            'config_logical_word_range':[phase*CW,(phase+1)*CW],
            'word_API':'config_word(matrix_record,compiled_pair,word0..24)',
            'payload_plan_sha256':C.sha(json.dumps(m['plans'],separators=(',',':')).encode()),
            'invalid_pair_or_unused_phase_default_cfg_payload':0,'physical_or_timing_or_arithmetic_credit':False})
    if len(phase_records)!=46509 or any(counts[s['stage']]!=s['control']['phase_count'] for s in readback['stage_stats']):
        raise ValueError('phase identities not conserved')
    C.gzrows(out/'phase_directory.jsonl.gz',phase_records)
    C.gzrows(out/'key_tables.jsonl.gz',({'stage':s,'PHW':PHW,'word_bits':32,'words':words} for s,words in enumerate(keys)))
    immutable=list(C.readrows(JOURNAL/'immutable_provider_preallocation.jsonl.gz'))
    C.gzrows(out/'immutable_provider_directory.jsonl.gz',immutable)
    ecc=[p for p in C.readrows(JOURNAL/'provider_assignment.jsonl.gz') if p['kind']=='ECC_FP4_SIDECAR']
    C.gzrows(out/'FP4_ECC_provider_directory.jsonl.gz',ecc)
    matrix_ops=collections.Counter(x['format'] for x in phase_records)
    result={'schema':'opentallas.dsrom.cfg-provider-interface.v1','owner_commit':OWNER,'containment_commit':PARENT,
        'candidate':'DS4096-TP4-S58-PAIR1','compiled_NP':NP,'NBF':724,'R':128,'PHW':PHW,
        'cfg_words_per_phase_per_pair':25,'uniform_phases_per_stage':1024,'uniform_cm_words_per_pair':25600,
        'actual_phase_directory_count':len(phase_records),'actual_phase_counts_by_stage':dict(counts),
        'matrix_phase_formats':matrix_ops,'key_table_schema':{'valid_bit':31,'ME_BF16_bit':30,'key_bits':[0,30],
            'expert_key':'layer<<24 | family<<21 | expertID<<12','expert_stride':4096,
            'lookup_source':'adapt.keyrom:32bit entries; parallel compare and priority over all1024 slots',
            'same_tables_repeat_per4_rank_geometry':True,'new_hardware_tables_loaded_or_run':False},
        'generic_source_loader':{'cm_payload_bits':48,'ld_a_bits_required':15,'c_a_bits':5,'c_d_bits':48,
            'ld_run_drives_unbackpressured_read_cadence':True,'c_v_is_source_valid_not_provider_ack':True,
            'act_accumulates_class_valid_from_words8..15':True,'go_e':'go && act',
            'source27cycle_schedule_only_generic_model':'CW+2; physical macro/capture/ECC alignment must be independently bounded',
            'hard_provider_or_cfg_ECC_or_cfg_fault_path_present':False,'pair_fault_current_owner':'u_e.fault'},
        'prospective_physical_cfg_provider':expansion,
        'all58x4rank_macro_instances_if_uniform_provider':58*4*28672,
        'all58x4rank_physical_cfg_pins_if_uniform_provider':58*4*2523136,
        'older_packed274_cfg_screen_is_not_this_provider':True,
        'cfg_adapter_required_contract':{'request_identity':['pair','phase','word_index','logical_address','reset_or_lease_generation'],
            'macro_command':['clk','onehot_slice_ce_in[7]','addr_in[11:0]'],
            'macro_return':['rd_out[7][71:0]','selected_slice_identity','capture_valid'],
            'decoder_terminal':['decoded_payload48','good_or_corrected','uncorrectable_cfgfault','word_identity'],
            'consumer_delivery':['c_a[4:0]','c_d[47:0]','c_v_aligned_to_good_terminal'],
            'final_fence':'All25 words delivered to element with actual last-word/act visibility before go_e; no timer or generic c_v as causal hard-provider completion.',
            'fault_rule':'No act/go authorization from poison, stale, duplicate, mismatched, missing or reset-era returns; cfgfault must be separately surfaced and held through owner drain.',
            'ports_generation_ready_and_fault_plumbing_not_implemented':True},
        'raw_provider_adaptations':[{'kind':'HE','packing_reference':'8banks x256-bit pack_he_fp32 HHW8',
             'actual_native_HROM768_consumer_not_equivalent':True,'mapping_API':'provider_tensor_address + source tensor rank slices',
             'required_binding':'native accepted address -> readbank/address/FP32lane -> exact native output schedule and reply ownership'},
            {'kind':'CROM','storage':'8FP32 per256bitword','actual_consumer_64bit_interface_not_equivalent':True,
             'required_binding':'native address/half -> packed word/lane -> source precision/rank -> exact native reply ownership'},
            {'kind':'FP4_ECC','source_code_scale_payload_bits':272,'required_SECDED_bits':10,
             'candidate_inline_bits':2,'candidate_extra_sidecar_bits':8,'sidecar_address_API':'sidecar_address(provider,linear_bit)',
             'required_binding':'Accept real paired codeword+sidecar read; align ECC parity to same codeword/row/epoch; terminal good/corrected/fault before arithmetic acceptance',
             'current_decoder_or_sidecar_ports_present':False}],
        'actual_source_port_tables':parent['source_port_tables'],
        'parent_whole_budget':parent['authoritative_ledger'],
        'snapshot_storage_verdict':'PASS_SYMBOLIC_STORAGE_PLACEMENT','cfg_physical_timing_fault_ECC_admission':False,
        'full_descriptor_finite_calendar_bound':False,'cfg_requests_and_returns_are_model_identities_not_measured_events':True,
        'partition_or_geometry_selected':False,'RTL_builds_PR_or_sim_jobs':0,'checkpoint_payload_reads':0,
        'compiler_sha256':C.sha(Path(__file__).read_bytes()),'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in
             [READBACK,JOURNAL/'assignments.jsonl.gz',JOURNAL/'provider_assignment.jsonl.gz',
              OUT/'inputs/containment_model.json',OUT/'inputs/containment_verification.json',OUT/'inputs/source_receipt.json']}}
    (out/'interface.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'phase_entries':len(phase_records),'PHW':PHW,'cfg_macros_per_stage':28672,
        'cfg_physical_pins_per_stage':2523136,'snapshot_PASS':True,'cfg_physical_PASS':False}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
