#!/usr/bin/env python3
"""Compile independent static calendar roots; no controller observations accepted.

This is a bounded hardware mechanism, not a production schedule generator. A
component contract must supply exact cycles at this leaf's output pins. Missing
all36 absolute calendars and physical path receipts cannot be inferred here.
"""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRODUCER='rtl/qwen_sys/static_kv_20261014/qkd_kv_calendar_replay.sv'
CONSUMERS={
 'HBM':['rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static.sv',
        'rtl/qwen_sys/static_kv_20261014/qkd_kv_hbm_elastic_front.sv'],
 'CORE':['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv']}

def compile_image(contract):
    if contract.get('stage_count',1)!=1:
        raise ValueError('leaf has no actual36-layer rowcount/image coverage; stage_count must be1')
    if contract.get('scope')!='COMPONENT_ONLY':
        raise ValueError('production missing all36 source calendar/physical clock-path receipts and storage/home/cost')
    if contract.get('origin')!='INDEPENDENT_STATIC_CONTRACT':
        raise ValueError('runtime controller/arrival/ready traces cannot define a calendar')
    domain=contract.get('domain')
    if domain not in CONSUMERS:raise ValueError('HBM or CORE domain required')
    if contract.get('cycle_origin')!='INTERNAL_START_OUTPUT_INTERVAL_0':
        raise ValueError('explicit output interval origin required')
    sources=contract.get('source_sha256',{})
    for p in [PRODUCER,*CONSUMERS[domain]]:
        if sources.get(p)!=hashlib.sha256((ROOT/p).read_bytes()).hexdigest():
            raise ValueError('missing or changed actual producer/consumer source '+p)
    width=64 if domain=='HBM' else 33
    events=contract.get('events',[]);stop=contract.get('stop_cycle')
    if not isinstance(events,list) or not 1<=len(events)<=64:raise ValueError('split into 1..64-event leaves')
    if type(stop)!=int or not 0<stop<2**32:raise ValueError('stop must be positive cycle32')
    last=-1;image=[]
    for address,event in enumerate(events):
        t=event.get('cycle');data=event.get('payload')
        if type(t)!=int or not last<t<stop:raise ValueError('strict increasing event cycles before stop required')
        if type(data)!=int or not 0<data<2**width:raise ValueError('nonzero exact payload width required')
        if domain=='HBM' and data>>63:raise ValueError('HBM bit63 is reserved zero')
        image.append(dict(address=address,cycle=t,payload=data));last=t
    return dict(schema='opentallas.qwen-kv-calendar-replay-image.v1',
      scope='COMPONENT_ONLY',domain=domain,width=width,depth=64,
      events=image,seal_stop_cycle=stop,input_capture_edges=1,
      cycle_origin=contract['cycle_origin'],source_sha256=sources,
      storage_bits=64*(32+width),production_installable=False,
      missing=['persistent boot/ingest/controller initial state and absolute all36 PC calendars',
               'independent front release/capacity and full landing consumer lifetimes',
               'actual HOST boot loader and all-leaf control storage composition',
               'physical home/phi-R/reset/command/return path ages and TT/FF/DRC',
               'measured token cost and actual die binding'])
