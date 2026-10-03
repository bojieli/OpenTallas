"""Join frozen visibility-anchored protocol to the same slot0 phase journal.
Downstream writer delivery is distinct from SU VM consumption. No actual binary,
accepted journal, physical service or ingress exclusion is invented.
"""
from fractions import Fraction
import argparse
import json
from pathlib import Path
import dsrom_I66_slot0_phase_lease as P
import dsrom_I66_credit_visibility_join as G
import dsrom_I66_capture_owner as O
import dsrom_I66_consumer_deadline as D
import dsrom_I66_capture_visibility_successor as N

BASE=Path(__file__).resolve().parents[1]/"results/uarch/dsrom_I66_phase_protocol_join_20261003"

KINDS=('read_accept_reserved','registered_return','consumer_accept','home_visible','credit_return_capture')


def join(lease,samples,protocol_context,protocol_journal,credit_delay,capacity):
    if O.identity(protocol_context)!=O.identity(lease['context']):
        raise ValueError('cross-journal frozen owner differs')
    if type(capacity) is not int or not 1<=capacity<=576:
        raise ValueError('supplied finite capacity; not a selected hardware C')
    phase=P.check(lease,samples,credit_delay)
    credit=G.check(protocol_journal,credit_delay)
    events={}
    for e in protocol_journal:
        if e['kind'] not in KINDS:
            raise ValueError('not accepted source protocol event')
        row=P.V.uint(e['row'],16)
        if row>=576:
            raise ValueError('source row')
        if type(e['time']) not in (int,str,Fraction):
            raise ValueError('exact source time; bool/float forbidden')
        time=Fraction(e['time'])
        if time.denominator!=1 or not lease['start_edge']<=time<=lease['release_edge']:
            raise ValueError('same native clock epoch; no implicit CDC conversion')
        key=(row,e['kind'])
        if key in events:
            raise ValueError('duplicate source protocol callback')
        if e['kind']=='read_accept_reserved' and P.V.uint(e['shard'],1)!=((row%256)//2)//64:
            raise ValueError('cross-journal physical shard')
        events[key]=int(time)
    if len(events)!=576*len(KINDS):
        raise ValueError('complete issue/reply/delivery/visibility/credit join required')
    for row in range(576):
        times=[events[(row,k)] for k in KINDS]
        if not all(a<b for a,b in zip(times,times[1:])):
            raise ValueError('positive registered issue/reply/delivery/visible/credit lifecycle')
    publications={};credit_captures={}
    for s in samples:
        if s['ingress'] is not None:
            publications[s['ingress']['row']]=s['edge']
        for row in s['credit_returns']:
            credit_captures[row]=s['edge']
    if any(publications[r]!=events[(r,'home_visible')] or credit_captures[r]!=events[(r,'credit_return_capture')] for r in range(576)):
        raise ValueError('protocol and actual-sampled publication/credit edges disagree')
    # Source credit crossing is postedge; issue at the same edge sees old debt.
    occupied=set();peak=0;bytime={}
    for (row,kind),time in events.items():
        bytime.setdefault(time,[]).append((row,kind))
    for time,actions in sorted(bytime.items()):
        for row,kind in actions:
            if kind=='read_accept_reserved':
                if len(occupied)>=capacity:
                    raise ValueError('same-edge returned credit cannot fund issue')
                occupied.add(row)
        peak=max(peak,len(occupied))
        for row,kind in actions:
            if kind=='credit_return_capture':
                if row not in occupied:
                    raise ValueError('unowned source credit')
                occupied.remove(row)
    if occupied:
        raise ValueError('unretired source debt')
    phase.update(protocol_rows=credit['rows'],supplied_capacity=capacity,
                 peak_source_credit_debt=peak,hardware_C_selected=False,
                 downstream_delivery_is_SU_read=False,
                 actual_source_enrollment=False,finite_actual_service_bound=None)
    return phase


def encode_header144(values):
    return N.encode(N.widths()['header_fields'],values)


def decode_header144(word):
    return N.decode(N.widths()['header_fields'],word)


def source_plan():
    import hashlib
    pins=json.loads((BASE/'input_pins.json').read_text())
    for name,pin in pins.items():
        if hashlib.sha256((BASE/'inputs'/f'{name}.json').read_bytes()).hexdigest()!=pin['sha256']:
            raise ValueError('selected c9 metadata pin')
    clock=json.loads((BASE/'inputs/selected_clock_model.json').read_text())
    fields=N.widths()['header_fields'];offset=0;layout=[]
    for name,width in fields.items():
        layout.append(dict(name=name,width=width,LSB=offset));offset+=width
    return dict(selected_clock_source=pins,selected_Arch_bank=clock['selected_selector_clock_construction'],
        selected_clock_phase_reset_release=clock['parent_clock_phase_reset_release_control_sink_union'],
        selected_clock_physical_fit_proven=clock['physical_fit'],selected_clock_qualified=False,
        codec_source='6f2c3b8f: capture_visibility_successor.encode/decode, exact LSB-first pinned field order',
        header144_fields_LSB=layout,actual_decoder_implemented=False,scope='ONE_TWO_JOURNAL_PROTOCOL_AND_SLOT0_PHASE_JOIN',
        phase_model=P.source_plan(),Nash_source='6f2c3b8f143fb6cecc5534b6cb9abbbd29166efb',
        distinction='Nash consumer_accept is downstream writer delivery; SU VM read requires separate source-aligned context/tag callback',
        identical_association=['169bit context','physical shard at source issue','row','home_visible edge','captured credit-return edge','qualified native clock epoch'],
        publication_is_actual_only_after_compiled_callback_enrollment=True,
        producer_completion_fence='all576 owned VM-visible before producer-complete permits waiting SU; keep address/version lease separately through consumer reads',
        lease_is_not_unit_busy='holding producer idle false until consumer read would circularly block wait2 consumer; commit and address-lease fences must be distinct',
        necessary_admission_samples=['actualS_ISSUE/PC/d_unit/d_wait/idles/waited/unit_ready/sourceSUcommand accept','latched vector owner/sequence and source-aligned X tags','owned source producer completion/visibility fence, not original cone idle421'],
        scalar_publication_lower_bound='one accepted scalar word/edge: first-to-last visibility span at least575edges plus actual reply/formatter/credit/CDC; not actual consumer deadline',
        actual_deadline_entry='dsrom_I66_consumer_deadline.enrolled_join with current PHW10 compiled ingress/callback/source inverse, exact programs/field, actual consumer journal and reviewed shared service slots',
        compiled_ingress_or_callback_available=False,actual_journal_available=False,
        C=None,stations=None,actual_consumer_deadline=None,RTL_GO=False,new_jobs=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.write_text(json.dumps(source_plan(),indent=2,sort_keys=True)+'\n')
