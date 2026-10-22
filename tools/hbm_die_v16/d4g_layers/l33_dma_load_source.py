#!/usr/bin/env python3
"""Attach the real static LOAD conversion and routing source to a die contract.

This is a source candidate, never a physical-view alias. Existing vmfc payload
bits 0..88 and raw delivery remain present. The compiler must consume the new
command fields and the explicit latency ledger before a release is claimed.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QS = ('SW', 'SE', 'NW', 'NE')
REGION = 'd4g_l33_dma_load'
LOAD_SOURCE = 'rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_load_static.sv'
ROUTE_SOURCE = 'rtl/hbm_accel/loader/service_native/split/ot_hbm_dma_load_route_static.sv'
OR_SOURCE = 'rtl/hbm_accel/die_glue/ot_hbm_kqs_fault_or4.sv'


def port(direction, bits):
    return dict(direction=direction, bits=bits)


def apply(c):
    for source in (LOAD_SOURCE, ROUTE_SOURCE, OR_SOURCE):
        assert (ROOT/source).is_file(), source
    assert not any(n.startswith('dmal_') for n in c['instances']), 'already applied'
    instances = c['instances']
    added = []

    def edge(source, sink, bits):
        c['edges'].append(dict(name=f'l33_{len(c["edges"]):06d}', bits=bits,
            source=source, sink=sink, clock='stream', ready_or_credit=False,
            allowed_exception=None, basis='Static LOAD source and fixed-slot routing; calendar projection owed', region=REGION))

    def inst(n, master, ports, clock_from=None, params=None, source=ROUTE_SOURCE):
        instances[n] = dict(master=master, source=source, rtl_deps=[],
            params=params or {}, slot=n, region=REGION, owner='CODEX-HBM-CHAIN-2000',
            force_synth=True, note='Real source candidate; placement and measured die calendar OPEN', ports=ports)
        added.append(n)
        if clock_from:
            for r in list(c['clock_resets']):
                if r['instance']==clock_from and r['port'] in ('clk','rst_n'):
                    c['clock_resets'].append(dict(copy.deepcopy(r), instance=n))

    for qid, q in enumerate(QS):
        cal = instances[f'vmfc_{q}']
        assert cal['master']=='hfd_hgi_vm_calendar_f20_role' and cal['params']['W']==89
        assert cal['ports']['payload']['bits']==89
        cal['params']['W']=159
        cal['ports']['payload']['bits']=159
        cal['force_synth']=True
        cal.pop('physical_view',None)
        cal.pop('closed_record',None)
        cal['note'] += ' | l33: low89 unchanged, LOAD valid8 at89 and command62 at97; roleW159 source only'
        obs=instances[f'obs_{q}']
        base_obs=obs['params']['N']
        assert obs['ports']['obs']['bits']==base_obs
        obs['params']['N']=base_obs+8
        obs['ports']['obs']['bits']=base_obs+8
        obs['force_synth']=True
        obs.pop('physical_view',None)
        obs.pop('closed_record',None)
        sj=f'dmal_src_{q}'
        dj=f'dmal_dst_{q}'
        inst(sj,'ot_hbm_dma_load_source_join',dict(clk=port('input',1),rst_n=port('input',1),
            lane_dq=port('input',2248),lane_destination=port('input',40),
            packet=port('output',281),destination=port('output',5),fault=port('output',1)),f'vmdel_{q}0')
        inst(dj,'ot_hbm_dma_load_destination_join',dict(clk=port('input',1),rst_n=port('input',1),
            source_packet=port('input',1124),source_destination=port('input',20),
            packet=port('output',281),bank=port('output',3),fault=port('output',1)),f'vmdel_{q}0',dict(QID=qid))
        for b in range(8):
            lane=f'vmdel_{q}{b}'
            i=instances[lane]
            assert i['master']=='ot_hbm_svc_vmdel_lane_n' and i['params']['NPC']==2
            i.update(master='ot_hbm_svc_vmdel_lane_load_static', source=LOAD_SOURCE, force_synth=True)
            # Preserve the real bank identity declaration on the new source
            # master. Leaving its old master name silently drops that identity
            # from the strict binder's admitted strap inventory.
            for strap in c['straps']:
                if strap.get('inst')==lane:
                    if strap['port']=='bank_id':
                        assert strap['value']==b, (lane, strap)
                    strap['master']=i['master']
            i.pop('physical_view',None)
            i.pop('closed_record',None)
            i['ports'].update(load_v_i=port('input',1),load_cmd_i=port('input',62),
                load_dq=port('output',281),load_dest_bank=port('output',3),
                load_dest_q=port('output',2),load_out_v=port('output',1))
            i['note']+=' | l33: raw delivery preserved, real SRAM LOAD conversion; source-to-packet4 edges'
            edge([f'vmfc_{q}','payload',89+b,90+b],[lane,'load_v_i',0,1],1)
            edge([f'vmfc_{q}','payload',97,159],[lane,'load_cmd_i',0,62],62)
            edge([lane,'load_out_v',0,1],[f'obs_{q}','obs',base_obs+b,base_obs+b+1],1)
            edge([lane,'load_dq',0,281],[sj,'lane_dq',281*b,281*(b+1)],281)
            edge([lane,'load_dest_bank',0,3],[sj,'lane_destination',5*b,5*b+3],3)
            edge([lane,'load_dest_q',0,2],[sj,'lane_destination',5*b+3,5*b+5],2)
            bj=f'dmal_bank_{q}{b}'
            fj=f'dmal_fault_{q}{b}'
            inst(bj,'ot_hbm_dma_load_bank_join',dict(clk=port('input',1),rst_n=port('input',1),
                raw_dq=port('input',281),load_dq=port('input',281),load_bank=port('input',3),
                dq=port('output',281),fault=port('output',1)),lane,dict(BANK=b))
            inst(fj,'ot_hbm_kqs_fault_or4',dict(leaf_faults=port('input',4),fault=port('output',1)),source=OR_SOURCE)
            raw_edges=[e for e in c['edges'] if e['source'][:2]==[lane,'dq'] and e['sink'][:2]==[f'vmb_{q}{b}','dq']]
            assert len(raw_edges)==1,(lane,'raw delivery edge absent or ambiguous')
            raw_edges[0]['source']=[bj,'dq',0,281]
            fault_edges=[e for e in c['edges'] if e['source'][:2]==[lane,'fault']]
            assert fault_edges,lane
            for e in fault_edges:e['source']=[fj,'fault',0,1]
            edge([lane,'dq',0,281],[bj,'raw_dq',0,281],281)
            edge([dj,'packet',0,281],[bj,'load_dq',0,281],281)
            edge([dj,'bank',0,3],[bj,'load_bank',0,3],3)
            for bit, source in enumerate(((lane,'fault'),(sj,'fault'),(dj,'fault'),(bj,'fault'))):
                edge([*source,0,1],[fj,'leaf_faults',bit,bit+1],1)
    for q in QS:
        for sid,sq in enumerate(QS):
            edge([f'dmal_src_{sq}','packet',0,281],[f'dmal_dst_{q}','source_packet',281*sid,281*(sid+1)],281)
            edge([f'dmal_src_{sq}','destination',0,5],[f'dmal_dst_{q}','source_destination',5*sid,5*(sid+1)],5)
    c['masters']=dict(sorted(collections.Counter(i['master'] for i in instances.values()).items()))
    c['summary']['clock_reset_ports']=len(c['clock_resets'])
    return dict(status='REAL_SOURCE_ATTACHED_PLACEMENT_AND_CALENDAR_OPEN',added_instances=added,
        changed_load_lanes=32,vmfc_role_width=159,payload=dict(preserved=[0,89],load_valid=[89,97],load_command=[97,159]),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (LOAD_SOURCE,ROUTE_SOURCE,OR_SOURCE)},
        fixed_edges=dict(command_pin_to_conversion=4,source_join=2,destination_join=2,bank_join=1,
                         command_pin_to_vm_request_before_die_relays=9,added_raw_delivery=1),
        physical_view_activation=False,obligations=['real source and destination regional landing and relay ages',
            'new router grants within26x33mm reticle, actual synthesis and placement',
            'compiler LOAD windows, release-only ownership, masks and destination mapping',
            'strict source bind, current token replay, actual die GRT STA CLK IR'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('input','output','report'):ap.add_argument(name,type=Path)
    a=ap.parse_args()
    c=json.loads(a.input.read_text())
    r=apply(c)
    for p,v in ((a.output,c),(a.report,r)):
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(v,indent=1)+'\n')
    print('DMA_LOAD_SOURCE_ATTACHED',r['changed_load_lanes'],'lanes, route instances',len(r['added_instances']),'; physical/calendar OPEN')
