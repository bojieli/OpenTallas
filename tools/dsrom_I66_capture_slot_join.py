#!/usr/bin/env python3
"""Observer-side no-ready capture banking and reserved-slot validation.

Uses actual PHW10 cone writers; does not implement Nash transport or banking
RTL. External slots are proposed until a source/physical owner qualifies them.
No reuse of local indexed admission timing for a resolved remote command.
"""
import argparse
import collections
import copy
import json
from pathlib import Path
import dsrom_I66_actual_service_join as J
S = J.S
OUT = J.R.ROOT/'results/uarch/dsrom_I66_capture_slot_join_20261002'


def bank_layout(events):
    """Extract phase-local bank/row ownership from source root port callbacks."""
    roots = [e for e in events if e['kind']=='root_row_accept']
    if len(roots)!=576:
        raise ValueError('complete source root obligations required')
    banks = collections.defaultdict(list)
    seen=set()
    for e in roots:
        bank=J.uint(e['a'],7);row=J.uint(e['b'],10)
        if row>=576 or row in seen:
            raise ValueError('duplicate or foreign row')
        seen.add(row);banks[bank].append(row)
    if set(banks)!=set(range(128)):
        raise ValueError('all source root ports must be represented')
    return {str(bank):sorted(rows) for bank,rows in sorted(banks.items())}


def capture(events, layout):
    """One write per bank/edge, all row slots retained until source health.

    Reject a bad layout/trace before returning any capture ledger. Deliberate
    source duplicates cannot be hidden by a last-writer-wins dictionary.
    """
    events=copy.deepcopy(events);layout=copy.deepcopy(layout)
    for e in events:
        for key,wanted in dict(rank=0,stage=0,phase=10,key_word=2149580800,reset_era=0).items():
            if type(e[key]) is not int or e[key]!=wanted:
                raise ValueError('source owner/phase/reset identity mismatch')
    for bank,rows in layout.items():
        if type(bank) is not str or bank not in map(str,range(128)):
            raise ValueError('invalid source bank name')
        for row in rows:
            J.uint(row,10)
    source_layout=bank_layout(events)
    if layout!=source_layout:
        raise ValueError('bank layout differs from source row/root ownership')
    slots={row:(int(bank),index) for bank,rows in layout.items() for index,row in enumerate(rows)}
    if len(slots)!=576:
        raise ValueError('all576 no-ready capture credits required')
    roots={e['b']:e for e in events if e['kind']=='root_row_accept'}
    writes=[e for e in events if e['kind']=='VM_write_accept']
    idle=[e for e in events if e['kind']=='phase_retire']
    if len(idle)!=1 or len(writes)!=576:
        raise ValueError('healthy source terminal and all writers required')
    terminal=J.uint(idle[0]['edge']);stored=set();occupied=set();burst=collections.Counter();cells=[]
    last=-1
    for e in writes:
        edge=J.uint(e['edge']);port=J.uint(e['a'],7);row=J.uint(e['b'],30)-398720
        if edge<last or edge>=terminal or row not in slots or row in stored:
            raise ValueError('unordered, late, foreign or duplicate no-ready capture')
        last=edge;bank,index=slots[row]
        if bank!=port or (edge,bank) in occupied:
            raise ValueError('source bank write-port conflict')
        root=roots[row]
        if edge!=root['edge']+1 or e['c']!=root['c']:
            raise ValueError('writer differs from source root/NBA mapping')
        stored.add(row);occupied.add((edge,bank));burst[edge]+=1
        cells.append(dict(edge=edge,bank=bank,slot=index,row=row,address=e['b'],data=e['c']))
    if stored!=set(range(576)):
        raise ValueError('missing no-ready capture row')
    depths=[len(layout[str(bank)]) for bank in range(128)]
    padding=128*max(depths)-576
    return dict(source_healthy_terminal=terminal,all_rows_capture_edge=last,
                peak_writes_per_edge=max(burst.values()),banks=128,
                bank_depth_histogram=dict(collections.Counter(depths)),
                writer_bursts=dict(sorted(burst.items())),captured_rows=576,
                exact_information_bits=576*33+1,
                uniform_depth=max(depths),uniform_extra_slots=padding,
                uniform_payload_occupancy_and_fault_bits=128*max(depths)*33+1,
                source_writer_boundary_bits=128*63,
                field_root_boundary_bits=128*69,cells=cells,
                no_ready=True,other_phase_banking_qualified=False)


