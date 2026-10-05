#!/usr/bin/env python3
"""Verify symbolic ownership and bind source hardware sites. No payload/build.

This additive verifier keeps all draft allocation records immutable. It does not
convert a failed allocation or an unbound provider ABI into executable admission.
"""
import argparse, collections, gzip, hashlib, json, math, subprocess
from pathlib import Path
import dsrom_full_owner_compiler as C

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_fixed4096_owner_compiler_20261002'
SOURCES=['rtl/v41die/ot_v41_field_w17w10.sv','rtl/v41die/ot_v41_pair_w17w10.sv',
         'rtl/v41rom/ot_v41_rom_elem_w10.sv','tools/v41_die_images_w17w10.py',
         'tools/v41_fullshape_weight_layout.py']


def dedicated_providers(headers,table_dies=36,head_dies=8):
    """Integer physical assignments, retaining dedicated provider classes.

    Table word =32 E4M3 codes+one UE8M0 scale+10 SECDED =274 bits.
    Head/embed word =16 BF16+10 SECDED =266 bits. These are storage
    addresses; original ME32/WROM ports require an explicit adapter contract.
    """
    tables=[];cursor=0
    for L in (1,14):
        n=f'layers.{L}.engram.embed.weight';h=headers[n];r,k=h['shape']
        sc=headers[n[:-6]+'scale']
        if k!=256 or sc['shape']!=[r,8]:raise ValueError('table block geometry')
        words=r*8;pairs=math.ceil(words/16384)
        tables.append({'tensor':n,'scale_tensor':sc['tensor'],'rows':r,'K':k,'pair_start':cursor,
                       'pairs':pairs,'words':words,'word_data_bits':264,'secded_bits':10})
        cursor+=pairs
    per=math.ceil(cursor/table_dies)
    globals_=[];start=0
    for n in ('embed.weight','head.weight','norm.weight'):
        h=headers[n];elements=math.prod(h['shape']);words=math.ceil(elements/16);pairs=math.ceil(words/16384)
        globals_.append({'tensor':n,'shape':h['shape'],'elements':elements,'pair_start':start,
                         'pairs':pairs,'words':words,'word_data_bits':256,'secded_bits':10})
        start+=pairs
    return {'tables':tables,'table_dies':table_dies,'table_pairs_per_die_ceiling':per,
            'table_physical4096_macros_per_die_ceiling':4*per,
            'table_macro_body_area_per_die_ceiling_mm2':per*31525.4592/1e6,
            'global_tensors':globals_,'head_dies':head_dies,'head_storage_pairs_per_die_ceiling':math.ceil(start/head_dies),
            'table_ports_HBM_or_ROM_provider_ABI_qualified':False,
            'head_compute_shape_and_rowtree_binding_qualified':False,
            'storage_only_table_class_not_layer_q_compute_area':True}


