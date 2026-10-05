"""Finite held-WR event calendar under a source-pinned controller model.

Columns require a separately bound DRAM row/bank/refresh eligibility event.
Reserve full pending payload before column issue, retain through visible ACK
and ready. There is no invented stack-global column serialization.
"""
from fractions import Fraction
from math import ceil
import ast,hashlib,subprocess


def source_epoch64_contract():
    """Full producer64 plus distinct transport32 repriced proposal, not RTL."""
    rev='c4f152571';path='tools/qwen_hbm_complete_controller_prereqs.py'
    raw=subprocess.check_output(['git','show',rev+':'+path]);tree=ast.parse(raw)
    nodes=[n.value for n in ast.walk(tree) if isinstance(n,ast.keyword) and n.arg=='source_epoch_contract']
    if len(nodes)!=1:raise ValueError('ambiguous producer epoch contract')
    values={k.arg:ast.literal_eval(k.value) for k in nodes[0].keywords if k.arg in ('producer_epoch_bits','transport_epoch_bits')}
    assert values=={'producer_epoch_bits':64,'transport_epoch_bits':32}
    format_path='tools/deepseek_hbm_complete_packed_index_provider.py'
    fmt=subprocess.check_output(['git','show','e5d9ad00a:'+format_path])
    assert b"struct.pack('<4sBBHQ'" in fmt and b'0<=epoch<2**64' in fmt
    return dict(values,source_pin={'git':rev,'path':path,'sha256':hashlib.sha256(raw).hexdigest()},
        source_format_pin={'git':'e5d9ad00a','path':format_path,'sha256':hashlib.sha256(fmt).hexdigest()},
        captured_queue_epoch_bits_per_entry=96,captured_WR_pending_epoch_bits=96,
        actual_provider_qualified=False)


def write_calendar(requests, depth, clock_ps, per_PC_interval_ps, visibility_ps, response_ps, epoch_capture_contract=None):
    if type(depth) is not int or depth<1:raise ValueError('pending depth')
    clock=Fraction(clock_ps);interval=Fraction(per_PC_interval_ps)
    visible=Fraction(visibility_ps);rsp=Fraction(response_ps)
    if min(clock,interval,visible,rsp)<=0:raise ValueError('nonpositive service contract')
    full64=epoch_capture_contract is not None
    if full64 and epoch_capture_contract!=source_epoch64_contract():
        return {'issues':['source_epoch_capture_contract_not_bound_to_repriced_source'],'calendar':None}
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
        if type(q['epoch']) is not int or not 0<=q['PC']<32 or not 0<=q['sector']<1<<34 or not 0<=q['tag']<1<<16 or not 0<=q['epoch']<1<<64:
            raise ValueError('controller identity/address aperture')
        if full64 and (type(q.get('transport_epoch')) is not int or not 0<=q['transport_epoch']<1<<32):
            return {'issues':['independent_transport_epoch32_binding_missing'],'calendar':None}
        if not full64 and q['epoch']>=1<<32:
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
            'producer_epoch64':q['epoch'],'transport_epoch32':q.get('transport_epoch'),
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
        'model_capture_contract':epoch_capture_contract,
        'model_full64_producer_representation_verified':full64,
        'candidate_epoch_scope':('source-repriced producer64 plus independent transport32 model; actual capture/routes/drain unqualified' if full64 else
            'low-valued fixture only; no narrowing of IKD1 wire. Full64 capture or proven generation reconstruction/drain required'),
        'scope':'conditional source DRAM eligibility and finite captured WR service; reads/RMW/CDC/ingress arbitration must join',
        'actual_provider_credit':False,'hardware_admission':False}
