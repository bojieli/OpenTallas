#!/usr/bin/env python3
"""Reconcile three source-pinned DS HBM model authorities; no hardware credit.

Replays only analytical composition, never numerical/checkpoint execution. All
historical inputs are retained locally; current pathname currency is independent
of historical byte validity. Fetch is charged once per source expert_fetch op.
"""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import types
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/h3_complete_native_calendar_20261002/authority_reconciliation_r4'

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read_inputs(base):
    manifest=json.loads((base/'input_manifest.json').read_bytes());loaded={}
    for name,entry in manifest.items():
        if name=='snapshot_main':continue
        path=base/'inputs'/entry['archive'];raw=path.read_bytes()
        if path.suffix=='.gz':raw=gzip.decompress(raw)
        if sha(raw)!=entry['sha256']:raise ValueError('retained authority input hash: '+name)
        loaded[name]=raw
    return manifest,loaded

def verify_record_inputs(record,manifest):
    by_hash={entry['sha256'] for key,entry in manifest.items()if key!='snapshot_main'}
    missing=[path for path,h in {**record['inputs'],**record['source_sha256']}.items()if h not in by_hash]
    if missing:raise ValueError('unresolved record source/input pin: '+','.join(missing))

def private_composer(base,manifest,key):
    path=base/'inputs'/manifest[key]['archive']
    module=types.ModuleType('authority_'+sha(path.read_bytes())[:16])
    module.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module

def replay_record(base,manifest,data,record_key,composer_key,*,fusion=False):
    record=json.loads(data[record_key]);verify_record_inputs(record,manifest)
    module=private_composer(base,manifest,composer_key)
    program=json.loads(data['results/rtl/w19_hbm_tp96_program_oreduce.json'])
    sm=module.SMTable([json.loads(data[p])for p in ('results/rtl/w19_sm_real_ops.json','results/rtl/w19_sm_real_ops_oreduce.json')],'ar')
    coll=module.w15_prod(json.loads(data['historical_W15']),'hbm_p48_ss')
    if composer_key=='selected_composer':
        select=json.loads(data['selected_select'])
        if select['parameters']!={'DIG':8,'N':96,'NMAX':512,'P':1024,'PF':256}:raise ValueError('selected wide merge geometry')
        coll['select_cycles']=next(c['cycles']for c in select['cases']if c['case']=='l20_index_topk'and c['exact'])
        module.FUSION['on']=fusion
    fetch=json.loads(data['results/rtl/w19_expert_fetch.json'])['audit_comparison']['exposed_ns']['ar_L0_refresh_postponed']/1000
    result=module.compose(program,sm,coll,fetch,{'n_keys':0})
    expected=record['result']
    for key in ('collectives_on_path','total_us','tokens_s','parts_us','layers','flags'):
        if result[key]!=expected[key]:raise ValueError('historical analytical replay mismatch: '+record_key+'/'+key)
    return result

def charge_fetch_once(program, *, fetch_paid, ns_per_fetch):
    if type(fetch_paid)is not bool or type(ns_per_fetch) not in (int,float)or not math.isfinite(ns_per_fetch)or ns_per_fetch<=0:raise ValueError('positive explicit source-case exposure required')
    count=sum(op['kind']=='expert_fetch'for layer in program['layers']for op in layer['ops'])
    return dict(source_fetch_ops=count,incremental_us=0.0 if fetch_paid else count*ns_per_fetch/1000,
                existing_paid_fetch_preserved=fetch_paid,scope='same exact program and source case only; no hardware qualification')

