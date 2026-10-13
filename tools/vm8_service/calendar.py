#!/usr/bin/env python3
"""Finite service schedule planner; never an RTL qualification receipt.

Input is the source-exact xload cadence file: record cycle addr grp data.
Two existing physical banks each issue one read/cycle. Every beat requires
both a write-verification read and a separate publication read. Sixteen
reserved transactions/bank are held until four native receiver ACKs.
"""
import argparse, collections, json

def calendar(arrivals, depth=16, read_latency=6, ack_latency=2, stalls=()):
    ready = collections.deque(arrivals)
    banks = [collections.deque(), collections.deque()]
    events = collections.defaultdict(list)
    publication = {}
    accepted = published = released = 0
    peak = [0,0]
    held = 0
    priorities = [0,0]
    states = {}
    c = arrivals[0]
    while ready or states:
        for stage, seq in events.pop(c, []):
            if stage == 'verified':
                states[seq]['state'] = 'publication_read'
                states[seq]['eligible'] = c + 2 # writeACK + matchingrdrequest
            elif stage == 'checked':
                states[seq]['state'] = 'checked'
                publication[seq] = c
            elif stage == 'released':
                assert states[seq]['state'] == 'published'
                b = seq % 2
                assert banks[b][0] == seq, 'native ACK must retain transaction ordering'
                banks[b].popleft()
                del states[seq]
                released += 1
        if ready and ready[0] <= c:
            b = accepted % 2
            if len(banks[b]) < depth:
                ready.popleft()
                states[accepted] = dict(state='verify_read',eligible=c+1)
                banks[b].append(accepted)
                accepted += 1
            else:
                held += 1
        for b in range(2):
            candidates = [s for s in banks[b] if states[s]['state'] in ('verify_read','publication_read') and states[s]['eligible'] <= c]
            chosen = None
            for kind in (('verify_read','publication_read') if not priorities[b] else ('publication_read','verify_read')):
                chosen = next((s for s in candidates if states[s]['state']==kind),None)
                if chosen is not None: break
            if chosen is not None:
                kind=states[chosen]['state']
                states[chosen]['state']='checking'
                events[c+read_latency].append(('verified' if kind=='verify_read' else 'checked',chosen))
                priorities[b]^=1
            peak[b]=max(peak[b],len(banks[b]))
        if published in publication and not any(start<=c<stop for start,stop in stalls):
            del publication[published]
            assert states[published]['state']=='checked'
            states[published]['state']='published'
            events[c+ack_latency].append(('released',published))
            published+=1
        c+=1
    return dict(beats=accepted,elapsed=c-arrivals[0],source_elapsed=arrivals[-1]-arrivals[0]+1,queue_peak_per_bank=peak,source_held_cycles=held,drain_cycles=c-arrivals[-1]-1,read_ports=2,reads_per_beat=2,read_issue_II=1,ack_latency=ack_latency,status='PLANNING_ONLY_NOT_RTL_QUALIFICATION')

def main():
    p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('--depth',type=int,default=16);p.add_argument('--ack-latency',type=int,default=2);a=p.parse_args()
    traces=collections.defaultdict(list)
    with open(a.trace) as f:
        for line in f:
            rec,cycle,*_=line.split();traces[int(rec)].append(int(cycle))
    print(json.dumps({r:calendar(t,a.depth,ack_latency=a.ack_latency) for r,t in traces.items()},indent=2))
if __name__=='__main__': main()
