"""Actual event-source ownership association; prefix only, no finite upper bound."""
import hashlib,json,re
from tools.w17_D1_terminal_owner_receipt import parse,lower_bound
P='tb_D1_scope_core__DOT__';D=P+'probe__DOT__dut__DOT__';C=D+'u_tile__DOT__u_core__DOT__';L=D+'g_packed_kv__DOT__u_desc_life__DOT__';W=D+'g_packed_kv__DOT__g_window_hbm_attention__DOT__u_source__DOT__u_window__DOT__'

def qualify(descriptor, read):
    """Use observed source output desc_accept, not a reconstructed absent gate.

    Pinned die binds lifecycle desc_v to kvd_v and the actual selected service
    start predicate. The source observer calls its unique descriptor format
    only under att_packed_desc_accept; IDLE/next-generation values are read at
    that call before NBA. Read marker is similarly under actual slot0 v/rdy.
    """
    for values in (descriptor,read):
        if any(type(v) is not int or v < 0 for v in values.values()):raise ValueError('invalid source field type/range')
        if values[D+'rst_s']!=3:raise ValueError('unsynchronized reset')
        for name in [D+'fault_r',D+'att_packed_desc_fault',D+'win_service_fault',C+'e_fault',P+'probe__DOT__g_D1_current__DOT__violations']:
            if values[name]:raise ValueError('source/ledger fault has precedence')
    if descriptor[D+'att_packed_desc_accept']!=1 or descriptor[D+'kvd_v']!=1 or descriptor[L+'state']!=0:
        raise ValueError('authoritative descriptor admission false/wrong phase')
    generation=descriptor[L+'last_gen']+1
    # First same-reset fixture transaction only; no generation-wrap claim.
    if descriptor[L+'last_gen']!=0 or generation!=descriptor[L+'next_gen'] or generation!=descriptor[D+'att_packed_desc_gen']:
        raise ValueError('source next generation mismatch')
    shape=dict(pos=127,tiles=4,k=512,nout=128,wbase=0,ts=512,ks=1,js=0,hg=1,mmode=1)
    if descriptor[D+'step_user']!=0 or descriptor[D+'att_packed_desc_rows']!=128 or descriptor[L+'incoming_rows']!=128:
        raise ValueError('descriptor user/rows mismatch')
    for key,expected in shape.items():
        if descriptor[C+'me_'+key]!=expected:raise ValueError('source descriptor shape mismatch')
        if read[L+'active_'+key]!=expected:raise ValueError('read descriptor identity mismatch')
    if read[L+'state']!=1 or read[L+'active_gen']!=generation or read[D+'win_service_gen']!=generation:
        raise ValueError('read owner generation/phase mismatch')
    if read[L+'active_rows']!=128 or read[L+'active_user']!=0 or read[W+'active_user']!=0:
        raise ValueError('read owner user/rows mismatch')
    if read[D+'att_packed_desc_accept']!=0 or read[W+'state']!=5 or read[W+'row']!=0 or read[W+'sec']!=0 or read[W+'active_row']!=0:
        raise ValueError('first source refill acceptance state mismatch')
    if read[P+'diag_cycle']<=descriptor[P+'diag_cycle']:
        raise ValueError('stale/read phase before descriptor')
    return dict(status='ACTUAL_SOURCE_DESCRIPTOR_TO_FIRST_READ_OWNER_ASSOCIATION',generation=generation,user=0,pos=127,rows=128,
                descriptor_guard='Observed att_packed_desc_accept1 + IDLE + kvd_v1; source-bound composed desc_v; optimized separate start-ready fields not synthesized.',
                core_ME_admission='NOT_IMPLIED',writer_ownership='NO_WRITE_OBSERVED',service_bound='BOUND_MISSING')


def review(text,receipt,plan,original_terminal_plan):
    events={};blocks=list(re.finditer(r'D1_SOURCE_EVENT_(DESCRIPTOR|READ)_BEGIN\n(.*?)D1_SOURCE_EVENT_END\n',text,re.S))
    if len(blocks)!=2 or [m[1] for m in blocks]!=['DESCRIPTOR','READ']:
        raise ValueError('event cardinality/order')
    for m in blocks:
        kind=m[1];fields=re.findall(r'^D1_EVENT_(\d{3}) value=(\d+)$',m[2],re.M)
        if len(m[2].strip().splitlines())!=105 or [int(i) for i,v in fields]!=list(range(105)):
            raise ValueError('event field order/type/count')
        values={}
        for (name,meta),(_,v) in zip(plan['fields'].items(),fields):
            value=int(v)
            if value>=2**(8*meta['bytes']):raise ValueError('event storage width')
            values[name]=value
        events[kind]=values
        marker='D1_REAL_DESCRIPTOR' if kind=='DESCRIPTOR' else 'D1_REAL_ACCEPT'
        if not text[m.end():].startswith(marker+' '):raise ValueError('source marker/event phase not adjacent')
    association=qualify(events['DESCRIPTOR'],events['READ'])
    ds=re.findall(r'^D1_REAL_DESCRIPTOR time=(\d+) generation=(\d+) rows=(\d+)$',text,re.M)
    requests=re.findall(r'^D1_REAL_ACCEPT time=(\d+) address=(\d+) tag=(\d+) write=(\d+)$',text,re.M)
    if len(ds)!=1 or tuple(map(int,ds[0][1:]))!=(association['generation'],128):
        raise ValueError('descriptor marker/source generation mismatch')
    # Frozen fixture window region base262144; first FR row0/sector0 maps to
    # its first sector with initial tag0. This is not a generic tag convention.
    if len(requests)!=1 or tuple(map(int,requests[0][1:]))!=(262144,0,0):
        raise ValueError('first selected fixture request identity mismatch')

    # Reuse checked final snapshot/argv/hash/priming review, stripping only new
    # event blocks. Raw receipt stays untouched; projection gets its own hash.
    projection=re.sub(r'D1_SOURCE_EVENT_(?:DESCRIPTOR|READ)_BEGIN\n.*?D1_SOURCE_EVENT_END\n','',text,flags=re.S)
    projected_receipt={**receipt,'log_SHA256':hashlib.sha256(projection.encode()).hexdigest()}
    if receipt['log_SHA256']!=hashlib.sha256(text.encode()).hexdigest():raise ValueError('raw hash mismatch')
    live={'actual_argv':receipt['actual_argv']}
    result=parse(projection,projected_receipt,original_terminal_plan,live)
    if result['descriptor_accept_sample_ps']>=result['read_accept_sample_ps']:raise ValueError('accepted service origin before descriptor')
    return dict(status='ACTUAL_ENROLLED_OWNED_FIRST_RETURN_EXPERIMENTAL_PREFIX_ONLY',association=association,event_values=events,
        final_snapshot=result['owner_values'],reset_qualified_rows=result['priming']['rows'],
        service_origin_ps=result['read_accept_sample_ps'],descriptor_origin_ps=result['descriptor_accept_sample_ps'],reply_ps=result['read_reply_sample_ps'],
        observed_request_reply_cycles=result['actual_reply_delta_cycles'],conditional_stage_lower_bound=lower_bound(result['actual_reply_delta_cycles']),
        universal_upper_bound=None,first_return_deadline=None,service_bound='BOUND_MISSING',
        fulltoken=False,RTL_fidelity='UNPROVEN_HAND_PAIRED_NATIVE',X_ROM=0,ROM_PHW=6,I66_origin=None,
        source_clock_ps=1000,clock_is_not_physical_timing_qualification=True,program_SHA256=plan['program']['SHA256'])
