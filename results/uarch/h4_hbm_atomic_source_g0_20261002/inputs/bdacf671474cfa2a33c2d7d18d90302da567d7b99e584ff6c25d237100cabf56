#!/usr/bin/env python3
"""Full-size banked L2 injector/service contract before connected RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_model as U

ROOT=Path(__file__).resolve().parents[1]


def compose():
    base=json.loads((ROOT/'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json').read_text())
    fit=json.loads((ROOT/'results/uarch/qwen_hbm_connected_20261001/GU_pipeline_total_fit_v3.json').read_text())
    # Eight producer-owned banks avoid the simultaneous row0 bank collision
    # of eight384-row SM partitions. The RTL descriptor retains canonical
    # global row and a checked local row; consumers address both explicitly.
    banks,macros_per_bank,macro_bytes=8,8,32*1024
    write_packet_bits=32+18+16+16+4
    ack_packet_bits=18+16+4+1
    read_packet_bits=256+64
    DMA_packet_bits=1024+32+16+4
    register_bits=2*banks*write_packet_bits+banks*ack_packet_bits+2*banks*read_packet_bits+DMA_packet_bits+10+banks*(18+16)
    mux_bits=banks*(macros_per_bank-1)*256+4*256+8*(write_packet_bits+ack_packet_bits)
    register_um2=register_bits*U.DFF_UM2
    mux_um2=mux_bits*.2
    control_um2=1024.0
    extra_per_slice=(register_um2+mux_um2+control_um2)/U.GPU_LOGIC_UTIL/1e6
    SRAM_per_slice=banks*macros_per_bank*U.GPU_UNIT_UM2['sram32k']*U.GPU_MACRO_PACK/1e6
    return dict(schema='opentallas.qwen-production-l2-injector-model.v1',
        status='model_before_RTL',full_token=False,physical_build_ready=False,adoption=False,
        shape=dict(TP_dies=2,SMs_per_die=32,L2_slices_per_die=4,
            producer_banks_per_slice=banks,macros_per_bank=macros_per_bank,
            macro='ot_sram_1r1w_1024x256_m2_r2c2',macro_bytes=macro_bytes,
            bytes_per_slice=banks*macros_per_bank*macro_bytes,
            macro_count_per_die=4*banks*macros_per_bank),
        address_contract=dict(bank='Static quadrant-local producer SM id0..7',
            scalar_local_row_bits=16,word_address_bits=13,macro_select_bits=3,
            SRAM_word_row_bits=10,FP32_lane_bits=3,global_row_bits=18,epoch_bits=16,
            mapping='bank=producer; macro=local_row[15:13]; word=local_row[12:3]; lane=local_row[2:0]',
            identity='RTL descriptor checks global_row=partition_base+local_row; actualproducer packet owns data. Canonical row metadata survives storage/readback',
            consumers='RTL vector/KV/TP consumer supplies explicit producer-bank/local-row/golden-index. No hostconcat/gather or arrival-order arithmetic'),
        ports=dict(scalar_write_ports_per_slice=8,scalar_write_Bpc_per_slice=32,
            physical_gather_bits_per_SM=256,read_ports_per_slice=8,
            read_Bpc_per_slice=256,DMA_line_bytes=128,
            write='One masked FP32 lane of a256bit SRAM word; no hostpostscale and no hidden read-modify-write',
            read='True1r1w banks, macroselect retained across SRAM read latency; read/write collision mustforward orstall explicitly',
            commit='ActualSRAMwrite acceptance plus retainedrow/epoch/id produces commit; inputready alone neverreleasesGUcredit'),
        service_contract=dict(clients=36,SM_weight_clients=list(range(32)),
            L2_vector_KV_clients=list(range(32,36)),quadrants=4,
            clients_per_quadrant=9,quadrant_clients=[[8*q+i for i in range(8)]+[32+q] for q in range(4)],
            client_credits=512,line_bytes=128,line_address_bits=32,
            global_tag_bits=16,tag_mapping='global_tag={client_id6,local_transaction_tag10}; no truncation or reuse before actualresponse/writeack',
            class_bits=4,request_metadata_bits=52,response_metadata_bits=20,
            request='Readmetadata consumes transactioncredit, not a second data-byte charge; retainedelastic request stableuntilaccepted',
            bandwidth='Readreturn and writepayload share same quadrant bytebudget, maximum750B/fastcycle average; bench/backend wait remains realclocktime',
            returned_lanes_per_quadrant=9,
            capacity='A single128B/cycle backend wouldundersize750B/cycle and is forbidden. Model requiresparallelreturn/write lanes with finite aggregatebytearbitration',
            acknowledgment='Writes acknowledged onlyafterbackendmemorycommit; no hostsoftware completion substitution'),
        area=dict(register_bits_per_slice=register_bits,register_logic_um2=register_um2,
            mux_two_input_bit_equivalents=mux_bits,mux_logic_um2=mux_um2,
            control_logic_assumption_um2=control_um2,
            added_controller_footprint_mm2_per_slice=extra_per_slice,
            SRAM_footprint_mm2_per_slice=SRAM_per_slice,
            SRAM_accounting='256actual32KBmacros replace baseline8MiBL2 budget, not additional fictitiouscache. FinalLEF/placement/SSclk-to-q stillrequired',
            composed_die_mm2=fit['element_area']['composed_die_mm2']-
                base['base_design']['die_fit']['l2_mm2']+4*(SRAM_per_slice+extra_per_slice),
            core_available_mm2=base['floorplan_fit']['available_mm2'],
            SM_slot_fit=False,SM_slot_blocker='Existing4.621mm2baseline exceeds4.085placeholder independentlyofsmallGUincrement',
            placement='EightlocalSRAMbanks besideeachquadrantgather; controller/DMA atL2edge. Actualmacroarray+36clientcorridors mustfit currentW13LEFfull32SMfloorplan'),
        routing=dict(weight_vertical_bits=1088,weight_vertical_capacity=2696,
            vector_horizontal_bits=2368,vector_horizontal_capacity=4104,
            assignment='Separatequadrantweightcorridors fromcentralvectorcorridors; no weightbroadcast acrossdie',
            adoption_gate='Actualhub routing-layer check and contextualSSsetup/FFhold at60ps/25ps'),
        latency=dict(write_capture_cycles=1,SRAM_write_cycles=1,commit_ack_cycles=1,
            result_to_matching_commit_unstalled_cycles=3,SRAM_read_cycles=1,DMA_assemble_cycles=4,
            existing_commit_allowance_cycles=11,additional_token_speed_credit=0,
            fit='3localcycles remainwithin11cycle resultcommit allowance; backend/service/CDC/hop waits must be separately measured, never subtracted as hostwait'),
        next_connected_gate='GU64actualRTLscale -> realfullsizeL2macro writes -> checkedcommit/readback -> finite36clientHBMwrite+actualbackendack -> RTLconsumerread. ThenKV/attention/vector/TP andfulltoken',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['tools/uarch_model.py','tools/uarch_qwen_l2_injector.py',
             'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json',
             'results/uarch/qwen_hbm_connected_20261001/GU_pipeline_total_fit_v3.json']})


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(compose(),f,indent=2);f.write('\n')
