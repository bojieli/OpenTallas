#!/usr/bin/env python3
"""Size the baseline GU64 phase/credit/scale/L2 pipeline before RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_model as U

ROOT=Path(__file__).resolve().parents[1]


def compose():
    # Same 16 addressed entries survive raw -> multiply -> ready -> sent ->
    # committed. No second output FIFO is hidden behind the unstallable pipe.
    # Actual AR companion stores one scalar FP32 per row, not a16-column
    # vector. Physical16-column SM remains the baseline; batch widening is
    # neither implemented nor qualified by this record.
    entry_fields=dict(FP32_scalar=32,global_row=18,epoch=16,BF16_scale=16,packed_state=3)
    data_bits=16*sum(entry_fields.values())
    control_fields=dict(reserved_slots=8,product_counts=8*7,clock_phase=3,
        raw_cursor=4,out_cursor=4,held_output_id=4,held_output_valid=1,
        sticky_fault=1,multiplier_id_delay=7*4,multiplier_valid_delay=8)
    control_bits=sum(control_fields.values())
    bits=data_bits+control_bits
    # Bit-mux proxy matches unified gpu_payload_transport_model's0.2um2.
    # Charge an extra activeAR multiplier until composition proves reuse of
    # the baseline row-scale unit. No duplicate hardware is silently free.
    mux_bits=15*(32+16+32+18+16)+7*36+16*32*2
    mux_um2=mux_bits*.2
    decode_um2=512.0  # explicit assumed grant/state/phase/identity control budget
    mul_um2=U.GPU_UNIT_UM2['fp32_mul']
    register_um2=bits*U.DFF_UM2
    total_extra_mm2=(register_um2+mux_um2+decode_um2+mul_um2)/U.GPU_LOGIC_UTIL/1e6
    baseline=json.loads((ROOT/'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json').read_text())
    floorplan=json.loads((ROOT/'results/floorplan/hbm_gpu/qwen_hbm_die.json').read_text())
    base_sm_mm2=baseline['base_design']['sm_area']['total_mm2']
    sm_slot_mm2=floorplan['sm_tile']['footprint_mm2']
    duplicate_AR_columns_mm2=baseline['base_design']['sm_area']['logic_um2']['mma_lanes_and_trees']/16/U.GPU_LOGIC_UTIL/1e6
    return dict(schema='opentallas.qwen-gu64-pipeline-sizing.v2',
        status='model_before_RTL',full_token=False,adoption=False,
        physical_columns=16,active_AR_columns=1,SM_replicas=32,
        MACs_per_active_column_fast_cycle=128,weight_Bpc=128,
        x_read_bits_per_active_column=1024,L2_AR_payload_Bpc=4,
        L2_physical_gather_bits_per_SM=256,
        FIFO=dict(entries=16,allocation='Two fixed entries per circulating slot',
            entry_payload='One scalar FP32 for the active AR column plus row/epoch/scale/packedstate',
            entry_fields_bits=entry_fields,control_fields_bits=control_fields,
            states=['free','reserved','raw','multiplying','ready','sent','committed'],
            release='Only matching actual L2 commit releases credits; a ready handshake is insufficient',
            stored_bits=data_bits,control_bits=control_bits,
            footprint_mm2_per_SM=bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6,
            replicated_mm2=32*bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6),
        element_area=dict(register_logic_um2=register_um2,mux_logic_um2=mux_um2,
            mux_two_input_bit_equivalents=mux_bits,mux_unit_um2=.2,
            control_logic_assumption_um2=decode_um2,additional_row_scale_mul_logic_um2=mul_um2,
            total_incremental_footprint_mm2_per_SM=total_extra_mm2,
            duplicate_AR_tensor_column_footprint_mm2=duplicate_AR_columns_mm2,
            conservative_unshared_companion_extra_mm2=total_extra_mm2+duplicate_AR_columns_mm2,
            conservative_unshared_SM_mm2=base_sm_mm2+total_extra_mm2+duplicate_AR_columns_mm2,
            tensor_accounting='Standalone RTL instantiates128additionalAR lanes unless later composition actually replaces/shares existingtensorcolumns; charge duplication for that organization, not fictional reuse',
            multiplier_accounting='Conservative extra1 multiplier; baseline already contains16. Remove extra only after actual replacement/reuse composition proves it',
            baseline_SM_mm2=base_sm_mm2,composed_SM_mm2=base_sm_mm2+total_extra_mm2,
            historical_slot_mm2=sm_slot_mm2,slot_fit=base_sm_mm2+total_extra_mm2<=sm_slot_mm2,
            die_core_available_mm2=baseline['floorplan_fit']['available_mm2'],
            composed_die_mm2=baseline['floorplan_fit']['existing_mm2']+
                baseline['floorplan_fit']['new_controller_mm2']+32*total_extra_mm2,
            placement='LocalrowFIFO/mux/multiplier beside TC result edge and quadrant L2 gather; slot abstract pending. Die budget is not slot fit',
            physical_build_ready=False),
        ports=dict(result_write_rows_per_cycle=2,scale_issue_rows_per_cycle=1,
            scale_return_rows_per_cycle=1,L2_send_rows_per_cycle=1,
            L2_commit_rows_per_cycle=1,scale_store='Reservation captures actual broadcast BF16 scale once per row',
            boundary_metadata_bits=18+16+4,
            mux_cost='16-way addressed raw/ready selection and one active-column row-scale multiply; no global weight broadcast'),
        phase=dict(IL=8,counter='Advances on every actual clock, including bubbles',
            acceptance='Step slot must equal actual clock phase; reserve two row credits before first product',
            products_per_leaf=64,slot_release='Both rows committed; no slot/tag reuse while results are outstanding'),
        latency=dict(product_and_64tree_cycles=56,FIFO_capture_cycles=1,
            last_burst_serialization_bound_cycles=16,row_scale_cycles=7,
            ready_register_cycles=1,unstalled_tail_bound_cycles=81,
            existing_model_drain_cycles=89,
            backend='Memory bubbles, ready stalls and L2 commit waits remain actual clock cycles, with no host replacement or hidden wait subtraction',
            pricing='Keep existing89-cycle drain and GU72 extra-token allowance; no gain credited. Replace only from the matched connected measurement'),
        gates=['Actual circulating phase with bubbles','Two-row result bursts under backpressure',
            'RTL BF16 row scaling and global row/epoch tags','Matching actual L2 commits before credit reuse',
            'Composed hub route and contextual SS/FF before adoption'],
        historical_U_scope='bad304 generator pin used only for qualified computational constants; not current source-currency or physical qualification',
        supersedes_sizing='f84f2e57e mistakenly budgeted512bit vector payload per entry and omitted explicit mux/multiplier/slot-fit pricing; historical record retained',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['tools/uarch_model.py','tools/uarch_qwen_gu64_pipeline.py',
             'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json',
             'results/floorplan/hbm_gpu/qwen_hbm_die.json']})


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(compose(),f,indent=2);f.write('\n')
