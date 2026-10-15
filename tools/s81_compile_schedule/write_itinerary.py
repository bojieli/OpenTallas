#!/usr/bin/env python3
"""Compile fixed bank-write staging slots from a source-pinned output pattern.

All choices happen here before execution. Hardware captures each exact source
port into a compiler-selected storage slot and drains that slot at its reserved
edge. No runtime head/tail arbitration, ready, credits or retry is specified.
An observed fixture pattern is demand evidence only, never native qualification.
"""
from collections import defaultdict
import argparse
import gzip
import hashlib
import heapq
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
from static_vm_reservations import bank_of


def compile_itinerary(requests,contract):
    mapping=dict(banks=32,bank_mapping=contract['bank_mapping'])
    capture_to_drain=contract['capture_to_drain_min_cycles']
    drain_to_commit=contract['drain_to_macro_commit_cycles']
    source_to_storage=contract.get('source_to_storage_capture_cycles',0)
    if type(source_to_storage) is not int or source_to_storage<0:
        raise ValueError('actual source-to-storage pipeline stages required')
    if type(capture_to_drain) is not int or capture_to_drain<1 or type(drain_to_commit) is not int or drain_to_commit<0:
        raise ValueError('exact nonnegative physical pipeline stages required; staging capture precedes drain')
    writes=[dict(e) for e in requests['events'] if e['kind']=='write']
    ids=[e['id'] for e in writes]
    if len(ids)!=len(set(ids)):
        raise ValueError('duplicate write event identity')
    by_bank=defaultdict(list)
    capture_buckets=defaultdict(list)
    for event in writes:
        if type(event['issue_cycle']) is not int or event['issue_cycle']<0 or type(event['row']) is not int or not 0<=event['row']<16384:
            raise ValueError('actual fixed capture edge and physical row required')
        if type(event.get('mask')) is not int or not 0<event['mask']<=65535:
            raise ValueError('actual word mask required')
        for field in ('client','slot','tag','job'):
            if field not in event:
                raise ValueError('source port/context identity missing: '+field)
        bank=bank_of(event['row'],mapping)
        by_bank[bank].append(event)
        capture_buckets[(event['issue_cycle'],bank)].append(event)
    violations=[]
    # Concurrent writes to the same word require an actual compiled ordering
    # contract. A testbench's source-loop priority cannot define chip semantics.
    for (edge,bank),events in capture_buckets.items():
        for i,a in enumerate(events):
            for b in events[i+1:]:
                if a['row']==b['row'] and a['mask']&b['mask']:
                    violations.append(dict(kind='same_edge_word_alias',capture_cycle=edge,events=[a['id'],b['id']]))
    rows=[];bank_peaks={};capture_peaks={};extra_delay=0
    for bank,events in sorted(by_bank.items()):
        next_drain=0;live=[];free=[];allocated=0;peak=0
        for event in sorted(events,key=lambda e:(e['issue_cycle'],e['client'],e['slot'],e['id'])):
            capture=event['issue_cycle']+source_to_storage
            while live and live[0][0]<=capture:
                _,slot=heapq.heappop(live);heapq.heappush(free,slot)
            if free:
                storage=heapq.heappop(free)
            else:
                storage=allocated;allocated+=1
            drain=max(capture+capture_to_drain,next_drain)
            next_drain=drain+1
            heapq.heappush(live,(drain,storage));peak=max(peak,len(live))
            commit=drain+drain_to_commit
            extra_delay=max(extra_delay,drain-capture-capture_to_drain)
            output=dict(id=event['id'],source_port=dict(client=event['client'],slot=event['slot']),
                        job=event['job'],tag=event['tag'],row=event['row'],mask=event['mask'],bank=bank,
                        source_capture_cycle=event['issue_cycle'],capture_cycle=capture,capture_storage_slot=storage,
                        scatter_issue_cycle=drain,drain_storage_slot=storage,macro_commit_cycle=commit)
            if 'deadline_cycle' in event and not event.get('native_done_deadline_missing',False):
                output['native_visibility_deadline_cycle']=event['deadline_cycle']
                if commit>event['deadline_cycle']:
                    violations.append(dict(kind='missed_native_write_visibility',event=event['id'],commit=commit,deadline=event['deadline_cycle']))
            rows.append(output)
        bank_peaks[str(bank)]=peak
        capture_peaks[str(bank)]=max(len(es) for (edge,b),es in capture_buckets.items() if b==bank)
    # Half-open storage lifetime: its reserved drain reads before any reuse on
    # the same edge. This ordering must be implemented in the actual staging.
    edges=[]
    for row in rows:
        edges += [(row['capture_cycle'],1),(row['scatter_issue_cycle'],-1)]
    occupancy=peak_total=0
    for _,delta in sorted(edges):
        occupancy+=delta;peak_total=max(peak_total,occupancy)
    captures=defaultdict(int)
    for row in rows: captures[row['capture_cycle']]+=1
    missing_deadlines=sum('native_visibility_deadline_cycle' not in r for r in rows)
    return dict(schema='opentallas.s81.fixed-write-itinerary.v1',status='DEMAND_ITINERARY_ONLY',
                dispatch_eligible=False,qualified=False,bank_mapping=contract['bank_mapping'],
                capture_to_drain_min_cycles=capture_to_drain,drain_to_macro_commit_cycles=drain_to_commit,
                source_to_storage_capture_cycles=source_to_storage,
                writes=len(rows),write_ids_preserved=sorted(ids)==sorted(r['id'] for r in rows),
                bank_storage_slots=bank_peaks,total_reserved_storage_slots=sum(bank_peaks.values()),
                peak_live_storage_rows=peak_total,max_capture_ports_per_bank=capture_peaks,
                max_total_simultaneous_captures=max(captures.values(),default=0),
                maximum_extra_bank_serialization_cycles=extra_delay,
                missing_native_visibility_deadlines=missing_deadlines,violations=violations,
                original_input_provenance=requests.get('scope'),rows=sorted(rows,key=lambda r:(r['capture_cycle'],r['id'])),
                required=['production allocation and immutable native output template',
                          'actual multiport register staging and compiled drain selection RTL',
                          'true write commit and dependent-read visibility calendars',
                          'physical phase/relay and complete native replay'])


