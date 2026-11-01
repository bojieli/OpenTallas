#!/usr/bin/env python3
"""Prepare an explicit, unadopted IDXQ source/ABI request from real HGI rows.

This does not edit the accepted graph, allocate targets, reuse retired routes,
select a physical view, or manufacture missing native data. Current typed
producer paths must be attached from Binder's post-compose observation.
"""
import argparse, hashlib, json
from pathlib import Path

QUARTERS = (('SW',0,171),('SE',1,171),('NW',2,173),('NE',3,171))
FIELDS = {'n_rows':(769,5),'row_pitch':(774,12),
          'weight_row_stride':(786,16),'query_row_stride':(802,16)}

def request(cohort_path, typed_path=None):
    raw=cohort_path.read_bytes(); cohort=json.loads(raw)
    records=[]
    for rec in cohort['index_records']:
        row=rec['rowx']; rs=row['rs']
        if not 1<=row['n']<=8 or rs['A']%8 or rs['B']%8:
            raise ValueError('Unrepresentable actual HGI row/sector count')
        qstride,wstride=rs['A']//8,rs['B']//8
        if wstride%4 or qstride%4:
            raise ValueError('Actual HGI row stride violates native reader contract')
        records.append(dict(record=rec['record'],offset=rec['offset'],n_rows=row['n'],
            query_row_stride=qstride,weight_row_stride=wstride,
            source_query_stride_words=rs['A'],source_weight_stride_words=rs['B'],
            global_nkeys=rec['imm_a'],param=rec['param'],
            row_pitch=None,row_pitch_status='REQUIRES_CURRENT_BOUND_CALENDAR',
            HOST_source='Expanded IDXQ818 collar from real six-row operand packet'))
    if len(records)!=8 or any(r['n_rows']!=6 for r in records):
        raise ValueError('Expected the actual eight N6 INDEX occurrences, not a synthetic cohort')
    typed=None
    if typed_path:
        typed=dict(path=str(typed_path),sha256=hashlib.sha256(typed_path.read_bytes()).hexdigest(),
                   report=json.loads(typed_path.read_text()))
    connections=[]
    for q,sid,rt in QUARTERS:
        reader={'role':'IDX_operand_reader','quarter':q,'prospective_master':'ot_hnx_idx_vm_query_static_n12'}
        qctl={'role':'IDX_quarter_calendar','quarter':q,'prospective_master':'ot_hnx_idxq_qctl'}
        collar={'role':'CURRENT_IDX_COLLAR_REPLACED_IN_PLACE','prospective_master':'ot_hbm_static_cfg_collar_idxq818'}
        for port,width,source in [
            ('frame_start',1,dict(producer=qctl,port='frame_start',low=0)),
            ('weight_row_stride',16,dict(producer=collar,port='prm',low=786)),
            ('query_row_stride',16,dict(producer=collar,port='prm',low=802))]:
            connections.append(dict(consumer=reader,port=port,width=width,source=source,
                kind='REAL_REGISTERED_PRODUCER_NEW_SOURCE_ROUTE',
                current_cell_paths='PENDING_TYPED_BINDER_ROSTER_RESOLUTION',
                reuse_retired_L124=False,physical_route=None,cohort_arrival_edge=None))
    return dict(schema='opentallas.hbm.idxq.source_overlay_request.v1',
        status='SOURCE_ONLY_UNADOPTED; CURRENT_TYPED_INSTANCE_RESOLUTION_AND_NEW_ROUTE_COHORT_DATES_REQUIRED',
        may_generate_physical=False,current_graph_changed=False,native_required_tied=False,
        source_cohort=dict(path=str(cohort_path),sha256=hashlib.sha256(raw).hexdigest(),records=records),
        new_reader_connections=connections,
        host_fields={name:dict(prm_low=low,width=width,operand_low=424+low-769)
                     for name,(low,width) in FIELDS.items()},
        host_contract=dict(old_packed_bits=769,new_packed_bits=818,additional_bits=49,
            operand_rows=[0x800+i for i in range(6)],new_operand_range=[424,472],
            existing_low769='BYTE_IDENTICAL',current_IDX256R_accepts_extension=False,
            initialize_before_arm=True,hold_through_record=True),
        quarter_profiles=[dict(quarter=q,SID=sid,reader_VM_RT_EXTRA=rt,reader_WEIGHT_FP32=1,
            new_reader_declared_pin_bits=3319,current_reader_declared_pin_bits=3286,
            current_reader_supports_WEIGHT_FP32=False,
            qctl=dict(master='ot_hnx_idxq_qctl',K=8,S=4,CW=2,DELIVERED_RESET=1,ROW_CLEAR_DELAY=rt-2),
            frame_start='ONCE_PER_RECORD; not row_start',query_clear='qctl.row_start, once per row',
            keybuf_provider=dict(master='ot_hnx_idxn_kb_ctl',clear='qctl.frame_start',
                live_v='qctl.key_v && key_row==0',replay_v='qctl.key_v && key_row!=0',
                live_index='qctl.key_index',replay_index='qctl.key_index',
                pre_v='qctl.pre_v',pre_index='qctl.pre_index')) for q,sid,rt in QUARTERS],
        source_closure=['rtl/hbm_next/idx/ot_hnx_idx_vm_query_static_n12.sv',
            'rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv','rtl/lib/ot_rst_relay.sv'],
        contracts=dict(clock_ps=833,weight_values='32 BF16 values widened to FP32; all low16 zero else HGI E_RANGE',
            weight_base_alignment_sectors=4,weight_sector_requests_per_row=4,
            query_base_alignment_words=8,query_offsets_qualified=[2,7],query_bank_wrap_qualified=True,
            row_stride_units='256-bit VM sectors; derived from actual FP32 words/8',
            first_operand_slot='At least one reader input edge after frame_start; base/stride fields already stable',
            row_base_step='query_slot && query_index==127; no frame_start at intermediate rows',
            reader_reset='Existing SYNC2/TREE1 relay: three relay edges plus consumer edge; retain reset4 state contract',
            reader_capture_added_edges=0,vm_requests_added_per_N6=12,
            root_service=dict(VM_RT=75,CR_RT=36,SEL_LAT=40,RSTL=1,FAN32='retain actual service value',argmax_m_bits=264),
            current_native_inputs=152,new_prospective_IDX_controls=28),
        selector_link_request=dict(selector_count=4,additional_selectors=3,additional_SRAM=36,
            input_per_selector=1184,sparse_expansion='For each q: {296zero, actual296}; no compressed-quarter alias',
            output_per_selector=2368,valid_per_selector=4,link_input_line_bits=9472,
            link='ot_hnx_idxq_link + ot_hnx_idxn_link from donor859b27b6b; not yet current source selected',
            single_delivering_selector_per_edge=True,source_faults='All real qctl/reader/query/keybuf/scorer/selector/link faults connected'),
        component_evidence=dict(weight_mode='6ae1c6453:results/tok_hbm_codex_1029/idx_fp32/result.json',
            query_alignment='a1d3c708f:results/tok_hbm_codex_1029/idx_source_layout/result.json',
            numeric_heads=192,blocks=768,rows=6,reader_requests=3096,profiles=[171,173],
            component_example_pitch=328,component_example_only=True,
            source_defaults='WEIGHT_FP32=0 unchanged; prospective mode1 is a new source/ABI, no old view alias'),
        typed_current_source=typed,
        held=['New 49-bit HOST fanout and each 33-bit reader connection need actual source-cell/port/bit identities and new physical routes/cohort dates',
            'No retired L124/L124m presumed route; no current C11E interface change',
            'South key_lines active for global524288/1048576; no nkeys0 or absent-provider tie',
            'Correct per-SID or actual mirror data residency and legal BF16-widened payloads required',
            'No current row_pitch/global programme timeline inferred from the component book',
            'Full qctl/reader/query/keybuf/scorer/four-selector/link composition and current delivered-reset proof remain before adoption',
            'Physical prep/pinmap only; no PNR, source-default change or full G5 claim'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cohort',type=Path,required=True)
    p.add_argument('--typed-current',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('New output required; preserve the prior request')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(request(a.cohort,a.typed_current),indent=2)+'\n')
