#!/usr/bin/env python3
"""One physical two-page HC image, full 24-row PMAX6/8 component.

Absolute whole-token allocation and clocks remain the parent compiler's input.
Two starts consume preinstalled disjoint row/tail ranges; no configuration
transfer is needed between projection rows or tail positions.
"""
from lower_hbm_hc_mtp_static_calendar import lower
from lower_hbm_hc_tail_loop_calendar import lower_tail_loop

def lower_native(*,npos,first_row_consumer_cycle,first_tail_consumer_cycle,sink_divisor=7,sink_phase=0):
    if npos not in (6,8):raise ValueError('production PMAX6/8')
    row,rm=lower('row',first_consumer_cycle=first_row_consumer_cycle,sink_divisor=sink_divisor,sink_phase=sink_phase,row=0,slot=0,npos=npos,early=True,clear=True)
    if first_tail_consumer_cycle<first_row_consumer_cycle+24*len(row):raise ValueError('tail overlaps projection programme')
    tail,tm=lower_tail_loop(first_consumer_cycle=first_tail_consumer_cycle,sink_divisor=sink_divisor,sink_phase=sink_phase,npos=npos)
    base=len(row)
    # The actual issuer checks the global PC, including the relocated tail.
    tail=[(w&((1<<223)-1))|(0xc7a1<<240)|((base+i)<<223) for i,w in enumerate(tail)]
    words=row+tail
    if len(words)>2048:raise ValueError('actual two-page programme capacity')
    return words,{'positions':npos,'rows':24,'configuration_words':len(words),'programme_pages':2,
        'row':{'start_base':0,'start_limit':base,'start_loops':24,'ROW_LOOP':1,'body_cycles':base},
        'tail':{'start_base':base,'start_limit':len(words),'start_loops':npos,'TAIL_LOOP':1,'body_cycles':len(tail)},
        'first_row_consumer_cycle':first_row_consumer_cycle,'first_tail_consumer_cycle':first_tail_consumer_cycle,
        'sink_divisor':sink_divisor,'sink_phase':sink_phase,'reconfigure_between_components':False,
        'scope':'HC component image only; absolute parent start slots/VM allocation and physical clock qualification remain required'}
