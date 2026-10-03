"""Default-off CLOCK_REGION cost on combined ROM rows; candidate, not measured."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='results/uarch/clock_region_candidate_composition_20261003/'
DECISION=BASE+'inputs/option_C_decision.json'
QWEN='results/uarch/qwen_rom_calibrated_calendar_20261003/summary-r1.json'
DS='results/uarch/dsrom_s82_token_pricing_20261003/model.json'
OUT=BASE+'model.json'


def compose(decision,qwen,ds):
    p=decision['recommendation']['price_to_model']
    if decision['status']!='MODEL_ONLY_DECISION_RECORD' or decision['recommendation']['qwen_rom']!='C' or decision['recommendation']['deepseek_rom']!='C':
        raise ValueError('explicit candidate optionC required')
    if (p['qwen']['central_cycles'],p['qwen']['bound_cycles'],p['deepseek']['central_cycles'],p['deepseek']['bound_cycles'])!=(506,2024,661,2642):
        raise ValueError('new primitive measurement needs explicit source-bound successor')
    if ds['stages']!=82 or ds['return_RD']!=64 or ds['old_S73_headline_transferred']:
        raise ValueError('current S82/RD64 combined baseline required')
    latency=decision['derivation']['latency'];area=decision['derivation']['area']
    clock=1.2e9;rows=[];profiles={}
    for name,source in [('central','central_thick_metal'),('bound','bound_ss_routed')]:
        delta=decision['derivation']['mesochronous_crossing'][source]['added_cycles']
        if delta!=(1 if name=='central' else 4):raise ValueError('source wander profile changed')
        q=latency[source]['qwen'];d=latency[source]['deepseek']
        qc=q['C']['vs_calibrated']['cycles'];dc=d['C']['cycles']
        if qc!=p['qwen'][name+'_cycles'] or dc!=p['deepseek'][name+'_cycles']:
            raise ValueError('priced latency table differs from CLOCK_REGION authority')
        band=q['C_banded']['vs_calibrated']['cycles']-qc
        qio=q['C_unmerged']['vs_calibrated']['cycles']-qc
        dio=d['C_unmerged']['cycles']-dc
        if min(band,qio,dio)<0:
            raise ValueError('extra banded/IO crossings cannot grant a saving')
        profiles[name]=dict(Qwen_base_cycles=qc,Qwen_banded_extra_cycles=band,
            Qwen_unmerged_IO_extra_cycles=qio,DS_base_cycles=dc,
            DS_source_S73_unmerged_IO_extra_cycles=dio,delta_per_crossing=delta)
        for banded in (False,True):
            for unmerged in (False,True):
                cycles=qc+(band if banded else 0)+(qio if unmerged else 0)
                for base in ('calibrated_current','near_hbm_selected_for_build'):
                    before=qwen['headline_numbers'][base]['token_us']; extra=cycles/clock*1e6
                    rows.append(dict(model='Qwen3-8B_ROM',baseline=base,profile=name,
                        banded_tree=banded,unmerged_IO=unmerged,CLOCK_REGION_cycles=cycles,
                        CLOCK_REGION_us=extra,base_conditional_AR_us=before,
                        combined_conditional_AR_us=before+extra,
                        combined_conditional_AR_tokens_s=1e6/(before+extra),
                        rate_debit_percent=100*(1-before/(before+extra)),
                        combined_MTP_step_us=None,combined_MTP_tokens_s=None,
                        missing_MTP_cost='position-specific verify/draft crossing counts not provided'))
        # S82 stage-only boundaries are 81. The source IO alternative counted
        # 73 source hops at S73. Keep this definitional mismatch explicit;
        # price the additional eight pairs of crossings conditionally, with
        # no inference that either count is an accepted runtime calendar.
        oldhops=decision['derivation']['counts']['deepseek']['stage_hops_S73']
        newhops=ds['stage_hops']['total']
        added_io=(newhops-oldhops)*2*delta
        if added_io<0:raise ValueError('source hop basis does not bind selected DS geometry')
        for unmerged in (False,True):
            cycles=dc+(dio+added_io if unmerged else 0)
            for base in ds['scenarios']:
                before=base['conditional_AR_us'];extra=cycles/clock*1e6
                rows.append(dict(model='DeepSeek_V4.1_ROM_S82',baseline=dict(base),profile=name,
                    banded_tree=False,unmerged_IO=unmerged,CLOCK_REGION_cycles=cycles,
                    CLOCK_REGION_us=extra,base_conditional_AR_us=before,
                    combined_conditional_AR_us=before+extra,
                    combined_conditional_AR_tokens_s=1e6/(before+extra),
                    rate_debit_percent=100*(1-before/(before+extra)),
                    source_IO_hops=oldhops,S82_stage_only_hops=newhops,
                    provisional_extra_S82_IO_cycles=added_io if unmerged else 0,
                    IO_count_equivalence_qualified=False,
                    combined_MTP_step_us=None,combined_MTP_tokens_s=None,
                    missing_MTP_cost='position-specific verify/draft crossing counts not provided'))
    return dict(schema='opentallas.uarch.clock-region-candidate.v1',term='CLOCK_REGION',
        status='CANDIDATE_MODEL_COST_NOT_MEASURED_NOT_ADOPTED',default_enabled=False,
        adopted=False,published_rate=None,measured_primitive_delta=None,
        source_commit='f954ad1ea67f77e8f1a5e86cf48856a96ca650bf',profiles=profiles,rows=rows,stream_clock_hz=clock,
        resources=dict(Qwen_source_optionC=area['qwen']['C'],DS_source_optionC=area['deepseek']['C'],
            DS_geometry_area_transfer_qualified=False,contextual_route_SS_FF_qualified=False),
        double_count_rule='CLOCK_REGION charges only new region FIFO crossings. Existing stage wire/CDC/service terms remain in the baseline. I/O merging gives zero NEW crossing charge, not removal of existing async FIFO/wire costs. Each selected banded or unmerged delta is charged once.',
        limitations=['source DS operation counts are rounded analytical sensitivity probes, not accepted full-program counts',
            'DS unmerged IO S73/source-hop versus S82/stage-only-hop binding is conditional and requires actual endpoint/calendar review',
            'both banded+unmerged Qwen price is conditional on both placement choices being implemented',
            'Qwen baselines and S82 component rows remain conditional models, not newly measured system rates',
            'Beauvoir measured primitive delta and contextual SS60/FF25 replace candidate cost in a future successor; no historical records refreshed'])


def build(root=ROOT):
    names=[DECISION,QWEN,DS];blobs={p:(root/p).read_bytes()for p in names}
    r=compose(*[json.loads(blobs[p])for p in names])
    for p in ['tools/clock_region_candidate_composition.py','tools/uarch_model.py']:blobs[p]=(root/p).read_bytes()
    r['input_sha256']={p:hashlib.sha256(b).hexdigest()for p,b in blobs.items()}
    return r


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verify',action='store_true')
    args=ap.parse_args();p=ROOT/OUT;payload=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    if args.verify:
        if p.read_text()!=payload:raise ValueError('record drift')
    else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(payload)
    print('PASS opt-in CLOCK_REGION candidate combined costs; no measured/adopted rate')
