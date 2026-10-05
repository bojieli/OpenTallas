#!/usr/bin/env python3
"""Finite WRACK completion calendar with mandatory consumer events.

Trace fields are provider inputs. This model never generates DRAM visibility or
kernel completion from a timer, and does not qualify any RTL provider.
"""
from fractions import Fraction
FAST=Fraction(10**12,1200000000)
SLOW=Fraction(10**12,900000000)
def crossing(timestamp,period):return (Fraction(timestamp)//period+3)*period

def command_budget(commands):
    buckets={};ticks={};totals={};last={}
    for c in sorted(commands,key=lambda x:Fraction(x['issue_ps'])):
        stack=c['stack'];t=Fraction(c['issue_ps']);kind=c['kind'];size=c['bytes']
        if not 0<=stack<4 or t<0 or t%FAST or kind not in ('read','write'):raise ValueError('invalid scheduled controller command')
        if kind=='write' and size!=32 or kind=='read' and (size<32 or size>1024 or size%32):raise ValueError('illegal LENW6/write1 command')
        tick=int(t/FAST)
        if (stack,tick) in ticks:raise ValueError('one shared read/write command per stack cycle')
        ticks[stack,tick]=1
        credit=min(1024,buckets.get(stack,0)+750*(tick-last.get(stack,-1)))
        if credit<size:raise ValueError('finite read/write byte bucket exhausted')
        buckets[stack]=credit-size;last[stack]=tick
        totals[kind]=totals.get(kind,0)+size
    return totals

def completion_calendar(events,commands,AW=34):
    command_budget(commands)
    issued={}
    for c in commands:
        key=(c['stack'],c['tag'],c['kind'])
        if key in issued or 'sector' not in c:raise ValueError('duplicate command or missing sector ownership')
        issued[key]=(Fraction(c['issue_ps']),c['sector'])
    credits={s:[Fraction(0)]*4 for s in range(4)};locks={};tags=set();out=[]
    for e in sorted(events,key=lambda x:Fraction(x['reserve_ps'])):
        required={'stack','tag','sector','epoch','reserve_ps','column_ps','visible_ps','landing_accept_ps','opcode_finish_ps','result_visible_ps','consumer_done_ps','completion_epoch'}
        if not required<=e.keys():raise ValueError('actual provider schedule/visibility/consumer events required')
        s=e['stack'];tag=e['tag'];sector=e['sector'];epoch=e['epoch']
        if not 0<=s<4 or not 0<=sector<1<<AW or not 0<=tag<65536 or not 0<=epoch<65536:raise ValueError('field aperture')
        if (s,tag) in tags:raise ValueError('tag reuse needs independently proven drain')
        tags.add((s,tag));reserve=Fraction(e['reserve_ps']);slot=min(range(4),key=credits[s].__getitem__)
        if reserve<credits[s][slot] or reserve<locks.get((s,sector),0):raise ValueError('transaction/ACK/sector ownership unavailable')
        write_record=issued.get((s,tag,'write'))
        if write_record is None or write_record[1]!=sector:raise ValueError('command sector differs from completion ownership')
        write=write_record[0]
        if write<crossing(reserve,FAST):raise ValueError('actual scheduled write command required after admitted request')
        if e.get('partial',False):
            if not {'read_return_ps','merge_done_ps'}<=e.keys():raise ValueError('actual RMW completion required')
            read_record=issued.get((s,tag,'read'))
            if read_record is None or read_record[1]!=sector:raise ValueError('RMW read sector differs from owned write')
            read=read_record[0]
            if read<crossing(reserve,FAST) or Fraction(e['read_return_ps'])<read or Fraction(e['merge_done_ps'])<Fraction(e['read_return_ps']) or write<Fraction(e['merge_done_ps'])+FAST:raise ValueError('RMW lifecycle/ingress violation')
        column=Fraction(e['column_ps']);visible=Fraction(e['visible_ps'])
        if column<write or visible<column+7274:raise ValueError('actual WR/visible ordering violation')
        registered=(visible//FAST+1)*FAST;delivered=crossing(registered,SLOW)
        landing=Fraction(e['landing_accept_ps']);finished=Fraction(e['opcode_finish_ps']);result=Fraction(e['result_visible_ps']);done=Fraction(e['consumer_done_ps'])
        if landing<delivered or finished<landing or result<finished or done<result or e['completion_epoch']!=epoch:raise ValueError('landing is not final consumer completion/visibility')
        release=crossing(done,FAST);credits[s][slot]=release;locks[s,sector]=release
        out.append(dict(stack=s,tag=tag,epoch=epoch,ACK_delivery_ps=str(delivered),landing_accept_ps=str(landing),opcode_finish_ps=str(finished),result_visible_ps=str(result),consumer_done_ps=str(done),credit_release_ps=str(release)))
    return dict(status='EVENT_BOUND_MODEL_CALENDAR_PROVIDER_UNQUALIFIED',timeline=out,
        done_ps=str(max((x for rows in credits.values() for x in rows),default=0)),
        full_token_cycles=None,engine_RTL_build_ready=False,physical_admission=False)
