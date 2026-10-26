#!/usr/bin/env python3
"""Compile actual sequential SU quarter-sum -> native RED_CARRY ring slots.

Preserves (((q0+q1)+q2)+q3), including all three FP32 roundings. The
current scalar quarter result occupies each of the eight physical carry lanes;
only the declared returned RF lane is a programme consumer. Repetition is
explicit and priced as eight physical lane operations, never eight workloads.
"""
from __future__ import annotations
import json
from pathlib import Path
from su_red_carry_calendar import lower, CalendarError
ROOT=Path(__file__).resolve().parents[2]
LAYOUT=ROOT/'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json'
ORDER=[0,1,3,2]

def compile_sum(roots, export_start, rf_return_destination=31):
    if len(roots)!=4 or {r['quarter'] for r in roots}!={0,1,2,3}:
        raise CalendarError('four actual native quarter producers required')
    if export_start<max(r['ready_serial'] for r in roots):
        raise CalendarError('native quarter sum unavailable')
    # Last scalar capture E+12, cxport processing E+13; rc update ceil((4m+3)/3).
    base=(4*(export_start+7+13)+5)//3
    # B odd ensures every native ring result lands at stream update 0/2,
    # hence the cxport captures returns on legal stream phases 1/3.
    late=base&1
    b=base+late+1
    assert b%2==1
    rows={};reserved={};fields=json.loads(LAYOUT.read_text())['ring_fields']
    def put(q,c,name,value):
        f=fields[name]; mask=((1<<f['width'])-1)<<f['lsb'];key=q,c
        old=rows.get(key,0)
        if old&mask:raise CalendarError(f'occupied ring field {q} {c} {name}')
        if not 0<=value<1<<f['width']:raise CalendarError('ring field overflow')
        rows[key]=old|(value<<f['lsb'])
    def reserve(q,c,name):
        key=q,c,name
        if key in reserved:raise CalendarError(f'occupied native resource {key}')
        reserved[key]=True
    def send(src,dst,c,result=False):
        d=0 if result or (ORDER.index(dst)-ORDER.index(src))%4!=3 else 1
        put(src,c,'tx_inject',1<<d);put(src,c,'tx_tag',3)
        put(src,c,'tx_dst',dst);put(src,c,'tx_result',int(result));put(src,c,'tx_acc',int(src!=0))
        put(src,c-2,'state_read_tx',1);put(src,c-2,'state_tx_tag',3);put(src,c-2,'state_tx_acc',int(src!=0))
        q=src; hops=3 if result else ((ORDER.index(dst)-ORDER.index(src))*(1 if d==0 else -1))%4
        for h in range(1,hops+1):
            q=ORDER[(ORDER.index(q)+(1 if d==0 else -1))%4]; t=c+2*h
            reserve(q,t,'ring.rx'+str(d));put(q,t,'rx_slot',1<<d)
            put(q,t,'rx_kind',(2 if result else 1)<<(2*d));put(q,t,'rx_src',src<<(2*d));put(q,t,'rx_tag',3<<(3*d))
            if h<hops:put(q,t,'tx_forward',1<<d)
        if result:
            put(src,c,'rr_local',1);put(src,c,'rr_local_tag',3)
            put(src,c-2,'state_read_rr',1);put(src,c-2,'state_rr_tag',3)
    def add(q,c,src):
        put(q,c-2,'state_read_add',1);put(q,c-2,'state_add_tag',3);put(q,c-2,'state_add_src',src)
        put(q,c,'add_v',1);put(q,c,'add_tag',3);put(q,c,'add_src',src)
    for q in range(4):put(q,b,'lp_we',1);put(q,b,'lp_tag',3)
    send(0,1,b+3);add(1,b+8,0)
    send(1,2,b+19);add(2,b+26,1)
    send(2,3,b+37);add(3,b+42,2)
    send(3,3,b+53,True)
    # Ring root3 publishes locally, then CW visits2,0,1 every two stream edges.
    rr={q:b+53+2*i for i,q in enumerate([3,2,0,1])}
    plan=dict(rf_relay=36,exports=[],returns=[dict(quarter=q,tag=3,coll_update_stream=p) for q,p in rr.items()])
    for root in sorted(roots,key=lambda r:r['quarter']):
        for w in range(8):
            x=dict(quarter=root['quarter'],command_edge=export_start+w,source_addr=root['source_addr'],
                   source_ready_serial=root['ready_serial'],carry_word=w)
            if w==7:x.update(emit=True,collective_tag=3,return_destination=rf_return_destination,lp_sample_stream=b)
            plan['exports'].append(x)
    native=lower(plan)
    return dict(schema='opentallas.hbm.su.sequential_ring_programme.v1',
                producer_graph=roots, export_plan=plan, native_lowering=native,
                ring_rows=[dict(quarter=q,stream_edge=c,word=f'{v:015x}') for (q,c),v in sorted(rows.items())],
                lp_sample_stream=b, rr_update_stream=rr,
                rf_commit_serial={e['quarter']:e['rf_commit_serial'] for e in native['events'] if e['kind']=='return'},
                arithmetic_order='(((q0+q1)+q2)+q3)', repeated_carry_lanes=8,
                logical_results=1, ring_relay_stages=0, physical_relay_calendar_qualified=False,
                whole_layer_native_qualified=False, production_rate_qualified=False)
