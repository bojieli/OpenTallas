#!/usr/bin/env python3
"""Additive ME replacement-semantics audit before a prefetch headline.
Fixed historical/corrected source contracts only; no sweep or calendar tuning.
"""
import hashlib
import json
import math
from pathlib import Path
import uarch_model as U
import arch_budget_qwen3 as Q
import hdc_timing as T
import hdc_program as PROGRAM
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('results/uarch/qwen_rom_me_latency_semantics_20261003')


def point(extra,ctx,link):
    p=U.qwen_tp_point(4,6144,link,clock_hz=1200000000,me_lat_extra=extra,ctx=ctx,su_width=64)
    return {k:p[k] for k in ['cycles','layer_chain_cycles','ctx','su_width','exchange']}


def build():
    assert U.QWEN_W12_TP4_ME_EXTRA_SS==112
    source=(ROOT/'tools/uarch_model.py').read_text()
    assert 'QWEN_WIRE_W12["me_lat_extra"] if me_lat_extra is None else me_lat_extra' in source
    old=point(55,8192,'ucie_measured');corrected=point(167,8192,'ucie_measured')
    calibration=point(112,1,'board')
    shape=dict(Q.Q,NH=8,KV=2,FF=3072,V=37984)
    width=Q.I.SU_WIDTH;Q.I.SU_WIDTH=64
    try:prog=PROGRAM.build_program(Q.capped_layout(6144,None,shape))
    finally:Q.I.SU_WIDTH=width
    me=[i for i,f in enumerate(prog) if f.get('unit')==Q.I.UNIT_ME]
    weight=[i for i in me if not prog[i].get('me_wsrc') and not prog[i].get('me_amax')]
    lo,hi=weight[72],weight[76];middle=[i for i in me if lo<=i<hi]
    rows=[]
    for extra in [55,167]:
        k=dict(T.K,red_lv=7,me_lat=T.K['me_lat']+extra)
        iss,_=T.simulate(prog,8191,groups=6144,dyn_shape=dict(H=4096,half=64,HD=128),su_width=64,k=k)
        rows.append(Q.layer_chain(prog,iss,T.dyn_values(8191,groups=6144,H=4096,half=64,HD=128),8192,6144))
    stages=[dict(stage=a['stage'],historical_cycles=a['cycles'],corrected_cycles=b['cycles'],
        wire_debit_cycles=b['cycles']-a['cycles'],ME_contributions=(b['cycles']-a['cycles'])//112)
        for a,b in zip(rows[0]['stages'],rows[1]['stages'])]
    delta=corrected['cycles']-old['cycles'];bodydelta=corrected['layer_chain_cycles']-old['layer_chain_cycles']
    assert len(middle)==6 and bodydelta==672 and delta==24304
    assert len(me)==217 and delta==len(me)*112
    prefix0=rows[0]['stages'][0]['cycles'];prefix1=rows[1]['stages'][0]['cycles']
    ar=old['exchange']['per_allreduce_cycles']
    #Retain the existing+28% serial-domain policy for the scoped calendar
    #debit; don't replace it with measured historical stream-cycle counts.
    ar_debit=2*ar*1.28
    calibration_body=calibration['layer_chain_cycles'];calibration_ar=calibration['exchange']['per_allreduce_cycles']
    return dict(schema='QROM_ME_LATENCY_SEMANTICS_REPRICE_R1',owner='Ampere',calendar_rate_owner='Claude',
        parameter_semantics='explicit me_lat_extra replaces default wire extra; T.K.me_lat=base16+argument',
        base_ME_latency_cycles=T.K['me_lat'],historical_wire_extra_cycles=112,proposed_arithmetic_extra_cycles=55,
        old_effective_ME_latency_cycles=16+55,corrected_me_lat_extra_argument=112+55,
        corrected_effective_ME_latency_cycles=16+112+55,
        generated_program_ME_count=len(me),per_layer_ME_count=len(middle),head_ME_count=len(me)-36*len(middle),
        critical_layer_ME_program_indices=middle,stage_debits=stages,
        historical_point_8K=old,corrected_point_8K=corrected,
        added_wire_cycles_per_layer=bodydelta,added_wire_cycles_per_token=delta,
        added_wire_debit_token_s=delta/1200000000,
        calendar_compute_inputs=dict(historical_prefix_cycles=prefix0,corrected_prefix_cycles=prefix1,
            historical_remaining_body_cycles=old['layer_chain_cycles']-prefix0,
            corrected_remaining_body_cycles=corrected['layer_chain_cycles']-prefix1,
            unchanged_serial_AR_multiplier=1.28,unchanged_projected_AR_cycles_each=ar,
            unchanged_projected_two_AR_debit_cycles=ar_debit,
            historical_rest_cycles=old['layer_chain_cycles']-prefix0+ar_debit,
            corrected_rest_cycles=corrected['layer_chain_cycles']-prefix1+ar_debit,
            additional_nonlayer_head_cycles=delta-36*bodydelta,
            scoped_policy='source-sized compute inputs only; rerun finite service recurrence with real owned source deadlines'),
        L0_calibration=dict(scope='historical TP4/SU64/SMIN7/ctx1; source requests only, strict returns FAIL',
            measured_layer_cycles=4669,model_body_cycles=calibration_body,
            model_AR_cycles_each=calibration_ar,model_layer_cycles=calibration_body+2*calibration_ar,
            measured_body_cycles=2687,measured_AR_cycles_each=991,measured_AR_segments_each=2,
            body_gap_cycles=2687-calibration_body,AR_gap_cycles=1982-2*calibration_ar,
            observed_reducer_LV=7,model_ctx1_auto_reducer_LV=math.ceil(math.log2(4096/64)),
            body_ratio=2687/calibration_body,ratio_current_context_or_SSFF_qualified=False,
            measured_two_segment_AR_transfer_to_UCIe_or_current_SMIN6_qualified=False),
        affected_consumers=['uarch_model_qwen_kv_rate_risk.build passes55 and separately setsT.K.me_lat+=55',
            'uarch_model_qwen_kv_bank_groups and successor inherit that layer/compute debit',
            'uarch_model_qwen_kv_credit17.build passes55 and hard asserts3338body/71AR/451prefix'],
        frozen_credit17_verdict='REJECTED; no mutation, gain recalculation, tuning or build',
        actual_sustained_PHY_Bps=None,corrected_finite_calendar_s=None,corrected_prefetch_rate=None,
        source_scope_transfer=False,headline_admission=False,SSFF_closed=False,
        Claude_next_join='Use explicit167argument and563prefix/4010body for this source-sized8K contract; replace71-cycle UCIe/two-segment calibration only through a scoped source/measurement policy. Recompose finite streaming service before any headline.',
        status='SEMANTICS_CONFIRMED_ADDITIVE_COMPUTE_DEBIT_ONLY')


if __name__=='__main__':
    p=ROOT/OUT/'model-r1.json'
    if p.exists():raise ValueError('preserve verdict')
    p.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
