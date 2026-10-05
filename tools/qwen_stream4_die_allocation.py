#!/usr/bin/env python3
"""Allocate the selected 128-PC interface in the preserved Qwen b3r12 die.

No old context is released or resized. This is the missing composed geometry
and clock/source term, not an alternative architecture or a core RTL edit.
"""
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'results/rtl/qwen_rom_fulldie_20261003/b3r3/plan_b3r12/plan.json'
DEF = 'results/rtl/qwen_rom_fulldie_20261003/b3r3/plan_b3r12/floorplan.def'
OUT = 'results/rtl/qwen_stream4_protected_20261005/die_context_r1'


def up(v, quantum):
    return round(math.ceil(v / quantum - 1e-9) * quantum, 6)


def allocation(interface, root=ROOT):
    root = Path(root)
    plan = json.loads((root/PLAN).read_text())
    text = (root/DEF).read_text()
    entries = re.findall(r'^- (\S+) (\S+) \+ FIXED \( (\d+) (\d+) \) (\S+) ;$', text, re.M)
    assert len(entries) == plan['instances'] == 3225
    old = {n: dict(master=m, x=int(x)/1000, y=int(y)/1000, orient=o) for n,m,x,y,o in entries}
    gx, gy = .432, 2.16
    # Retile the same positive area; do not rotate a placed standard-cell macro.
    pcw = up(interface['required_per_PC_home_um'][1], gx)
    pch = up(interface['required_per_PC_home_um'][0], gy)
    gapx, gapy, halo = up(40, gx), up(40, gy), up(4.32, gx)
    bandw = up(2*pcw+gapx+2*halo, gx)
    die = dict(w=plan['die']['w']+2*bandw, h=plan['die']['h'])
    die['mm2'] = die['w']*die['h']/1e6
    die['budget_mm2'] = 858
    die['margin_mm2'] = 858-die['mm2']
    die['fits_reticle'] = die['mm2'] <= 858 and die['w'] <= 26000 and die['h'] <= 33000
    assert die['fits_reticle']
    pcs=[]
    stacks=['WS','WN','ES','EN']  # literal wrapper stack order and old PHY positions
    extent = 16*pch+15*gapy
    for stack, st in enumerate(stacks):
        phy=old['phy_'+st]
        y0=up(phy['y']+12000.12/2-extent/2,gy)
        bx=0 if st[0]=='W' else bandw+plan['die']['w']
        for q in range(32):
            col,row=q//16,q%16
            x=bx+halo+col*(pcw+gapx);y=y0+row*(pch+gapy)
            assert y >= halo and y+pch <= die['h']-halo
            assert pcw*pch/1e6 >= interface['per_PC_core_area_mm2']
            pcs.append(dict(PC_ID=stack*32+q,stack=stack,shoreline=st,
                instance=f'selected.pc[{stack*32+q}].u_cdc',rect_um=[x,y,x+pcw,y+pch],
                core_area_mm2=pcw*pch/1e6,free_clock='clk',memory_clock='hclk',
                source='rtl/hdc/kv/ot_qwen_s4_protected_pc.sv'))
    shared=interface['shared_descriptor_GO']['required_home_um']
    sw,sh=up(shared[0],gx),up(shared[1],gy)
    # The central gap between the two west stack arrays is already inside the
    # new band. It contains no old instance or claimed released context.
    sy=up((old['phy_WS']['y']+old['phy_WN']['y']+12000.12)/2,gy)
    shared_rect=[halo,sy,halo+sw,sy+sh]
    for p in pcs:
        a=p['rect_um'];b=shared_rect
        assert a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]
    original_shifted={n:dict(v,x=v['x']+bandw) for n,v in old.items()}
    # Clock topology is read from actual source, not an insertion-offset guess.
    top='rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv'
    core='rtl/hdc/ot_hdc_core_vector_weight.sv'
    gate='rtl/hdc/ot_hdc_cg.sv'
    t=(root/top).read_text();c=(root/core).read_text()
    assert '.clk(clk), .rst_n(rst_n), .start(kv_layer_start)' in t
    assert 'ot_hdc_cg u_me_cg (.clk(clk), .en(me_en), .gclk(me_clk))' in c
    assert '.clk(me_clk), .rst_n(rst_n), .go(me_go)' in c
    paths=[PLAN,DEF,top,core,gate,'tools/qwen_rom_fulldie.py',
           'tools/orfs_allcorner_spef.py','rtl/hdc/kv/ot_qwen_s4_protected_pc.sv',
           'rtl/hdc/kv/ot_qwen_s4_protected_control.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv']
    # Root-domain service traffic remains full width. No existing 2112-bit
    # near-memory link is silently substituted for these raw STREAM4 ports.
    traffic=dict(CLK_payload_in_bits_per_edge=128*(24+256+9+1),
                 CLK_payload_out_bits_per_edge=128*(281+1+9+1),
                 HCLK_return_in_bits_per_edge=128*(281+1+9+1),
                 HCLK_credit_out_bits_per_edge=128*3,
                 MACs_per_edge=0,compute_intensity=0,codec_routing_priced=True)
    # Clock-qualified link pitch from the existing Qwen corridor gate. Report
    # the real demand before routing; do not turn a long wire into a 90ps IO.
    hub=original_shifted['hub_el']
    # qfd_hub is 412.56 square in this pinned plan.
    service=[hub['x']+412.56/2,hub['y']+412.56/2]
    legs=[]
    for p in pcs:
        r=p['rect_um'];d=abs((r[0]+r[2])/2-service[0])+abs((r[1]+r[3])/2-service[1])
        legs.append(dict(PC_ID=p['PC_ID'],service_distance_um=d,
                         required_registered_spans_at430p56um=math.ceil(d/430.56)))
    stages=sum(x['required_registered_spans_at430p56um'] for x in legs)
    # A lower bound, not a chosen transport. Data/address/tag and validity in
    # both directions must be held; endpoint FIFO protection cannot protect
    # newly added intermediate registers. Handshakes/owners/credits/codec,
    # clock trees and additional routing cost remain above this lower bound.
    payload_bits=(24+256+9+1)+(281+1+9+1)
    dmr_ff=2*stages*payload_bits
    span_max=max(x['required_registered_spans_at430p56um'] for x in legs)
    transport=dict(implemented=False,selected=False,registered_spans_total=stages,
        one_way_max_CLK_edges=span_max,one_way_max_ps=span_max*833.333,
        request_return_min_CLK_edges=2*span_max,
        held_payload_bits_per_bidirectional_span=payload_bits,
        DMR_payload_FF_lower_bound=dmr_ff,
        DMR_payload_core_mm2_lower_bound=dmr_ff*.2916/interface['utilization']/1e6,
        excluded_from_lower_bound=['finite owner and backpressure state','codec/identity checks',
            'buffer/mux cost','clock trees','loaded wire routing'],
        existing_WB_depth=16,existing_landing_depth=64,
        WB_one_per_edge_at_max_round_trip=False,
        WB_credit_limited_II_edges_lower_bound=math.ceil(2*span_max/16),
        full_token_delta_measured=False,rate_credit=False,
        composition='serial write/ACK adds outbound plus return spans; landing adds return spans only where exposed; do not multiply hidden fills by layers',
        slot_fit_of_added_transport=None,
        source_change_required='protected finite transport and exact backpressure proof before global service route')
    return dict(schema='opentallas.qwen.stream4.actual-die-allocation.v1',
        default_OFF=True,NEAR_HBM=0,DSpark=False,parent_core_edited=False,
        baseline_plan=PLAN,baseline_die=plan['die'],die=die,
        preserved_contexts=len(old),released_contexts=[],
        old_context_translation_um=[bandw,0],old_relative_placement_preserved=True,
        old_contexts=original_shifted,shoreline_band_width_um=bandw,
        PC_replicas=128,PC_home_um=[pcw,pch],PCs=pcs,shared_control_rect_um=shared_rect,
        complete_interface_core_area_mm2=interface['complete_interface_core_area_mm2'],
        added_reticle_area_mm2=2*bandw*die['h']/1e6,
        slot_fit=True,traffic=traffic,service_hub_center_um=service,service_legs=legs,
        maximum_required_service_spans=max(x['required_registered_spans_at430p56um'] for x in legs),
        service_transport=transport,
        actual_interface_context=dict(PCs=128,stacks=4,channels_per_stack=16,
            CRED=32,LD=64,WB=16,AD=64,TAGW=9,REF_MODE=1,WR_EN=1,WQ=4,PULLIN=0,AQ_RD=0,
            planned_source='rtl/hdc/kv/ot_qwen_s4_interface_context.sv',
            service_ports='literal full-width free CLK ports; no dummy source or capture substitution',
            PHY_ports='literal HCLK landing/ACK and row/column/completion ports; external real endpoint must supply returns',
            controller_homes={st:original_shifted['ctrl_'+st] for st in stacks},
            controller_slot_qualified=False,
            PHY_protocol_adapter_qualified=False,
            behavioral_DRAM=False,core_instantiated=False,
            qualification_scope='128-PC interface and four actual controllers; global transport and core/gated-clock relation remain separate required gates'),
        source_clocks=dict(service_root=dict(source='selected_top.clk -> u_kv.clk',period_ps=833.333,free_running=True),
            ME=dict(source='core.g_me_cg.u_me_cg.u_icg.GCLK -> core.u_me.clk',
                    parent_root='clk',gate='low-phase latch AND; SE=0; actual me_en includes !rst_n',
                    relationship='active rising edges are a subset of root edges; insertion/skew must come from actual gate and CTS',
                    interface_payload_clock=False),
            HCLK=dict(source='external periodic hclk -> four real stream controllers and interface H ports',period_ps=1024,
                      relationship_to_CLK='independent roots, arbitrary relative phase; no generated-clock alias')),
        setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        crossing_budget_ps=833.333-60,crossing_min_ps=0,
        no_clock_groups_or_blanket_falsepaths=True,no_fabricated_insertion_offset=True,
        loaded_parent_phase_skew_qualified=False,
        physical_admission=False,
        physical_blockers=['corrected c625 32-case actual terminal pending',
                           'full-width service/PHY interconnect must fit registered spans and loaded endpoint budget; no 0.2T IO proxy',
                           'harden one exact full-size PC then compose all128 with actual multi-clock abstracts and four real controllers'],
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})


if __name__=='__main__':
    from qwen_stream4_protected_model import model
    x=allocation(model())
    out=ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    (out/'allocation.json').write_text(json.dumps(x,indent=2)+'\n')
    print(json.dumps({k:x[k] for k in ['die','PC_home_um','shoreline_band_width_um','added_reticle_area_mm2','maximum_required_service_spans']}))
