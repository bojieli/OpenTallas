#!/usr/bin/env python3
"""Exact event-count capacity check for a compiled raw-word CDC window.

Clock periods and epoch phases must come from the selected physical contract.
No ready or data-dependent idle adjustment exists. This model does not supply
an unmeasured physical clock contract or qualify a production calendar.
"""
from fractions import Fraction


def check_window(*, words, write_period_ps, read_period_ps,
                 write_first_ps, read_first_ps, depth, pointer_sync_edges=3):
    if words<=0 or depth<=0 or pointer_sync_edges<0:
        raise ValueError('invalid window size')
    wp,rp,w0,r0=map(Fraction,(write_period_ps,read_period_ps,write_first_ps,read_first_ps))
    if wp<=0 or rp<=0:
        raise ValueError('clock periods must be positive')
    events=[(w0+i*wp,0,i) for i in range(words)]+[(r0+i*rp,1,i) for i in range(words)]
    events.sort()
    writes=reads=peak=sync_peak=0;fail=[]
    for time,kind,index in events:
        if kind==0:
            # A same-time read cannot be relied on to free a slot across CDC.
            cutoff=time-pointer_sync_edges*wp
            visible_reads=max(0,min(words,int((cutoff-r0)//rp)+1))
            sync_peak=max(sync_peak,writes-visible_reads+1)
            if writes-visible_reads>=depth:fail.append({'kind':'synchronized_full_margin','word':index,'time_ps':str(time)})
            if writes-reads>=depth:fail.append({'kind':'overflow','word':index,'time_ps':str(time)})
            writes+=1;peak=max(peak,writes-reads)
        else:
            # Reserve enough age for synchronized write ownership, independent
            # of whether data happens to arrive correctly in this run.
            producer_time=w0+index*wp
            if time-producer_time<pointer_sync_edges*rp:
                fail.append({'kind':'read_before_synchronized_ownership','word':index,'time_ps':str(time)})
            if reads>=writes:fail.append({'kind':'underflow','word':index,'time_ps':str(time)})
            reads+=1
    return {'capacity_pass':not fail,'words':words,'peak_logical_words':peak,'peak_conservative_write_occupancy':sync_peak,'depth':depth,
            'failures':fail,'scope':'known-clock finite epoch capacity only; source/FEC and physical qualification separate'}
