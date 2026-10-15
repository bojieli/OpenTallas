#!/usr/bin/env python3
"""Emit fixed SU/HC row requests/deadlines from an observed full-shape layer.

Does not change the issue timeline or infer native ownership from golden boot
rows. Native service/commit edges require a separately measured contract and
compiler allocation. This artifact is a reservation request, never native
qualification. Fixture producers remain explicitly named.
"""
import argparse
import csv
import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path


def convert(path, metadata=None):
    with path.open() as stream:
        raw = list(csv.DictReader(stream))
    events, jobs, pending = [], [], defaultdict(deque)
    last_write = {}
    unresolved = []
    for line, row in enumerate(raw, 2):
        client, kind = row['client'], row['event']
        cycle, job, slot, addr, tag = (int(row[k]) for k in ('stream_cycle', 'job', 'slot', 'row', 'tag'))
        if client not in ('su', 'hc'):
            # Other row writes are fixture/control-plane sources. This annotates
            # observation only, not whether a physically bound producer exists.
            if kind == 'write':
                last_write[addr] = dict(client=client, job=job, tag=tag, cycle=cycle,
                                        native_producer_bound=False)
            continue
        key = (job, client, slot)
        if kind in ('start', 'done'):
            jobs.append(dict(client=client, tag=tag, job=job, **{kind+'_cycle': cycle}))
            continue
        if kind == 'response':
            if not pending[key]:
                raise ValueError(f'unsolicited response line {line}')
            event = pending[key].popleft()
            # The independently recorded response address may reference a delay
            # stage advanced on this edge. Slot FIFO identity is authoritative
            # here; retain the monitor row so mismatches remain reviewable.
            event.update(deadline_cycle=cycle, observed_model_response_cycle=cycle,
                         response_monitor_row=addr)
            continue
        if kind not in ('read', 'write'):
            raise ValueError(f'unknown client event {kind} line {line}')
        eid = f'{job}/{client}/{tag}/{kind}/{len(events)}'
        event = dict(id=eid, kind=kind, client=client, job=job, slot=slot, row=addr,
                     tag=tag, issue_cycle=cycle, observed_time_ns=row['time_ns'],
                     mask=int(row['mask'], 16), group=f'{job}/{client}/{kind}/{cycle}',
                     native_service_reserved=False)
        if kind == 'read':
            producer = last_write.get(addr)
            event['observed_producer'] = producer or {'client': 'BOOT_OR_GOLDEN', 'native_producer_bound': False}
            pending[key].append(event)
        else:
            last_write[addr] = dict(client=client, job=job, tag=tag, cycle=cycle,
                                    mask=event['mask'], native_producer_bound=False)
            # This is where the bench array is updated, not a native SRAM ACK.
            event['observed_model_commit_cycle'] = cycle
        events.append(event)
    for queue in pending.values():
        unresolved += [e['id'] for e in queue]
    if unresolved:
        raise ValueError(f'{len(unresolved)} requests lack model responses: {unresolved[:8]}')
    done = {(j['job'], j['client'], j['tag']): j['done_cycle'] for j in jobs if 'done_cycle' in j}
    for event in events:
        if event['kind'] == 'write':
            key=(event['job'], event['client'], event['tag'])
            if key not in done:
                raise ValueError(f'write has no job-done boundary {event["id"]}')
            event['deadline_cycle'] = done[key]
    if not events or not any(e['client']=='su' for e in events) or not any(e['client']=='hc' for e in events):
        raise ValueError('full SU/HC trace missing')
    return dict(schema='opentallas.s81.static_vm_trace.v1',
                trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source_metadata=metadata or {}, events=events, jobs=jobs,
                observed_rows=len(raw), client_row_requests=len(events),
                qualified=False, complete_actual_trace=False,
                required=['actual native row producer bindings', 'fixed VM ingress/service edges',
                          'measured physical response/commit bounds and phases',
                          'capture/landing/collective/PQ traffic', 'static occupancy/deadline gate',
                          'unchanged full-layer native replay'],
                scope='Observed real SU/HC client shapes on the layer vehicle; behavioral VM and numerical fixture producers remain')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--meta',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    meta=json.loads(a.meta.read_text()) if a.meta else {}
    result=convert(a.trace, meta)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print('STATIC_VM_TRACE',result['client_row_requests'],'requests; native qualification INCOMPLETE')


if __name__=='__main__':
    main()
