#!/usr/bin/env python3
"""Resource and clock contract for the wide WB successor; not PHY qualification."""
import argparse
import hashlib
import json
from pathlib import Path


def report():
    rtl = Path(__file__).with_name('ot_hbm_svc_wb_pipeline_cdc.sv')
    return dict(
        schema='opentallas.wb-pipeline-cdc-model.v1',
        source_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),
        logical_banks=32, actual_SRAM_macros=32, SRAM_rows=128,
        SRAM_width=256, payload_capacity_bytes=131072,
        SRAM_address='{block_bank,ordinal[10:5]}', SRAM_bank='ordinal[4:0]',
        fixed_input_sectors_per_stream_cycle=8,
        copy_max_sectors_per_stream_cycle=32, copy_II=1,
        copy_pending_words_per_lane=1,
        payload_FIFO=dict(count=32, width=288, depth=4, payload_FF=36864),
        metadata_FIFO=dict(count=2, width=29, depth=4),
        clock_contract=dict(
            stream_clock_period_ps=833.333, HBM_clock_period_ps=1024,
            stream_FIFO_root_ports=4, FIFO_lanes_per_root=8,
            payload_FF_per_FIFO_root=9216,
            FIFO_write_pointer_and_sync_FF_per_root=120,
            local_reset_sync_FF_per_root=2,
            root_phase='Each stream_fifo_clk input must have stream_clk frequency and phase; synchronous root-to-root timing constraints required.',
            actual_reset_synchronizers=6,
            physical_clock_tree_qualified=False),
        PHY=dict(native_sector_address_bits=30, request_len=1,
                 max_outstanding_per_PC=64, counter_bits_per_PC=7,
                 policy='Selected FIFO head locks under backpressure; pop only on acceptance; simultaneous done and accept preserve count.',
                 block_policy='One active descriptor until all actual completions return matching asynchronous bank/epoch/count ACK.'),
        qualification=dict(actual_SRAM_CDC_bench=True,
                           actual_PHY_joint=False,
                           compiler_calendar=False,
                           physical_adoption=False,
                           note='Synthetic delayed or fast PHY bench responses prove mechanism only; immutable actual-PHY baseline and full joint timing gate remain separate.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out')
    args = parser.parse_args()
    result = json.dumps(report(), indent=2) + '\n'
    if args.out:
        Path(args.out).write_text(result)
    print(result, end='')