def slot_join(captured, reads, publications, ACKs, terminal):
    """Validate a provider's finite read/publish/causal-ACK proposal.

    Reads are explicit reserved bank reads (row/edge); scalar drain cost is
    checked as one read per edge. Source health precedes any publication.
    Publications are row/edge/packet; ACKs are packet/edge. Packet delivery
    itself cannot retire a row without its accepted destination publication.
    terminal denotes the next owner-credit ACCEPT edge, not the same-edge
    postNBA completion receipt. Inclusive ACK-held credit becomes reusable
    on the following edge. This does not add a cycle to a completion signal.
    Actual provider callbacks are a separate gate.
    """
    if len(reads)!=576 or len(publications)!=576:
        raise ValueError('all576 read and publication slots required')
    rows={};read_edges=set();slots={x['row']:x for x in captured['cells']}
    for r in reads:
        row=J.uint(r['row'],10);edge=J.uint(r['edge'])
        if row not in slots or row in rows or edge in read_edges or edge<=captured['source_healthy_terminal']:
            raise ValueError('unowned, duplicate, conflicting or premature bank read')
        rows[row]=edge;read_edges.add(edge)
    packets=collections.defaultdict(list);published=set()
    for p in publications:
        row=J.uint(p['row'],10);edge=J.uint(p['edge']);packet=J.uint(p['packet'],32)
        if row not in rows or row in published or edge<=rows[row]:
            raise ValueError('premature, duplicate or unowned destination publication')
        published.add(row);packets[packet].append(edge)
    ack={}
    for a in ACKs:
        packet=J.uint(a['packet'],32);edge=J.uint(a['edge'])
        if packet not in packets or packet in ack or edge<=max(packets[packet]):
            raise ValueError('duplicate/foreign ACK or ACK before postNBA visibility')
        ack[packet]=edge
    if set(ack)!=set(packets):
        raise ValueError('packet ACK debt remains')
    terminal=J.uint(terminal)
    if terminal<=max(ack.values()):
        raise ValueError('owner retirement precedes causal ACK release')
    return dict(status='PASS_CONDITIONAL_CAPTURE_SLOT_CALENDAR',all_rows=576,
                first_read=min(read_edges),last_read=max(read_edges),
                last_home_publication=max(max(v) for v in packets.values()),
                last_causal_ACK=max(ack.values()),next_owner_accept_edge=terminal,
                owner_phase_service_edges=None,actual_provider_measured=False,
                physical_slots_qualified=False,fulltoken=False)


def replay():
    if S.sha_raw(S.A/'r2_PASS/actual.jsonl.gz')!=S.load(S.A/'r2_PASS/record.json')['actual_journal_sha256']:
        raise ValueError('actual journal hash mismatch')
    events=S.events('r2_PASS');layout=bank_layout(events);ledger=capture(events,layout)
    return dict(schema='opentallas.I66.capture-slot-observer.v1',
                actual_journal_sha256=S.sha_raw(S.A/'r2_PASS/actual.jsonl.gz'),
                scope='Actual PHW10 EID0/phase10 native CONE; no current wholeprogram transfer',
                layout=layout,capture=ledger,
                minimum_healthy_scalar_drain=dict(first_read=ledger['source_healthy_terminal']+1,
                    last_read=ledger['source_healthy_terminal']+576,
                    floor_only=True,selected_transport_or_VM_accepted_slots=False),
                accepted_origins=dict(local_indexed='op10/EIDread11/phase15; actual cone journal',
                    remote_resolved='Requires actual remote command acceptance/lookup/phase callbacks; do not translate indexed five-edge offset',
                    home_program='Needs actual current PHW10 core S_ISSUE/EID/source ownership journal'),
                required_actual_callbacks=['full operation identity on every accepted writer',
                    'bank/slot ownership and each reserved accepted bank read',
                    'all576 accepted home postNBA publications with packet ownership',
                    'causal packet ACK after owned service visibility',
                    'remote source healthy idle and command retire after all debt'],
                current_program_enrollment=False,remote_service_bound=None,
                no_new_build_runtime_or_hardware=True)


def replay_proposal(proposal):
    """Portable offline replay of archived peer slots; no private ROOT reads."""
    proposal=copy.deepcopy(proposal)
    captured=replay()['capture']
    shift=J.uint(proposal['proposed_remote_phase_accept'])-15
    if shift<0 or proposal['proposed_remote_source_idle']!=422+shift:
        raise ValueError('peer source idle detached from calibrated phase body')
    captured['cells']=[dict(c,edge=c['edge']+shift) for c in captured['cells']]
    captured['source_healthy_terminal']=422+shift
    ack=J.uint(proposal['result_packet_ACK_accept'])
    complete_ack=J.uint(proposal['completion_packet_ACK_accept'])
    if complete_ack<ack or proposal['next_owner_credit_accept_floor']!=complete_ack+1:
        raise ValueError('completion packet debt not retained through credit reuse')
    result=slot_join(captured,proposal['minimum_source_scalar_reads'],
                     proposal['proposed_home_postNBA_rows'],
                     [dict(packet=0,edge=ack)],proposal['next_owner_credit_accept_floor'])
    if result!=proposal['join']:
        raise ValueError('peer calendar result not reproducible')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--proposal',type=Path)
    a=p.parse_args();r=replay_proposal(S.load(a.proposal)) if a.proposal else replay()
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
