#!/usr/bin/env python3
"""Selected finite transport on the actual b3r12 four stack corridors.

This prices the missing transport, including shared credit pools and local
endpoint wires. It does not qualify omitted PHY hardware or floorplan slots.
"""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def ring(width, depth, replicas, pair, utilization):
    p=int(math.log2(depth))+1; n=math.ceil((width+1)/44);cw=n*72
    enc=n*104+p+1
    dec=[cw+p+1,cw+n*40+p+1,cw+n*8+p+1,width+p+2]
    control=22*p+4;reset=8;pipe=2*(enc+sum(dec))
    ff=depth*cw+control+reset+pipe
    mux=cw*(depth-1)*3;checks=3*(pipe//2+control//2)
    buffers=math.ceil(ff/7)
    cell=(ff*.2916+(mux+checks)*.08748+buffers*.10206+n*pair)/1e6
    return dict(payload_bits=width,depth=depth,pointer_bits=p,pieces=n,coded_bits=cw,
        replicas=replicas,total_FF_each=ff,coded_memory_FF_each=depth*cw,
        encoder_decoder_DMR_FF_each=pipe,pointer_control_sync_FF_each=control+reset,
        read_mux_NAND2_each=mux,check_NAND2_each=checks,fanout8_buffers_each=buffers,
        codec_pairs_each=n,cell_mm2_each=cell,core_mm2_all=replicas*cell/utilization,
        read_ports=1,write_ports=1,payload_bytes_per_port_edge=width/8,
        coded_bytes_per_port_edge=cw/8,II_edges=1,
        encoder_edges=2,decoder_edges=4)

def transport(allocation, interface, root=ROOT):
    root=Path(root);util=interface['utilization']
    pair=json.loads((root/'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json').read_text())['SRAM_protection_candidate']['pair_cell_body_um2']
    # NWR64 is the literal service authority. Four grants select one PC per
    # stack each edge, so same-stack WBW4 cannot overrun a one-frame link.
    ingress=ring(296,16,4,pair,util)
    forward=ring(296,128,4,pair,util)
    reverse=ring(288,128,4,pair,util)
    assert ingress['coded_bits']==forward['coded_bits']==reverse['coded_bits']==504
    plan=json.loads((root/allocation['baseline_plan']).read_text())
    stacks=['WS','WN','ES','EN'];legs=[];local=[]
    for st in stacks:
        old=next(p for p in plan['link_stages']['paths'] if p['stack']==st)
        # Use the actual hub->lfifo channel, then each actual new PC home.
        # Retain the old separate fan cost as history; it is not near compute.
        stages=math.ceil(old['trunk_um']/430.56)
        legs.append(dict(stack=st,actual_link_anchor='lfifo_'+st,
            trunk_um=old['trunk_um'],registered_spans=stages,
            original_strip_fan_um=old['fan_um'],original_strip_fan_reused=False))
        a=allocation['old_contexts']['lfifo_'+st]
        center=[a['x']+96.768/2,a['y']+136.08/2]
        for pc in allocation['PCs']:
            if pc['shoreline']!=st:continue
            r=pc['rect_um'];d=abs((r[0]+r[2])/2-center[0])+abs((r[1]+r[3])/2-center[1])
            local.append(dict(PC_ID=pc['PC_ID'],stack=st,distance_um=d,
                registered_spans=math.ceil(d/430.56)))
    trunk_spans=sum(l['registered_spans'] for l in legs)
    local_spans=sum(l['registered_spans'] for l in local)
    # Each payload register is already a sealed 7xSECDED72 word. Newly added
    # pipeline data is NOT plain raw data or unprotected mutable control.
    # Each control node stores valid/poison as DMR and stores both Gray rails
    # plus fault rails in a separately checked state. An upset quarantines,
    # it cannot authorize a credit or replay a prior owner.
    control_ff=4+2*(2*8+2)
    per_node_ff=504+control_ff
    trunk_ff=2*trunk_spans*per_node_ff
    # Conservative local legs retain full sealed records per PC in both
    # directions. Do not omit the PC->stack gather or stack->PC delivery.
    local_ff=2*local_spans*per_node_ff
    global_receiver_and_credit_source_FF=8*(8*8+6)
    # Reuse each already charged PC ring's encoder and decoder as the local
    # wire endpoints. WIRE_STAGES moves sealed code between those cuts; it
    # does not introduce another 256 full encoder/decoder pipelines.
    # ACK remains its own 72-bit sealed ring, not a dropped sideband pulse.
    local_ack_control_ff=4+2*(2*7+2)
    local_ack_ff=local_spans*(72+local_ack_control_ff)
    local_receiver_and_credit_source_FF=128*((8*7+6)+(8*5+6)+(8*7+6))
    extra_endpoint_ff=4*2*(5+6+8+8+3+3+1+1)+128*2*(5+1)+global_receiver_and_credit_source_FF+local_receiver_and_credit_source_FF
    # Exact gates still determine realized mux/decode area. Count raw muxes
    # and PC demux/semantic/owner compares positively before source.
    mux=4*504*31*3+4*32*296*3
    checks=3*((trunk_ff+local_ff-504*2*(trunk_spans+local_spans)+local_spans*local_ack_control_ff)//2+extra_endpoint_ff//2)
    buffers=math.ceil((trunk_ff+local_ff+local_ack_ff+extra_endpoint_ff)/7)
    pipeline_cell=((trunk_ff+local_ff+local_ack_ff+extra_endpoint_ff)*.2916+(mux+checks)*.08748+buffers*.10206)/1e6
    local_codec_cell=0
    functional_core=ingress['core_mm2_all']+forward['core_mm2_all']+reverse['core_mm2_all']+(pipeline_cell+local_codec_cell)/util
    # Explicit capacity reserve, not a borrowed closure verdict: ten percent
    # extra cell/floorplan area for buffers and actual clock trees, plus the
    # actual site snapping will be resolved by the contextual floorplan.
    clock_buffer_reserve=.10*functional_core
    total= functional_core+clock_buffer_reserve
    max_local=max(l['registered_spans'] for l in local)
    max_trunk=max(l['registered_spans'] for l in legs)
    max_oneway=max_local+max_trunk+1+2+4
    # Includes encoder publication, receive visibility+decoder and returned
    # retirement pointer, not merely a straight-line geometric wire count.
    longest_credit_rtt=2*(max_local+max_trunk)+1+2+4+2+2
    return dict(schema='opentallas.qwen.stream4.selected-transport.prebuild.v1',
        selected='four independent sealed 504-bit full-record stack links with protected finite credit pools; existing PC ring codecs reused on local legs',
        default_OFF=True,implemented=False,NEAR_HBM=0,DSpark=False,ROM_ECC=False,
        baseline_plan=allocation['baseline_plan'],actual_service_NWR=64,actual_top_WBW=4,
        source_grants='one rotating PC grant per stack; at most four total; held one-edge grant reserves a queue slot even across warm admission pause',
        grant_rotation_bound_CLK_edges=32,
        source_write_ingress=ingress,forward_frame_pool=forward,reverse_frame_pool=reverse,
        maximum_source_write_entries=64,maximum_source_unspent_grants=4,
        frame_pool_includes_inflight_and_held=True,frame_pool_depth=128,
        control_reserved_entries=4,data_frame_admission_limit=124,
        reservation_basis='one descriptor, one GO, one latest status, one sticky fault per stack; controller consumption ACK and descriptor ordinal retained',
        old_backend_WB=16,old_backend_LD=64,old_backend_AD=64,old_backend_CRED=32,
        backend_WB_is_local_only=True,
        source_write_debt='service NWR64 until actual WR acknowledgment; ingress owner transfers atomically to protected global pool, then protected backend WB16; no retirement from raw handoff',
        landing_debt='existing local landing ring transfers to reserved protected return pool; end retirement only at actual service l_pop; never an advisory credit',
        write_ACK='existing AD64 held output requires opt-in explicit ready; no pulse-only output may be multiplexed or dropped',
        packets=dict(forward='kind2 + PC5 + payload289; descriptor ordinal3/row19/count11 and GO ordinal3 are packet kinds',
            reverse='kind2 + PC5 + payload281; writeACK9, consumed-descriptor ACK3, and busy/ready/fault status are packet kinds',
            seal='existing W2/W6 PC7(stack identity)/word10(frame slot*7+piece)/kind3 plus protected wrap; destination also checks dynamic PC and address bounds',
            kinds_are_protected=True,frame_identity_and_order_are_checked=True),
        trunk_legs=legs,local_legs=local,
        coded_data_FF_per_pipeline_node=504,checked_control_FF_per_pipeline_node=control_ff,
        trunk_pipeline_FF=trunk_ff,local_pipeline_FF=local_ff,extra_endpoint_DMR_FF=extra_endpoint_ff,
        global_receiver_and_credit_source_FF=global_receiver_and_credit_source_FF,
        local_receiver_and_credit_source_FF=local_receiver_and_credit_source_FF,
        local_ACK_pipeline_FF=local_ack_ff,
        local_codec_reuse=dict(source='ot_qwen_s4_protected_pc u_l/u_w/u_a with LOCAL_WIRE_SPANS',
            already_charged_in='mutable_interface rings landing/write/write_done encoder+decoder DMR cuts and codec pairs',
            extra_local_encoder_decoder_FF=0,extra_local_codec_pairs=0,
            actual_source_placement_required=True,
            implemented_default_OFF=True,
            ACK_ready='explicit backpressure at u_a output; retirement on actual mux acceptance',
            local_write_no_stall_credit_bound_CLK_edges=2*max_local+11,
            local_write_depth=16,local_write_stalls_priced=True,
            local_write_peak_records_per_PC_CLK_edge=min(1,16/(2*max_local+11))),
        endpoint_mux_demux_NAND2=mux,extra_checker_NAND2=checks,extra_fanout8_buffers=buffers,
        local_codec_pairs=0,codec_pair_cell_um2=pair,
        pipeline_cell_mm2=pipeline_cell,local_codec_cell_mm2=local_codec_cell,
        utilization=util,functional_transport_core_mm2= functional_core,
        clock_and_buffer_reserve_core_mm2=clock_buffer_reserve,
        total_transport_core_mm2=total,
        endpoint_only_die_mm2=allocation['die']['mm2'],endpoint_only_margin_mm2=allocation['die']['margin_mm2'],
        conservative_area_charge_die_mm2=allocation['die']['mm2']+total,
        scalar_area_budget_fit=allocation['die']['mm2']+total<=858,
        physical_slot_fit=None,complete_system_fit=False,physical_admission=False,
        root_CLK_ps=833.333,HCLK_ps=1024,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        wire_span_um=430.56,max_local_spans=max_local,max_trunk_spans=max_trunk,
        one_way_visibility_max_CLK_edges=max_oneway,one_way_visibility_max_ps=max_oneway*833.333,
        longest_credit_roundtrip_CLK_edges=longest_credit_rtt,
        frame_pool_covers_no_stall_roundtrip=128>=longest_credit_rtt,
        peak_payload_per_stack_CLK_edge_bytes=289/8,peak_coded_per_direction_CLK_edge_bytes=504/8,
        peak_return_records_per_stack_CLK_edge=1,peak_return_records_all_stacks_CLK_edge=4,
        MACs_per_edge=0,compute_intensity_MAC_per_byte=0,
        communication_intensity='one full sealed frame per link edge; up to four globally; bounded by downstream ownership and credits',
        tracks=dict(data_per_stack_duplex=1008,valid_poison_dualrail=8,credit_dualrail=32,fault_dualrail=4,
            clock_shielded=3,cold_POR=1,total_per_stack=1056,actual_horizontal_capacity=1056,
            shared_vertical_two_stack_demand=2112,actual_vertical_capacity=2112,nominal_margin=0,
            loaded_slew_cap_fanout_and_CTS_qualified=False),
        latency_price=dict(P8191_minimum_fill_records=131072,
            minimum_fill_CLK_edges_at_four_return_records=32768,
            minimum_fill_ps_at_four_return_records=32768*833.333,
            historical_changed_source_fill_edges=1466,
            actual_released_layers=36,component_chain_MLP_window_CLK_edges=3000,
            component_chain_minimum_late_prefetch_exposure_CLK_edges=32768-3000,
            full_token_issue_timestamps_known=False,
            token_composition='first exposed fill >=32768 edges plus visibility; later fills >=max(0,32768-actual measured independent MLP window) each; add ordered write/ACK fences and unchanged head/core path once; component MLP3000 is not the actual36-layer calendar',
            price='return bandwidth and PC grant stalls are real; compose into each exposed fill and write visibility fence, retain posted prefetch overlap only when measured',
            whole_token_measured=False,rate_credit=False,adopted=False),
        warm_reset='closes fresh grants; every issued grant, frame, pointer, decoder and backend owner drains or stays held; POR alone erases',
        admission_blockers=['existing bbcb and corrected c625 actual32 terminals',
            'implement and exact-test actual shared frame links and protected ready/credit/control endpoints',
            'allocate nonoverlapping central ingress, local legs, endpoint/control/PHY and clock homes in b3r12; scalar area sum is not slot fit',
            'loaded SS60/FF25 contextual route with actual independent HCLK and source free/gated clock relation'],
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in [
            allocation['baseline_plan'],'tools/qwen_rom_fulldie.py',
            'rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv','rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
            'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv','rtl/hdc/kv/ot_qwen_s4_interface_context.sv',
            'rtl/hdc/kv/ot_qwen_s4_packet_link.sv',
            'rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv']})
