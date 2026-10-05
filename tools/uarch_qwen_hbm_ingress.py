#!/usr/bin/env python3
"""Price finite command ingress, coalescing, returns and write commits."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import uarch_model as U

ROOT=Path(__file__).resolve().parents[1]


def compose():
    base=json.loads((ROOT/'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json').read_text())
    l2=json.loads((ROOT/'results/uarch/qwen_hbm_connected_20261001/L2_injector_before_RTL.json').read_text())
    clock=1.2e9;stacks=4;clients=36;NPC=32;QD=512;RQD=512
    # The old model is read-only provenance. Its LENMAX is2**(LENW-1),
    # independently of RW. Each stack has just one command input per cycle.
    choices=[]
    for name,sectors in [('uncoalesced128B',4),('LENW5_fourline',16),('LENW6_eightline',32)]:
        choices.append(dict(name=name,sectors_per_read_command=sectors,
            B_per_read_command=32*sectors,max_read_Bpc_die=stacks*32*sectors,
            max_read_bytes_s=stacks*32*sectors*clock))
    # Keep the500ns loaded-latency assumption as a controller/PHY floor,
    # split between request/response. DRAMCL/burst and actualbank/refresh
    # waits are additional, not a faster substitution using old10ns defaults.
    minimum_backend_ns=250+250+12.5+1.024
    boundary_cycles=72+2+7+3+3 # wire roundtrip, controller, collect8, map, gather
    roundtrip=math.ceil(minimum_backend_ns*1e-9*clock)+boundary_cycles
    worst=roundtrip+55
    credit_Bpc=32*512*128/worst
    served=min(3000,4096,credit_Bpc)
    design=base['base_design']
    ops=U.qwen_hbm_ops(design['element'],64,89)
    traffic=sum(b for b,t in ops)
    # Conservative controller/gather organization: store all partial128B
    # lines until delivered. No fictional free reuse of the existingSMring.
    gather_macros_per_client=2 # 512lines*128B =64KB
    metadata_bits_per_client=64*(8*10+32+6+32+4+1)+2*(32+8*10+4)+512*5+10
    controller_queue_metadata_bits=stacks*NPC*(QD*(34+16+5+1)+RQD*(16+5+1))
    queue_data_macros_per_stack=(NPC*QD*32+NPC*RQD*32)//(32*1024)
    metadata_bits=clients*metadata_bits_per_client+controller_queue_metadata_bits
    metadata_mm2=metadata_bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6
    data_macros=clients*gather_macros_per_client+stacks*queue_data_macros_per_stack
    data_mm2=data_macros*U.GPU_UNIT_UM2['sram32k']*U.GPU_MACRO_PACK/1e6
    # Explicit first estimate for arbitration/tag-table/sector-gather muxes.
    mux_bits=stacks*NPC*(256+16+5)*8+clients*4*256
    logic_extra_mm2=(mux_bits*.2+stacks*2048)/U.GPU_LOGIC_UTIL/1e6
    cdc_bits=32*2*16*320 # one FIFO in each direction per SM
    cdc_mm2=cdc_bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6
    return dict(schema='opentallas.gpu-hbm-ingress-contract.v1',status='model_before_RTL',
        full_token=False,adoption=False,physical_build_ready=False,
        organization='OrdinaryGPU contiguous-read coalescer and finite per-PC DRAM controller; generic128B transport for Qwen and DeepSeek packers',
        ingress_alternatives=choices,
        selected=dict(stacks=4,commands_per_stack_per_fast_cycle=1,LENW=6,BEATW=5,
            LENMAX_sectors=32,line_bytes=128,lines_per_read_command=8,
            read_ingress_Bpc_die=4096,read_ingress_TB_s=4.9152,
            write_sectors_per_command=1,write_command_bytes=32,
            write_command_ingress_Bpc_die=128,
            mixed_command_bound='read_bytes/1024 + write_bytes/32 <=4commands/fastcycle; writes and reads also share actualDRAM bytebudget',
            RW=16,RW_scope='Bank-reorder window only, not maximumread length'),
        coalescer=dict(clients=36,credits_in_128B_lines_per_client=512,
            batch_slots_per_client=64,retained_original_line_tags_per_batch=8,
            global_command_tag='{client6,batch_slot6,generation4}',
            original_SM_tag_bits=10,backend_sector_address_bits=34,
            stripe='32Bsectors;128Bline comprises4sectors; coalescedread comprises8adjacentlines/32sectors',
            collect='Only contiguoussameclient reads coalesce; retain each originaltag. Collectup to8, flushatdescriptorend/noncontiguousaddress or8idlecycles. Partialcommands consume a realcommand slot',
            matrix_line_counts=[dict(name=m['name'],per_SM_lines=m['rows_max_sm']*m['K']//128,
                full_eightline_batches=(m['rows_max_sm']*m['K']//128)%8==0) for m in base['matrix_contracts']],
            sector_gather='Retain32bit percommand completionbitmap and original8line tags; eachline4sectors assembledbeforea128Bresponse; duplicates/stalegeneration/unknownclient fault',
            write='One128Bclientwrite becomes4actual32Bwritecommands. Holdclientcredit untilall4realmemorycommitacks; issueacceptance is not commit',
            no_read_length_padding=True,
            arbitration="Round-robin among eligible clients with bounded-oldest MAXSKIP16; no free bypass of blocked credits. Per-stack byte token bucket 750B/cycle charges every read/write sector; sector bursts consume stored tokens, FIFO capacity bounds burst accumulation"),
        backend=dict(NPC=NPC,QD=QD,RQD=RQD,RW=16,MAXSKIP=16,PC_RDY=1,PC_ROOM=32,
            core_clock_target_hz=clock,CLK_PS=833,BURST_PS=1024,
            REQ_PS=250000,RSP_PS=250000,CL_PS=12500,CWL_PS=6250,
            REFI_PS=3900000,RFC_PS=350000,
            TCCDL_PS=2560,RCDRD_PS=19375,RCDWR_PS=9375,RP_PS=16250,RAS_PS=28125,
            WR_PS=20625,RTP_PS=5625,RRDS_PS=2500,RRDL_PS=3125,FAW_PS=15000,
            WTRS_PS=4375,WTRL_PS=6250,RTW_PS=9948,
            banking='SamecommodityHBM bank/openpage/turnaround/refresh timing reference, parameterizedports; originalROM model untouched',
            capacity_B_per_stack=U.HBM_STACK_B*.9,
            address='Exactfulladdress backing with finitecapacity admission; no moduloMEM_WORDS alias. Sparse simulator backing mayallocateonlytouchedpages, neverchangeaddressidentity',
            required_new_output='Ready/valid per-PC actualwritecommitack with globaltag+sectorbeat, emittedaftermemorywrite under timing/backpressure',
            original_backend_limitations='Originalot_hdc_hbm_model has no writeack and aliasesbacking via moduloMEM_WORDS. It cannot be relabeledproductionGPUservice'),
        queue_capacity=dict(request_bytes_per_stack=NPC*QD*32,return_bytes_per_stack=NPC*RQD*32,
            loaded_request_floor_inflight_bytes_per_stack=900e9*250e-9,
            loaded_response_floor_inflight_bytes_per_stack=900e9*250e-9,
            old_QD64_request_bytes=32*64*32,old_RQD32_return_bytes=32*32*32,
            note='Old64/32PC queues cannotabsorb250ns request/response floors at900GB/s.512/512 isfinite,area-priced and stillbackpressuresactualbank/refresh stalls'),
        area=dict(metadata_bits=metadata_bits,metadata_footprint_mm2=metadata_mm2,
            additional_data_macros_32KB=data_macros,additional_data_SRAM_footprint_mm2=data_mm2,
            mux_control_footprint_mm2=logic_extra_mm2,
            CDC_storage_bits=cdc_bits,CDC_storage_footprint_mm2=cdc_mm2,
            composed_die_mm2=cdc_mm2+l2['area']['composed_die_mm2']+metadata_mm2+data_mm2+logic_extra_mm2,
            core_available_mm2=l2['area']['core_available_mm2'],SM_slot_fit=False,
            no_free_reuse='Separate64KB/clientgather charged unless actualSMringsectorwrite composition proves reuse; extraSRAM/metadata locality mustfitrealW13SM/controllerLEF'),
        performance=dict(minimum_backend_read_ns=minimum_backend_ns,
            coalescer_map_gather_wire_control_cycles=boundary_cycles,
            loaded_round_trip_cycles=roundtrip,worst_jitter_cycles=55,
            credit_limited_worst_Bpc=credit_Bpc,selected_service_ceiling_Bpc=served,
            selected_service_ceiling_TB_s=served*clock/1e12,
            current_Qwen_token_HBM_bytes_per_die=traffic,
            current_token_FP8_KV_write_bytes_per_die=36*2*4*128,
            current_token_BF16_KV_write_bytes_per_die=36*2*4*128*2,
            FP8_KV_write_sector_commands=36*2*4*128//32,
            uncoalesced_transfer_lower_bound_cycles=math.ceil(traffic/512),
            LENW5_transfer_lower_bound_cycles=math.ceil(traffic/2048),
            selected_transfer_lower_bound_cycles=math.ceil(traffic/served),
            headline=False,speed_credit=0,
            note='These aretransferbounds,notconnectedtokenrates. Realpartialcommands,writeingresscompetition,bankturnarounds,queueoccupancy,network/CDC andproducer waits remain actualcycles'),
        CDC=dict(fast_clock_target_hz=1.2e9,vector_serial_clock_target_hz=.9e9,
            ratio='3serial:4fast',FIFO_pairs=32,FIFO_depth=16,entry_bits=256+64,
            storage_priced_separately=True,
            fast_cycles_roundtrip_allowance=8,
            acceptance='ActualasyncFIFO/gearbox read/write pointer and credit qualification; phasecounter alwaysadvancesfastclock, neveronvalidonly'),
        build_blockers=['Implementandqualify coalescer/tag/sector-gather and actualwriteack fulladdressbackend',
            'Full4x2MiBL2macro injector/commit/readback linkedto36clientservice',
            'ActualRF/vector/KV/TP consumers and3:4CDC with nextactivation read',
            'Real32SMLEF/floorplan slot+controller/SRAM/corridors andcontextualSS/FF beforephysicaladmission'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['tools/uarch_model.py','tools/uarch_qwen_hbm_ingress.py',
             'rtl/hdc/kv/ot_hdc_hbm_model.sv',
             'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json',
             'results/uarch/qwen_hbm_connected_20261001/L2_injector_before_RTL.json']})


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(compose(),f,indent=2);f.write('\n')
