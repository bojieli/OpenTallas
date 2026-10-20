#!/usr/bin/env python3
"""Default-off model of an existing-event shared origin; no RTL, clock, K or image mutation."""
import argparse, json, math
from pathlib import Path

def evaluate(c):
    failures=[]; result=dict(schema='opentallas.qwen.shared-epoch-origin.v1',qualified=False,enabled=False)
    if c.get('enabled') is not False:failures.append('DEFAULT_OFF_REQUIRED')
    if c.get('mode') != 'static_existing_events':failures.append('STATIC_EXISTING_EVENT_CONTRACT_REQUIRED')
    if not c.get('upstream_clock_reset_correlated'):failures.append('UPSTREAM_CLOCK_RESET_CORRELATION_MISSING')
    digest=c.get('origin_receipt_sha256')
    if not isinstance(digest,str) or len(digest)!=64 or any(x not in '0123456789abcdef'for x in digest):failures.append('PRODUCER_CONSUMER_ORIGIN_RECEIPT_MISSING')
    fields=['period_ps','global_source_to_consumer_edges','source_to_native_input_edges','native_output_to_consumer_edges',
            'cal_start_face_global_edge','face_to_cal_start_pin_edges','calendar_input_pr_edges','calendar_output_pr_edges',
            'first_event_dt','last_cfg_core_global_edge','context_pin_global_edge','context_to_first_slot_edges',
            'shared_epoch_global_edge','compiled_boot_edges','source_stores_ready_global_edge']
    for k in fields:
        if type(c.get(k)) is not int and not(k=='period_ps' and isinstance(c.get(k),float)):
            failures.append('MISSING_NUMERIC:'+k)
    kind=c.get('native_kind'); offset,sub,warm=(1,1,3) if kind=='flop' else (3,2,4)
    if kind not in ['flop','sram']:failures.append('NATIVE_CLASS_MISSING')
    if c.get('cases') is None or set(c['cases'])!={'tt','ff'}:failures.append('COMPLETE_TTFF_CASES_REQUIRED')
    if any(x.startswith(('MISSING_NUMERIC:','COMPLETE_TTFF')) for x in failures):
        result.update(status='BLOCKED',blockers=failures);return result
    T=c['period_ps']; A=c['global_source_to_consumer_edges']
    if T<=0:raise ValueError('positive period required')
    if any(c[k]<0 for k in ['global_source_to_consumer_edges','source_to_native_input_edges','native_output_to_consumer_edges','face_to_cal_start_pin_edges','calendar_input_pr_edges','calendar_output_pr_edges','context_to_first_slot_edges','compiled_boot_edges']):
        failures.append('NEGATIVE_PROTOCOL_LATENCY')
    native_global=A-c['source_to_native_input_edges']-c['native_output_to_consumer_edges']
    start_core=c['cal_start_face_global_edge']+c['face_to_cal_start_pin_edges']+c['calendar_input_pr_edges']
    source_first=start_core+c['first_event_dt']+c['calendar_output_pr_edges']
    consumer_first=source_first+A
    if c['first_event_dt']<1:failures.append('ZERO_DT_FORBIDDEN_BY_ACTUAL_CALENDAR')
    if c['last_cfg_core_global_edge']>start_core-2:failures.append('CFG_RECENT_AT_START')
    if c['source_stores_ready_global_edge']>start_core:failures.append('STORE_NOT_READY_NO_WAIT_ALLOWED')
    if c['context_pin_global_edge']+c['context_to_first_slot_edges']>consumer_first:
        failures.append('CONSUMER_CONTEXT_NOT_INSTALLED_BEFORE_FIRST_USE')
    if c['compiled_boot_edges'] != consumer_first-c['shared_epoch_global_edge']:
        failures.append('BOOT_WARM_FIRST_USE_UNPRICED')
    cases={}
    for corner,v in c['cases'].items():
        required=['G_raw','R0_raw','source_origin_global_edge','receiver_origin_global_edge','phi_pin_ps']
        if any(k not in v or not isinstance(v[k],(int,float)) or not math.isfinite(v[k]) for k in required):
            failures.append('INCOMPLETE_ACTUAL_CASE:'+corner);continue
        if any(type(v[k]) is not int for k in ['G_raw','R0_raw','source_origin_global_edge','receiver_origin_global_edge']):
            failures.append('NONINTEGER_RAW_EPOCH:'+corner);continue
        # Origins are actual producer/consumer receipt values. Local L is DERIVED from one compiled global price.
        L=native_global+v['source_origin_global_edge']-v['receiver_origin_global_edge']
        if type(L) is not int:failures.append('NONINTEGER_EDGE_ORIGIN:'+corner);continue
        K=(L+v['G_raw']-v['R0_raw']-sub)%16
        age=(L-offset)*T+v['phi_pin_ps']
        if not(1.25*T+150<=age<=4.125*T-100):failures.append('RESERVED_AGE_WINDOW:'+corner)
        native_input_first_local=source_first+c['source_to_native_input_edges']-v['source_origin_global_edge']
        native_output_first_local=consumer_first-c['native_output_to_consumer_edges']-v['receiver_origin_global_edge']
        if native_input_first_local<v['G_raw']+2:failures.append('SOURCE_WORD_BEFORE_CURRENT_WRITE_EPOCH:'+corner)
        unblock=v['R0_raw']+warm+(K or 16)
        if native_output_first_local<unblock:failures.append('FIRST_READ_BEFORE_WARM:'+corner)
        cases[corner]=dict(L_derived=L,K_model=K,age_ps=age,warm_unblock_local=unblock,
                           native_input_first_local=native_input_first_local,native_output_first_local=native_output_first_local)
    if len(cases)==2 and len({v['K_model']for v in cases.values()})!=1:failures.append('NO_COMMON_IMMUTABLE_K')
    result.update(status='BLOCKED' if failures else 'MODEL_CONSISTENT_NOT_NATIVE_SIGNOFF',blockers=failures,
                  origin_interface='existing fwd_epoch -> cal_start/segment + native_cmd/context; no new ready/credits',
                  native_global_edges=native_global,start_core_global_edge=start_core,
                  first_source_global_edge=source_first,first_consumer_global_edge=consumer_first,
                  mandatory_boot_edges=consumer_first-c['shared_epoch_global_edge'],cases=cases)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('contract',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=evaluate(json.loads(a.contract.read_text()));a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r));return int(r['status']=='BLOCKED')
if __name__=='__main__':raise SystemExit(main())
