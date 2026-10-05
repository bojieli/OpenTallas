#!/usr/bin/env python3
"""Per-PC finite supplied-event service model, not an actual RTL provider.

Price/storage prerequisite: controller_source_prerequisites_r4.json. This
exercises controls only; no checkpoint data, golden or RMW arithmetic is run.
"""
from fractions import Fraction
from math import ceil
from qwen_hbm_complete_common36 import pc_of
FAST=Fraction(2500,3)
SLOW=Fraction(10000,9)

class Capture:
    def __init__(self,depth=5,ACK_depth=4):
        if type(depth) is not int or depth<1 or type(ACK_depth) is not int or ACK_depth<1:
            raise ValueError('finite geometry')
        self.depth=depth;self.ACK_depth=ACK_depth;self.pending={};self.ACK={};self.locks={};self.next_column={};self.last_return={}
        self.seen=set()

    @staticmethod
    def identity(q):
        required={'die','stack','PC','sector','tag','producer_epoch','transport_epoch','instruction','position'}
        if set(q)!=required:raise ValueError('complete identity')
        for field,bits in [('producer_epoch',64),('transport_epoch',32),('sector',34),('tag',16)]:
            if type(q[field]) is not int or not 0<=q[field]<1<<bits:raise ValueError('identity width')
        if q['die'] not in (0,1) or not 0<=q['stack']<4 or q['PC']!=pc_of(q['sector']):raise ValueError('physical owner')
        return tuple(q[k] for k in sorted(required))

    @staticmethod
    def edge(t):return ceil(Fraction(t)/FAST)*FAST
    @staticmethod
    def address(q):return q['die'],q['stack'],q['sector']
    @staticmethod
    def channel(q):return q['die'],q['stack'],q['PC']

    def lock_partial(self,q,mask):
        ident=self.identity(q);address=self.address(q)
        if not 0<mask<0xffffffff or address in self.locks or sum(a[0]==q['die'] for a in self.locks)>=4:raise ValueError('partial ownership')
        self.locks[address]=dict(identity=ident,mask=mask,read_retired=None,merged=None)

    def read_import_retired(self,q,time):
        lock=self.locks[self.address(q)]
        if lock['identity']!=self.identity(q) or lock['read_retired'] is not None:raise ValueError('read owner')
        lock['read_retired']=Fraction(time)

    def merge_result(self,q,opcodes,issue,result):
        lock=self.locks[self.address(q)];issue,result=Fraction(issue),Fraction(result)
        if lock['identity']!=self.identity(q) or opcodes!=('XOR','AND','XOR') or lock['read_retired'] is None or lock['merged'] is not None:
            raise ValueError('actual read/merge callback identity')
        if issue<lock['read_retired'] or result<issue+27*SLOW:raise ValueError('merge latency')
        lock['merged']=result

    def column(self,q,time,mask,eligibility_event,eligibility_until):
        ident=self.identity(q);channel=self.channel(q);now=Fraction(time);address=self.address(q)
        if now!=self.edge(now) or eligibility_event is None or eligibility_until is None or now>Fraction(eligibility_until):
            raise ValueError('source DRAM eligibility/clock binding')
        if ident in self.seen:raise ValueError('duplicate identity')
        lock=self.locks.get(address)
        if lock and lock['identity']!=ident:raise ValueError('persistent address lock')
        if mask!=0xffffffff:
            if lock is None or lock['mask']!=mask or lock['merged'] is None or now<lock['merged']+FAST:
                raise ValueError('partial needs completed locked RMW')
        elif lock is not None:raise ValueError('masked RMW cannot bypass as fullwrite')
        if now<self.next_column.get(channel,0):raise ValueError('per-PC column interval')
        if any(e['address']==address for e in self.pending.values()):return False
        if sum(e['channel']==channel for e in self.pending.values())>=self.depth:return False
        self.pending[ident]=dict(q=dict(q),channel=channel,address=address,column=now,
            visible_due=self.edge(now+7274),state='COLUMN',visible=None,retired=None)
        self.seen.add(ident);self.next_column[channel]=now+2*FAST
        return True

    def backing_visible(self,q,time):
        e=self.pending[self.identity(q)];now=Fraction(time)
        if e['state']!='COLUMN' or now!=self.edge(now) or now<e['visible_due']:raise ValueError('backing visibility')
        e['visible']=now;e['state']='VISIBLE'

    def capture(self,q,time):
        ident=self.identity(q);e=self.pending[ident];now=Fraction(time);stack=q['die'],q['stack']
        if e['state']!='VISIBLE' or now!=self.edge(now) or now<self.edge(e['visible']+10000):raise ValueError('response visibility')
        queue=self.ACK.setdefault(stack,[])
        if len(queue)>=self.ACK_depth:return False
        queue.append(ident);e['state']='CAPTURED';e['captured']=now;return True

    def ACK_consumer_retire(self,q,time):
        ident=self.identity(q);e=self.pending[ident];stack=q['die'],q['stack'];now=Fraction(time)
        if not self.ACK.get(stack) or self.ACK[stack][0]!=ident:raise ValueError('held ACK identity/head')
        # Explicit bounded source-shaped 1.2->.9 synchronizer crossing and
        # one serial scoreboard store, followed by consumer retirement.
        earliest=(ceil((e['captured']+FAST)/SLOW)+3)*SLOW
        if now<earliest or now%SLOW or now<=self.last_return.get(q['die'],-1):raise ValueError('CDC/store/consumer callback')
        self.ACK[stack].pop(0);e['retired']=now;e['state']='RETIRED';self.last_return[q['die']]=now

    def reverse_credit(self,q,time):
        ident=self.identity(q);e=self.pending[ident];now=Fraction(time)
        if e['state']!='RETIRED' or now!=self.edge(now) or now<(ceil(e['retired']/FAST)+3)*FAST:raise ValueError('reverse credit callback')
        self.locks.pop(e['address'],None);del self.pending[ident]

    def quiescent(self):return not(self.pending or self.locks or any(self.ACK.values()))