def verify_itinerary(requests, itinerary):
    """Independent table integrity check; never changes a reservation."""
    errors=[]
    source={e['id']:e for e in requests['events'] if e['kind']=='write'}
    rows=itinerary['rows']
    if len({r['id'] for r in rows})!=len(rows) or {r['id'] for r in rows}!=set(source):
        errors.append('write_identity_coverage')
    bank_edges=defaultdict(list);storage=defaultdict(list)
    for row in rows:
        event=source.get(row['id'])
        if event is None:
            continue
        expected=dict(client=event['client'],slot=event['slot'])
        if row['source_port']!=expected or any(row[k]!=event[k] for k in ('row','mask','job','tag')) or row['capture_cycle']!=event['issue_cycle']+itinerary.get('source_to_storage_capture_cycles',0):
            errors.append('source_port_or_payload_identity')
        bank=bank_of(row['row'],dict(banks=32,bank_mapping=itinerary['bank_mapping']))
        if bank!=row['bank']:
            errors.append('wrong_bank')
        if row['scatter_issue_cycle']<row['capture_cycle']+itinerary['capture_to_drain_min_cycles']:
            errors.append('drain_before_capture_available')
        if row['macro_commit_cycle']!=row['scatter_issue_cycle']+itinerary['drain_to_macro_commit_cycles']:
            errors.append('wrong_physical_commit_edge')
        if row['capture_storage_slot']!=row['drain_storage_slot']:
            errors.append('wrong_drain_storage_slot')
        capacity=itinerary['bank_storage_slots'].get(str(bank),0)
        if not 0<=row['capture_storage_slot']<capacity:
            errors.append('storage_slot_out_of_bounds')
        bank_edges[(bank,row['scatter_issue_cycle'])].append(row['id'])
        storage[(bank,row['capture_storage_slot'])].append((row['capture_cycle'],row['scatter_issue_cycle']))
    if any(len(ids)>1 for ids in bank_edges.values()):
        errors.append('bank_write_service_collision')
    for intervals in storage.values():
        ordered=sorted(intervals)
        if any(b[0]<a[1] for a,b in zip(ordered,ordered[1:])):
            errors.append('live_storage_overwrite')
    return dict(status='fail' if errors else 'pass',violations=sorted(set(errors)),qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--requests',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    payload=a.requests.read_bytes()
    raw=gzip.decompress(payload) if a.requests.suffix=='.gz' else payload
    result=compile_itinerary(json.loads(raw),json.loads(a.contract.read_text()))
    result['requests_sha256']=hashlib.sha256(payload).hexdigest();result['contract_sha256']=hashlib.sha256(a.contract.read_bytes()).hexdigest()
    encoded=json.dumps(result,sort_keys=True,separators=(',',':')).encode()+b'\n'
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(gzip.compress(encoded,mtime=0) if a.out.suffix=='.gz' else encoded)
    print(f"{result['writes']} writes; {result['total_reserved_storage_slots']} bank-local slots; peak {result['peak_live_storage_rows']} rows; max bank delay {result['maximum_extra_bank_serialization_cycles']}; {len(result['violations'])} violations")


if __name__=='__main__':
    main()
