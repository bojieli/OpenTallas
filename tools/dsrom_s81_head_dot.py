#!/usr/bin/env python3
"""Opt-in SIM_ONLY released head DOT on actual native SU XN bits.

Extracted only from dsrom_s81_l20_sim_only.head_chain's ME branch. No norm,
argmax, expected outputs, VM publication, selector, or END. Caller owns actual
XN read acceptance and all subsequent native output/ACK/control lifetimes.
"""
import argparse
from pathlib import Path
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V

TP, ROWS, K, BATCH = 4, 32320, 5120, 128


def _dot_rows_u32(weights, xn_u32):
    """Original BF16 expansion, separate G.mul and ordered chunk8/padded tree."""
    if (not isinstance(xn_u32, np.ndarray) or xn_u32.shape != (K,)
            or xn_u32.dtype != np.dtype('<u4')):
        raise ValueError('actual native XN requires exactly 5120 little-endian uint32 bits')
    if weights.ndim != 2 or weights.shape[1] != K or weights.dtype != np.dtype('<u2'):
        raise ValueError('released head rows require BF16 uint16 storage, K5120')
    # Match head_chain's read(...).copy(): preserve the supplied produced XN.
    x = xn_u32.copy().view('<f4')
    logits = np.empty(len(weights), dtype=G.F)
    for begin in range(0, len(weights), BATCH):
        end = min(begin + BATCH, len(weights))
        w = G.from_bits(weights[begin:end].astype(np.uint32) << 16)
        logits[begin:end] = V.csum(G.mul(w, x[None, :]))
    return G.bits(logits).astype('<u4', copy=False)


def head_logits_u32(weights_bf16, rank, xn_u32):
    """32320 rank-local rows, global ID = rank*32320+row; no winner selection.

    weights_bf16 is the read-only released head.weight [129280,5120] raw BF16
    view, not a constructed model. xn_u32 comes from native SU readback at
    46464..51583. No rounding or normalization is applied to that input here.
    """
    if type(rank) is not int or not 0 <= rank < TP:
        raise ValueError('actual head rank must be 0..3')
    if weights_bf16.shape != (TP * ROWS, K):
        raise ValueError('released head.weight shape must be [129280,5120]')
    return _dot_rows_u32(weights_bf16[rank * ROWS:(rank + 1) * ROWS], xn_u32)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, required=True,
                   help='actual captured XN_rank0..3.u32; 5120 little-endian FP32 bits each')
    p.add_argument('--head-shard', type=Path, required=True, help='same released source shard as native HeadBytes')
    p.add_argument('--head-byte-offset', type=int, required=True, help='same actual absolute tensor byte offset as native HeadBytes')
    p.add_argument('--output-dir', type=Path, required=True, help='fresh directory for logits_rank0..3.u32')
    a = p.parse_args()
    needed = TP * ROWS * K * 2
    if a.head_byte_offset < 0 or a.head_byte_offset + needed > a.head_shard.stat().st_size:
        p.error('released head.weight byte extent outside source shard')
    inputs = []
    for rank in range(TP):
        path = a.input_dir / f'XN_rank{rank}.u32'
        if path.stat().st_size != K * 4:
            p.error('actual native XN file extent: ' + str(path))
        inputs.append(np.fromfile(path, dtype='<u4'))
    # Explicit invocation only; no integration/default behavior is changed.
    a.output_dir.mkdir(parents=True, exist_ok=False)
    weights = np.memmap(a.head_shard, mode='r', dtype='<u2',
                        offset=a.head_byte_offset, shape=(TP * ROWS, K))
    for rank, xn in enumerate(inputs):
        logits = head_logits_u32(weights, rank, xn)
        with (a.output_dir / f'logits_rank{rank}.u32').open('xb') as stream:
            logits.tofile(stream)


if __name__ == '__main__':
    main()
