#!/usr/bin/env python3
"""Replay the native full47/eight-row fixture through production event ledger."""
from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'layer_prog'))
from native_hwin_calendar import event_ledger,check_consumer_book,check_rx_return,MEASURED_SOURCE_SHA256


def fixture():
    events=[]
    for e in range(8):
        events.append(dict(kind=e//4,endpoint=e%4,delay=60+11*e,
            attributes=[dict(ab=(s+e)%2,land=int((s+e)%3==0)if e<4 else(s+e)%2)for s in range(47)]))
    return dict(first_KS_seq_capture=447,period=47*64,slot_offsets=[64*i for i in range(47)],
                return_latency=300,selected_params=dict(HOSTB_ENABLE=0,STATIC_KS6=0,STATIC_KS_SPAN=0,STATIC_KS_GRAPH_TAG=0,FMUT=0),hwin_events=events,hwin_source_sha256=MEASURED_SOURCE_SHA256,
                clock_reset_identity='FIXTURE833ps-HWIN-input-sampling')


def run():
    mu=fixture();tx=rp=0
    for i in range(94):
        descriptor=dict(user=i%47,position=100000+3*i)
        n=447+64*i;ledger=event_ledger(mu,descriptor,n)
        tx+=sum(e['kind']==0 for e in ledger['events']);rp+=sum(e['kind']==1 for e in ledger['events'])
        book=dict(schema='opentallas.s81.native_hwin_consumer_booking.v1',
                  clock_reset_identity=mu['clock_reset_identity'],resource=['FIXTURE','A',0],
                  events=[dict(e,consumer_sampling_edge=e['pin_visible_after_edge']+1,transport_edges=1,
                               consumer_source='explicit fixture sampler, not production LEP')for e in ledger['events']])
        assert not check_consumer_book(ledger,book,('FIXTURE','A',0))
        wrong=deepcopy(book);wrong['events'][0]['pin_visible_after_edge']+=1
        assert check_consumer_book(ledger,wrong,('FIXTURE','A',0))
        wrong=deepcopy(book);wrong['events'][0]['ab']^=1
        assert check_consumer_book(ledger,wrong,('FIXTURE','A',0))
        assert check_consumer_book(ledger,None,('FIXTURE','A',0))
        for d,ok in [(0,False),(1,True),(299,True),(300,False)]:
            assert check_rx_return(ledger,dict(descriptor,input_sampling_edge=n+d),descriptor)==ok
        assert not check_rx_return(ledger,dict(user=descriptor['user'],position=descriptor['position']+1,input_sampling_edge=n+160),descriptor)
    assert(tx,rp)==(376,188)
    print('HWIN_LEDGER_PASS94starts376TX188replay;wrongdate/copy/unbooked/RXcontrolsCAUGHT')


if __name__=='__main__':run()
