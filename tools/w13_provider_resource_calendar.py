"""Finite held-WR event calendar under a source-pinned controller model.

Columns require a separately bound DRAM row/bank/refresh eligibility event.
Reserve full pending payload before column issue, retain through visible ACK
and ready. There is no invented stack-global column serialization.
"""
from fractions import Fraction
from math import ceil


def write_calendar(requests, depth, clock_ps, per_PC_interval_ps, visibility_ps, response_ps):
    if type(depth) is not int or depth<1:raise ValueError('pending depth')
    clock=Fraction(clock_ps);interval=Fraction(per_PC_interval_ps)
    visible=Fraction(visibility_ps);rsp=Fraction(response_ps)
    if min(clock,interval,visible,rsp)<=0:raise ValueError('nonpositive service contract')
    def edge(t):return ceil(Fraction(t)/clock)*clock
    held={};pcnext={};address_visible={};calendar=[];identities=set()
    for q in requests:
        required=('id','producer_result_id','payload_sha256','epoch','tag','die','stack','PC','sector',
                  'earliest_column_ps','DRAM_eligibility_source_event','DRAM_eligibility_valid_until_ps',
                  'ACK_ready_ps','byte_mask')
        if any(k not in q or q[k] is None for k in required):
            return {'issues':['source_request_or_service_binding_missing'],'calendar':None}
        if q['id'] in identities:raise ValueError('duplicate request identity')
        identities.add(q['id'])
        if q['byte_mask']!=(1<<32)-1:
            return {'issues':['partial_write_requires_locked_RMW_read_merge_fullwrite'],'calendar':None}
        if type(q['die']) is not int or q['die']<0 or type(q['stack']) is not int or not 0<=q['stack']<4:
            raise ValueError('die/stack topology identity')
        if not 0<=q['PC']<32 or not 0<=q['sector']<1<<34 or not 0<=q['tag']<1<<16 or not 0<=q['epoch']<1<<64:
            raise ValueError('controller identity/address aperture')
        if q['epoch']>=1<<32:
            return {'issues':['source_epoch_LE64_capture_or_generation_mapping_unbound'],'calendar':None}
        stack=(q['die'],q['stack']);pc=(stack,q['PC']);address=(stack,q['PC'],q['sector'])
        pending=held.setdefault(stack,[])
        # Exact same-address ordering includes prior backing visibility; the
        # held descriptor still occupies capacity until its completion ready.
        t=edge(max(Fraction(q['earliest_column_ps']),pcnext.get(pc,0),address_visible.get(address,0)))
        pending[:]=[release for release in pending if release>t]
        while len(pending)>=depth:
            t=edge(min(pending));pending[:]=[release for release in pending if release>t]
        if t>Fraction(q['DRAM_eligibility_valid_until_ps']):
            return {'issues':['capacity_stall_requires_fresh_row_bank_refresh_eligibility'],'calendar':None}
        backing=edge(t+visible);ACK=edge(backing+rsp)
        release=edge(max(ACK,Fraction(q['ACK_ready_ps'])))
        pending.append(release);pcnext[pc]=t+interval;address_visible[address]=backing
        calendar.append({'source_request_id':q['id'],'producer_result_id':q['producer_result_id'],
            'payload_sha256':q['payload_sha256'],'epoch':q['epoch'],'tag':q['tag'],
            'die':q['die'],'stack':q['stack'],'PC':q['PC'],'sector':q['sector'],
            'eligibility_source_event':q['DRAM_eligibility_source_event'],
            'pending_reserved_and_column_ps':str(t),'backing_visible_ps':str(backing),
            'held_ACK_visible_ps':str(ACK),'ACK_ready_release_ps':str(release),
            'column_capacity_stall_ps':str(t-Fraction(q['earliest_column_ps'])),
            'pending_payload_slots_after_reservation':len(pending)})
    return {'issues':[],'calendar':calendar,'depth_per_stack':depth,
        'full_payload_retained_through_ACK_ready':True,
        'arbitrary_ready_backpressure_has_no_free_finite_depth':True,
        'source_epoch_LE64_whole_domain_qualified':False,
        'candidate_epoch32_scope':'low-valued fixture only; no narrowing of IKD1 wire. Full64 capture or proven generation reconstruction/drain required',
        'scope':'conditional source DRAM eligibility and finite captured WR service; reads/RMW/CDC/ingress arbitration must join',
        'actual_provider_credit':False,'hardware_admission':False}
