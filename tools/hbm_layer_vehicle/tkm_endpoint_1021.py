"""Exact new TP192 F32S1 endpoint contract, before real global COLL lowering.

Times are sampled at the actual tkm_SW input interface, not issuer/CP rows.
A caller must bind producer/qslots delays and the new 160 clock references.
No expected numerical output or synthetic delivery payload is accepted.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LAYOUT=ROOT/'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json'


def endpoint_plan(*, n, k, nout, g, gbase, pf, obase, rbase, has_r, start_edge):
    values=locals().copy()
    for name,value in values.items():
        if type(value) is not int:
            raise ValueError(f'{name}: exact integer required')
    if not (1<=g<=192 and 0<=gbase and gbase+g<=256 and
            1<=n<4096 and pf==(n+7)//8 and 1<=nout<=k<=2048 and
            has_r in (0,1) and start_edge>=0):
        raise ValueError('invalid fixed TP192 configuration')
    for name,value in [('obase',obase),('rbase',rbase)]:
        if not 0<=value<1<<40 or value%16:
            raise ValueError(f'{name}: aligned40bit VM word address required')
    cells=(nout+3)//4; flits=g*pf
    ingress=8+((flits+3)//4)*8; settle=136
    first=ingress+settle;clear2=first+cells+5;read2=clear2+5
    second=read2+cells+6+settle;finish=second+cells+8
    fields=json.loads(LAYOUT.read_text())['fields']
    def pack(d):
        word=0
        for name,value in d.items():
            field=fields[name]
            if not 0<=value<1<<field['width']:raise ValueError(name)
            word|=value<<field['lsb']
        return word
    config=dict(tkm_start=1,tkm_cfg_n=n,tkm_cfg_k=k,tkm_cfg_nout=nout,
                tkm_cfg_g=g,tkm_cfg_gbase=gbase,tkm_cfg_pf=pf,
                tkm_cfg_obase=obase,tkm_cfg_rbase=rbase,tkm_cfg_has_r=has_r)
    commands=[dict(sample_edge=start_edge,fields=config,uop_payload_hex=f'{pack(config):0384x}')]
    for group in range((flits+3)//4):
        mask=sum(1<<lane for lane in range(4) if 4*group+lane<flits)
        d=dict(tkm_del_slot=mask)
        commands.append(dict(sample_edge=start_edge+9+8*group,fields=d,
                             uop_payload_hex=f'{pack(d):0384x}',
                             required_actual_delivery_lanes=[lane for lane in range(4) if mask>>lane&1],
                             producer_flit_indices=[4*group+lane for lane in range(4) if mask>>lane&1]))
    return dict(schema='opentallas.tkm_f32s1_endpoint_plan.v1',
                source_master='ot_hgi_coll_tkm_m_tp192_f32s1',
                time_origin='posedge actually sampling tkm_start; not CP or issuer row age',
                commands=commands,zero_del_slot_and_valid_at_other_busy_edges=True,
                phases_tick=dict(ingress_end=ingress,first=first,clear2=clear2,read2=read2,second=second,finish=finish),
                phases_sample_edge={key:start_edge+1+value for key,value in dict(first=first,clear2=clear2,read2=read2,second=second,finish=finish).items()},
                capture_pipeline_tap=2,legacy_delta=dict(first=32,clear2=32,read2=32,second=64,finish=64,capture_tap=1),
                output_write_requirement=dict(port='real tkm_SW.w_v/w_addr/w_mask/w_data',
                    ids_base=obase,values_base=rbase,values_enabled=bool(has_r),
                    owner_window_start=start_edge,owner_window_end=start_edge+finish+1,
                    writer_commit_delay='required actual parent writer pipeline; not guessed'),
                programme_qualified=False,physical_view_qualified=False,
                remaining_binding=['actual peer/own producer and delivery/qslots programme',
                                   'map endpoint sample edges to actual issuer rows using selected source ages',
                                   'real writer grants/commit delay and VM footprints',
                                   '160 distinct tile entry clockrefs and actual parent delivery'])