def dedicated_address(layout,tensor,row,col=0,scale=False):
    table=next((x for x in layout['tables'] if tensor in (x['tensor'],x['scale_tensor'])),None)
    if table:
        if not (0<=row<table['rows'] and 0<=col<(8 if scale else 256)):raise ValueError('table coordinate')
        w=row*8+(col if scale else col//32);b=256 if scale else (col%32)*8;bits=8
        per=layout['table_pairs_per_die_ceiling'];kind='table';diecount=layout['table_dies']
        x=table
    else:
        x=next(x for x in layout['global_tensors'] if x['tensor']==tensor)
        idx=row*(x['shape'][1] if len(x['shape'])>1 else 1)+col
        if not (0<=idx<x['elements']):raise ValueError('global coordinate')
        w=idx//16;b=(idx%16)*16;bits=16
        per=layout['head_storage_pairs_per_die_ceiling'];kind='head_storage';diecount=layout['head_dies']
    gp=x['pair_start']+w//16384;die,pair=divmod(gp,per);a=w%16384;mb,logical=divmod(a,8192)
    if die>=diecount:raise ValueError('provider capacity')
    return {'provider_class':kind,'die':die,'pair':pair,'mb':mb,'parity':logical%2,'physical_row':logical//2,
            'bit_range':[b,b+bits],'physical_macros_per_pair':4,'physical_macro_depth':4096,
            'transport_ABI_qualified':False}


def source_receipts():
    out=[]
    for p in SOURCES:
        raw=C.gitread(p)
        if raw!=(ROOT/p).read_bytes():raise ValueError('source currency '+p)
        out.append({'commit':C.PIN,'path':p,'sha256':C.sha(raw)})
    return out


def verify(attempt,out):
    attempt=attempt.resolve();out=out.resolve()
    headers=C.load_headers(BASE/'inputs/tensor_headers.jsonl.gz')
    records=list(C.readrows(attempt/'assignments.jsonl.gz'))
    providers=list(C.readrows(attempt/'provider_assignment.jsonl.gz'))
    field=C.Pool(3375,724).compiled_field()
    np=field['compiled_NP'];nBF=len(field['BF_DUAL_site_IDs']);q=np-nBF
    field.update(physical_macros_per_pair=4,compiled_physical_macros=4*np,
                 compiled_q_sites=q,compiled_BF_dual_sites=nBF,
                 q_frame_area_um2=64825.596,BF_dual_frame_area_um2=142971.9984,
                 source_envelope_area_mm2=(q*64825.596+nBF*142971.9984)/1e6,
                 return_declared_bits=8386*(2*np-128)+2146304,root_public_ports=128,
                 dualcompute_area_and_RNE_WAKE_context_qualified=False)
    byclass=collections.Counter();placed=collections.Counter();missing=[]
    for m in records:
        byclass[m['format']]+=1
        if m['stage'] is None:missing.append({'layer':m['layer'],'alias':m['alias']});continue
        placed[m['format']]+=1
        for si,p,first,n,stride,start,w in m['plans']:
            if p not in field['weight_active_site_IDs']:raise ValueError('inactive weight site')
            if m['format']=='bf16' and p not in field['BF_DUAL_site_IDs']:raise ValueError('BF on q-only site')
    experts={(m['layer'],m['expert'],m['alias'].split('.')[-1]) for m in records if m['expert'] is not None}
    wanted={(L,e,f) for L in range(40) for e in range(384) for f in ('w1','w3','w2')}
    if experts!=wanted:raise ValueError('all384 expert declarations not conserved')
    # Fail closed on duplicate declaration names as well as physical overlaps.
    keys=[(m['layer'],m['alias']) for m in records]
    if len(set(keys))!=len(keys):raise ValueError('duplicate matrix declaration')
    overlap=C.check_global_overlap(records,providers)
    layout=dedicated_providers(headers)
    demand_path=BASE/'inputs/full_product_demand.json.gz'
    demand=json.loads(gzip.decompress(demand_path.read_bytes()))
    model=json.loads((attempt/'model.json').read_text())
    control=[]
    for st in model['stage_stats']:
        phw=st['required_PHW'];control.append({'stage':st['stage'],'phase_count':st['phase_count'],
            'required_PHW':phw,'source_PHW6_fits':st['source_PHW6_fits'],
            'compiled_pair_cfg_bits':np*25*48*(1<<phw),
            'source_PHW6_compiled_pair_cfg_bits':np*25*48*64,
            'cfg_words_per_pair':25*(1<<phw),'cfg_word_bits':48,
            'cfg_load_cycles_per_phase':27,'phase_key_table_bits':32*(1<<phw),
            'config_macro_abstract_and_area_not_bound':True})
    receipt={'schema':'opentallas.fullmodel.owner.closure.v1','candidate':'DS4096-TP4-S58-PAIR1',
             'source_pins':source_receipts(),'compiled_field':field,'declaration_counts_by_format':byclass,
             'placed_counts_by_format':placed,'all40_all384_expert_triples_declared':len(experts)==40*384*3,
             'unallocated_matrices':missing,'capacity_verdict':model['capacity_verdict'],
             'first_allocation_failure':model['allocation_failures'][0] if model['allocation_failures'] else None,
             'minimum_stage_claim':False,'overlap_and_rowtree_gate':overlap,
             'dedicated_provider_layout':layout,
             'descriptor_bridge_commit':'5633bfee064231573aafbf236571f63965b30944',
             'descriptor_demand_sha256':C.sha(demand_path.read_bytes()),
             'actual_instruction_descriptors':sum(n['kind']=='instruction' for n in demand['nodes']),
             'actual_runtime_actions':sum(n['kind']=='runtime_action' for n in demand['nodes']),
             'all_descriptor_node_rank_provider_and_calendar_bindings_complete':False,
             'next_gate':'Join actual descriptor IDs and rank slices to physical providers and causal finite service calendars; no engine alias from field274 to ME32/QE.',
             'source_config_storage_debit_separate_from_weight_ROM':True,
             'compiled_control_declarations':control,
             'draft_active_only_charges_rejected':{'draft_weight_macros':4*3375,'actual_compiled_weight_macros':4*np,
                'draft_control_count':3375,'actual_compiled_control_count':np},
             'config_area_ports_PHW_and_dispatch_not_qualified':True,
             'compiled_padding_cannot_be_replaced_by_active_mask':True,
             'RTL_or_PR_jobs':0,'payload_bytes_read':0,'physical_admission':False,'full_token_admission':False,
             'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in
                 [attempt/'assignments.jsonl.gz',attempt/'provider_assignment.jsonl.gz',attempt/'compiler_source.py',
                  BASE/'inputs/tensor_headers.jsonl.gz',BASE/'inputs/header_capture.json',demand_path]}}
    out.mkdir(parents=True,exist_ok=False)
    (out/'closure.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'capacity':receipt['capacity_verdict'],'declared':len(records),'placed':sum(placed.values()),
                      'missing':len(missing),'compiled_physical_macros':4*np,'descriptor_bindings_complete':False}))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();verify(a.attempt,a.out)
