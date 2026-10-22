#!/usr/bin/env python3
"""Unit tests for extracting observations; events here are explicitly synthetic."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import kv_producer_events as E


def run(root):
    root=Path(root)
    header=dict(schema=E.SCHEMA,record='run_identity',run_id='TEST_ONLY_EVENT_EXTRACTION',
        native_clock_domain='TEST_ONLY_CLOCK',native_command_epoch_edge=0,
        source_sha256={E.MEM:E.MEM_SHA},physical_epoch_mapping=None)
    def event(kind,edge,**kw):return dict(record='event',kind=kind,edge=edge,**kw)
    owner='L2.attn.cmp.pool';job=owner+'::CP'
    events=[event('SRAM_COMMIT',1,row=0,mask=15,word128='0123456789abcdef0011223344556677',
                  producer='TEST_ONLY_NATIVE_WRITER',producer_kind='TEST_ONLY',role='input'),
            event('DISPATCH_CAPTURE',3,owner=owner,job=job,command_kind='CP',jid=0),
            event('READ_REQUEST',4,row=0,owner=owner,job=job,read_id='r0'),
            event('READ_READY',8,row=0,read_id='r0',word128='0123456789abcdef0011223344556677'),
            event('DONE',393,owner=owner,job=job,command_kind='CP'),event('RUN_END',400)]
    result=E.extract(header,events,root/'source');record=result['producers'][owner+'::input_rows']
    assert record['rows'][0]['ready_edge']==2 and record['rows'][0]['last_read_edge']==4
    assert record['rows'][0]['release_edge']==5 and result['physical_epoch_mapping'] is None
    assert not result['production_enabled'] and not result['calendar_qualified']
    caught=[]
    def expect(name,h,ev):
        try:E.extract(h,ev,root/'source')
        except ValueError as exc:caught.append(dict(case=name,error=str(exc)))
        else:raise AssertionError('missed '+name)
    ev=deepcopy(events);ev[3]['word128']='0';expect('wrong_actual_read_value',header,ev)
    ev=deepcopy(events);ev[1]['edge']=0;ev[2]['edge']=1;ev.sort(key=lambda e:e['edge'])
    expect('read_before_write_same_edge',header,ev)
    ev=deepcopy(events);ev[2]['row']=1;expect('read_without_actual_writer',header,ev)
    ev=deepcopy(events);ev[2]['native_clock_domain']='OTHER';expect('clock_domain_cast',header,ev)
    expect('missing_finite_replay_end',header,events[:-1])
    h=deepcopy(header);h['source_sha256'][E.MEM]='0'*64;expect('different_native_macro',h,events)
    ev=deepcopy(events);ev[0]['mask']=1;expect('read_without_all_native_lanes',header,ev)
    ev=deepcopy(events);ev[4:4]=[event('SRAM_COMMIT',9,row=0,mask=15,word128='0',producer='OTHER_WRITER',role='input'),
        event('READ_REQUEST',10,row=0,owner=owner,job=job,read_id='r1'),
        event('READ_READY',14,row=0,read_id='r1',word128='0')]
    expect('writer_overwrites_consumer_lease',header,ev)
    incomplete=E.extract(header,[e for e in events if e['kind']!='DONE'],root/'source')
    ir=incomplete['producers'][owner+'::input_rows']
    assert ir['status']=='PARTIAL' and ir['rows'][0]['release_edge'] is None
    go='L2.attn.kv_norm.sumsq';gj=go+'::GK';cj=go+'::KV'
    gev=deepcopy(events[:4])
    gev[1].update(owner=go,job=gj,command_kind='GK',gain_set=0,gain_epoch='E0')
    gev[2].update(owner=go,job=gj)
    gev.extend([event('GAIN_LOAD',9,owner=go,job=gj,gain_set=0,gain_epoch='E0'),
                event('GK_DONE',10,owner=go,job=gj,command_kind='GK',gain_set=0,gain_epoch='E0'),
                event('DISPATCH_CAPTURE',12,owner=go,job=cj,command_kind='KV',gain_set=0,gain_epoch='E0'),
                event('GAIN_CONSUME',18,owner=go,job=cj,gain_set=0,gain_epoch='E0'),
                event('DONE',20,owner=go,job=cj,command_kind='KV'),event('RUN_END',30)])
    gain=E.extract(header,gev,root/'source')['producers'][go+'::gain_upload_rows']
    assert gain['status']=='PASS' and gain['gain_bank_loaded_edge']==10 and gain['gain_bank_release_edge']==21
    ev=deepcopy(gev);ev[5]['gain_epoch']='OTHER';expect('GK_DONE_epoch_mismatch',header,ev)
    ev=deepcopy(gev);ev[6]['edge']=8;ev.sort(key=lambda e:e['edge'])
    expect('arithmetic_precedes_gain_loaded',header,ev)
    ev=deepcopy(gev);ev[7]['gain_set']=3;expect('consumer_gain_bank_mismatch',header,ev)
    ev=deepcopy(gev);ev.insert(7,event('GAIN_OVERWRITE',16,owner='OTHER',job='OTHER',gain_set=0,gain_epoch='NEXT'))
    expect('gain_overwrite_before_consumer_done',header,ev)
    inc=E.extract(header,[e for e in gev if e['kind']!='DONE'],root/'source')
    assert inc['producers'][go+'::gain_upload_rows']['status']=='PARTIAL'
    out=dict(status='PASS',scope='SYNTHETIC_DIAGNOSTIC_EVENT_EXTRACTION_ONLY',
        extractor_sha256=E.sha(E.__file__),causal_refusals=caught,
        incomplete_cases=['missing_consumer_DONE','missing_gain_consumer_DONE'],
        calendar_qualified=False,production_enabled=False)
    (root/'event_extractor_test.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PASS relative observation extraction;',len(caught),'causal refusals; no hardware qualification')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();run(a.root)
