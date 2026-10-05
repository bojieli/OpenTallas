#!/usr/bin/env python3
"""Finite accepted-edge drain checker. No physical provider or ready is invented.
All times are exact rationals in caller-declared units and origin. Tests use
software schedules; actual admission requires enrolled accepted edges.
"""
from fractions import Fraction
import dsrom_I66_capture_owner as O

def replay(ctx,rows,raw,capacity,issue_edges,return_delays,consumer_edges,visible_edges,ack_edge,credit_return_delay):
    """Replay explicitly offered read slots against finite reserved credits.
    A read slot may go unused when its already-reserved seats are full.
    Consumer edges are *accepted* ready opportunities from the supplied provider,
    not a force-ready waveform. Delivery cannot coincide with registered arrival.
    Delivery ACK and visibility have independent causal evidence.
    """
    def ordered(xs):
        xs=list(map(Fraction,xs))
        if any(b<=a for a,b in zip(xs,xs[1:])):raise ValueError('edge identity/order')
        return xs
    issued_slots=ordered(issue_edges);consumers=ordered(consumer_edges)
    if Fraction(credit_return_delay)<=0:raise ValueError('positive credit return/CDC provider required')
    if set(return_delays)!={0,1} or any(Fraction(x)<=0 for x in return_delays.values()):raise ValueError('positive typed return provider')
    if set(visible_edges)!=set(range(576)):raise ValueError('all causal visibility edges required')
    if set(rows)!=set(range(576)) or set(raw)!=set(rows):raise ValueError('complete capture identity')
    own=O.Owner(ctx,rows,capacity)
    for r in range(576):own.capture(r,rows[r],raw[r])
    own.source_terminal(True)
    # Native source retirement must be bound by caller; this checker starts
    # with that source fence. It does not model new field capture or GO.
    pending={};credit_returns={};physical_reserved=set();journal=[];peak=0;accepted=0;delivery_edges={}
    times=set(issued_slots)|set(consumers)|set(map(Fraction,visible_edges.values()))|{Fraction(ack_edge)}
    issue_set=set(issued_slots);consumer_set=set(consumers)
    # A scheduled return may create a new event; heap avoids a fitted cycle loop.
    import heapq
    heap=list(times);heapq.heapify(heap);queued=set(times)
    while heap:
        edge=heapq.heappop(heap)
        for r in pending.pop(edge,[]):
            own.arrive(r,ctx,raw[r],edge,rows[r]//64)
            journal.append(dict(kind='registered_return',row=r,shard=rows[r]//64,time=str(edge)))
        if edge in consumer_set:
            # Arrival is post-edge data. At this edge, only older data is legal.
            r=own.next_delivery
            if r in own.returned and own.arrival_edges[r]<edge:
                item=own.consume(True,edge);r=item[0];delivery_edges[r]=edge
                journal.append(dict(kind='consumer_accept',row=r,time=str(edge)))
                t=edge+Fraction(credit_return_delay);credit_returns.setdefault(t,[]).append(r)
                if t not in queued:heapq.heappush(heap,t);queued.add(t)
        for r,t in visible_edges.items():
            if Fraction(t)==edge:
                if r not in delivery_edges or edge<=delivery_edges[r]:raise ValueError('visibility before accepted writer/causal provider')
                own.mark_visible(r,ctx);journal.append(dict(kind='home_visible',row=r,time=str(edge)))
        if edge in issue_set and own.next_issue<576 and len(physical_reserved)<capacity:
            r=own.next_issue
            if own.issue(r,ctx,edge,rows[r]//64):
                accepted+=1;physical_reserved.add(r);t=edge+Fraction(return_delays[rows[r]//64])
                pending.setdefault(t,[]).append(r)
                if t not in queued:heapq.heappush(heap,t);queued.add(t)
                journal.append(dict(kind='read_accept_reserved',row=r,shard=rows[r]//64,time=str(edge)))
        peak=max(peak,len(physical_reserved))
        # Credit crossing is captured post-edge and cannot fund same-edge read.
        for r in credit_returns.pop(edge,[]):
            if r not in physical_reserved:raise ValueError('unowned credit ACK')
            physical_reserved.remove(r);journal.append(dict(kind='credit_return_capture',row=r,time=str(edge)))
        if edge==Fraction(ack_edge):own.packet_ack(ctx,edge,True,True)
    if pending or credit_returns or physical_reserved:raise ValueError('unretired source credit debt')
    own.release(True,True,True)
    return dict(verdict='PASS_FINITE_SUPPLIED_EDGE_CONTRACT_ONLY',rows=accepted,peak_reserved_read_seats=peak,
                capacity=capacity,first_consumer_edge=str(delivery_edges[0]),last_consumer_edge=str(delivery_edges[575]),
                packet_delivery_ACK_edge=str(Fraction(ack_edge)),last_home_visible_edge=str(max(map(Fraction,visible_edges.values()))),
                journal=journal,physical_admission=False,actual_provider_enrollment_required=True)
