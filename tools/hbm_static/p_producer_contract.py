#!/usr/bin/env python3
"""Full-shape port sizing for the actual unnormalized DeepSeek P producer.

This contract prices real buffers and immutable tap latency. It deliberately
does not invent the missing whole-chain programme or physical allocation.
"""
import json


def contract(rows):
    if rows not in (128, 640):
        raise ValueError('production T must be 128 or 640')
    heads = 16
    words = heads * rows
    return {
        'heads': heads, 'rows': rows, 'words': words,
        'arithmetic': 'MB=max(FP32(score*scale)); E=exp(FP32(score*scale-MB)); '
                      'SE=golden_csum8(E); EB=BF16_RNE(E); P=expanded_FP32(EB)',
        'normalization': 'ATTPV uses unnormalized EB; PV/(sinkexp+SE) occurs later',
        'scalar_tags': {'MB': '2*head', 'SE': '2*head+1'},
        'source_buffer': {
            'macro': 'ot_sram_1r1w_128x256_m1_r2c2', 'replicas': 8,
            'physical_bytes': 32768, 'live_head_bytes': rows * 4,
            'fill_bytes_per_edge': 256, 'fill_edges_per_head': rows // 64,
            'read_bytes_per_edge': 4, 'read_latency_edges': 1,
            'max_source_order': '0..T-1',
            'sum_source_order': 'for offset in0..7: for chunk in0..T/8-1: 8*chunk+offset',
            'source_read_edges_all_max_and_sum': 2 * words,
            'minimum_operand_scan_edges': 2 * words,
            'sram_reuse': 'SCscaled then unrounded E, only after each head reducer drains',
        },
        'scalar_publisher': {
            'bytes_per_edge': 4, 'writes': 2 * heads,
            'sectors_per_write': 1, 'mask': '1<<word; seven neighbors preserved',
            'output_register_edges': 1,
            'tap_capture_edges_after_scalar_observed': 2,
            'vm_write_update_edges_after_tap_capture': 11,
            'vm_commit_edges_after_scalar_observed': 13,
            'vm_read_update_edges_after_tap_capture': 14,
            'sfu_scalar_capture_edges_after_tap_capture': 15,
        },
        'output_drains': [
            {'kind': 'E', 'round_bf16': 0, 'words': words, 'consumer': 'actual golden SUM'},
            {'kind': 'EB', 'round_bf16': 1, 'words': words, 'consumer': 'actual VM P -> ATT prefetch'},
        ],
        'required_real_chain': [
            'QK score serializer -> actual SC VM',
            'actual SFU MUL scale -> scaled SC VM -> source SRAM -> actual REDMAX',
            'masked MB VM publish -> actual SFU scalar fetch',
            'actual SFU MUL scale / AD_NEGB MB / EXP co_rnd0 -> unrounded E VM',
            'unrounded E VM -> source SRAM -> actual csum8 -> masked SE VM publish',
            'same real E output -> BF16 RNE drain -> actual P VM',
            'actual P VM -> ATT P prefetch -> actual PV',
        ],
        'open_gates': ['source-pinned dependency publication', 'canonical SC/E/MB/SE/P aperture allocation',
                       'actual whole-chain command/IO calendar', 'arithmetic whole-chain bench+mutants',
                       'physical slot, ports and routed timing', 'production throughput'],
        'physical_qualified': False, 'production_qualified': False,
        'native_whole_kernel_qualified': False,
    }


if __name__ == '__main__':
    print(json.dumps([contract(128), contract(640)], indent=2))