def reconcile(base):
    manifest,data=read_inputs(base)
    frozen_records={}
    for key in data:
        if key.startswith('frozen_')and not key.startswith(('frozen_input:','frozen_source:')):
            record=json.loads(data[key]);verify_record_inputs(record,manifest)
            frozen_records[key]=dict(record_sha256=manifest[key]['sha256'],producer_field=record['source_commit'],inputs=record['inputs'],source_sha256=record['source_sha256'],current_checkout_exists=manifest[key]['current_checkout_exists'])
    historical=replay_record(base,manifest,data,'results/uarch/w19_hbm_token_ar.json','tools/w19_hbm_token_compose.py')
    selected=replay_record(base,manifest,data,'selected_fused','selected_composer',fusion=True)
    unfused=replay_record(base,manifest,data,'selected_unfused','selected_composer',fusion=False)
    gpu=json.loads(data['results/uarch/hbm_gpu.json']);row=next(r for r in gpu['rows']if r['design']=='v41_hbm_gpu_groupslot')
    program=json.loads(data['results/rtl/w19_hbm_tp96_program_oreduce.json']);kinds=Counter(op['kind']for l in program['layers']for op in l['ops'])
    fetch=json.loads(data['results/rtl/w19_expert_fetch.json']);source=data['tools/uarch_model.py'].decode()
    constants={}
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='HBM_W19'for t in node.targets):
            for kw in node.value.keywords:
                if kw.arg in ('ar_us','ar_unfused_us','collectives','parts_us_fused','mtp_pass_us','drafter_us'):
                    if isinstance(kw.value,ast.Call):constants[kw.arg]={x.arg:ast.literal_eval(x.value)for x in kw.value.keywords}
                    else:constants[kw.arg]=ast.literal_eval(kw.value)
    if (constants['ar_us'],constants['ar_unfused_us'],constants['parts_us_fused'])!=(selected['total_us'],unfused['total_us'],selected['parts_us']):raise ValueError('current HBM_W19 constants differ frozen selected source')
    prod=json.loads(data['historical_W15'])['configs']['hbm_p48_ss_prod']
    current=json.loads(data['results/rtl/w15_hbm_nvls.json'])
    proposal=json.loads(data['Claude_proposal'])
    return dict(schema='DS_HBM_THREE_AUTHORITY_SOURCE_RECONCILIATION_R4',snapshot_main=manifest['snapshot_main'],input_pins=manifest,all8_frozen_record_pins=frozen_records,
        common_shape=dict(model='DeepSeek V4.1 Flash',hidden=5120,layers=40,experts=384,routed_topk=6,
            context=1048576,TP=96,SMs_per_rank=32,head_dies=64,key_block=8,position=program['position']),
        exact_program=dict(sha256=manifest['results/rtl/w19_hbm_tp96_program_oreduce.json']['sha256'],
            operations=sum(kinds.values()),families=dict(kinds),compiled_only=program['compiled_only'],variant=program['variant'],
            source_order='96 output-row slices, full K per row; grouped o-reduce8 contributors+multicast',
            legacy_arch_DAG_to_actual_PC_equivalence_proved=False),
        authorities=[dict(id='legacy_groupslot',row=row,clock_hz=gpu['designs']['v41']['clock_hz'],
            source_program='architecture priced critical path; no actual2213PC service execution',
            collective='fixed125.9us plus1.5bytes/0.9hops/2.0control; approximately188 from125.9/0.668, not265 source calls',
            topology='architecture DAG collective nodes omitted and replaced with fixed fabric constants',
            SM_element=gpu['designs']['v41']['element'],drain_cycles=gpu['designs']['v41']['drain_cycles'],
            source_clock_admission='legacy analytical/TT-derived; no comparator context SS/FF qualification',
            dense_weight_overlap='max(chain,37.4us) optimistic prefetch model',routed_fetch_explicitly_paid=False,
            fusion='architecture-priced dedicated/SU contribution; not selected W19 local-step fusion recipe',
            owner_ACK_CDC_backend_consumer_reverse_service_complete=False),
          dict(id='historical_f99',result=historical,fast_hz=1200000000,serial_hz=900000000,
            fusion=False,quantizer_recipe='historical local node table; selected successor adds z_quant and hc quant source steps',
            select='estimated9*(96*k/64)cycles; indexk512=6912 cycles',fetch_case='ar_L0_refresh_postponed',
            fetch_paid_once=charge_fetch_once(program,fetch_paid=True,ns_per_fetch=133.2)),
          dict(id='selected_71b3ffc5',result=selected,unfused_result=unfused,constants=constants,
            archival_commit='71b3ffc52af932f3e28d70842e879183526e9367',producer_field=json.loads(data['selected_fused'])['source_commit'],
            current_fused_record_missing=not manifest['selected_fused']['current_checkout_exists'],
            current_unfused_record_missing=not manifest['selected_unfused']['current_checkout_exists'],
            fast_hz=1200000000,serial_hz=900000000,select_cycles=419,
            select_geometry=dict(N=96,NMAX=512,P=1024,PF=256,DIG=8),
            select_clock='composition divides419 by W15fit1200480192.0768306Hz; select record supplies cycles, not contextual SS/FF clock',
            fusion='lane-local chained SU base/control savings; true cross-lane steps paid; unchanged golden operations',
            fetch_case='ar_L0_refresh_postponed',fetch_paid_once=charge_fetch_once(program,fetch_paid=True,ns_per_fetch=133.2))],
        collective_geometry=dict(config='hbm_p48_ss_prod',packages=48,endpoints=96,record_bytes=64,
            fit_clock_hz=prod['clock_hz'],product_slot_bytes=prod['slot_bytes'],parameters=prod['parameters'],
            all_reduce='grouped reduce extrapolation',wide_slot_is_literal_physical_word=False,
            slots='ceil(bytes_per_rank/749.7) is assumed product-bandwidth pricing, not implemented wideport proof',
            literal96_endpoint64B_serial_receipt_is_different_geometry=True,current_W15_hash=manifest['results/rtl/w15_hbm_nvls.json']['sha256'],
            historical_W15_hash=manifest['historical_W15']['sha256'],current_W15_matches_historical=False,
            current_W15_selected_numeric_fit_same=current['configs']['hbm_p48_ss_prod']['fit']['all_gather']==prod['fit']['all_gather']),
        refresh=dict(selected_exposure_ns=133.2,exposure_case='ar_L0_refresh_postponed',layer_calls=40,
            paid_us=5.328,refresh_live_cases=fetch['audit_comparison']['exposed_ns_refresh_live_ar'],
            refresh_live_mean_ns=sum(fetch['audit_comparison']['exposed_ns_refresh_live_ar'])/6,
            assumed_controller_PHY=fetch['hbm_model'],finite_background_queue_upper=None,
            replacing_case_requires_subtract_paid_case_before_adding_new_case=True),
        deltas_same_W19_program=dict(historical_to_selected_collective_us=round(selected['parts_us']['collective']-historical['parts_us']['collective'],2),
            local_recipe_change_unfused_us=round(unfused['parts_us']['local']-historical['parts_us']['local'],2),
            selected_lane_fusion_saving_us=round(unfused['parts_us']['local']-selected['parts_us']['local'],2),
            fetch_change_us=0.0),
        current_consumers=dict(legacy='v41_hbm_rows/hbm_gpu.json and v41_hbm_chain-derived speculation/reference rows',
            selected='cons_headline_table tier3 per_user_ar/per_user_mtp, unfused and TMEM sensitivity; cons system ratios use HBM_W19',
            historical_f99='retained W19 prior evidence; not current HBM_W19 selected constants'),
        Claude_proposal=dict(source_sha256=manifest['Claude_proposal']['sha256'],central=proposal['results']['ds_hbm']['central'],
            scope='unadopted proposal over legacy groupslot; cannot add19.04us fetch to already-paid W19 without subtraction',
            assumed_zero_reverse_CDC_or_queue_terms_are_not_finite_production_bounds=True),
        still_UNKNOWN=['actual complete native owner/commonACK/visibility/consumer/reverse/CDC/backend finite service',
            'installed wideport schedule/credits matching product slot geometry','source bound full token actual contender lifetimes',
            'context SS/FF clock, physical/routing/cuts, full token G4','third-party agentic per-request committed-token/verify MTP receipts'],
        authoritative_headline_selected=False,headline_changed=False,hardware_qualified=False,
        CPU_elapsed_converted=False,numerical_execution_launched=False,MTP_rate_qualification=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    base=ROOT/OUT;raw=json.dumps(reconcile(base),sort_keys=True,indent=2).encode()+b'\n';path=base/'reconciliation.json'
    if args.verify:
        if path.read_bytes()!=raw:raise ValueError('authority replay bytes changed')
    else:
        if path.exists()and path.read_bytes()!=raw:raise ValueError('historical verdict overwrite refused')
        path.write_bytes(raw)
    print('PASS three source authorities; historical/unfused/fused analytical replay exact; headline UNKNOWN')
if __name__=='__main__':main()
