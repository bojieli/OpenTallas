#!/usr/bin/env python3
"""Read-only composition of the existing Qwen GPU model before checkpoint RTL gates."""
import argparse
import hashlib
import json
from pathlib import Path

import uarch_model as U
import rtl_gpu_sm_exact as S

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(cols=1):
    design = U.hbm_gpu_design('qwen')
    e = design['element']
    if cols not in (1, e['cols']):
        raise ValueError('AR specialization (1) or full model columns (16) only')
    if (e['subparts'], e['int8_lanes'], e['il'], design['sm_count']) != (4, 128, 8, 32):
        raise ValueError('GPU SM contract changed; recompose before building')
    # QKV is 3072 x 4096 per TP2 die. Preserve shipped golden split 256;
    # 2 groups of 128 chunks, each chunk 16 sequential products.
    rows, k, split = 96, 4096, 256
    return dict(schema='opentallas.w19-qwen-hbm-preflight.v1',
                status='model_composed_before_build', design=design, tp=2,
                operation=dict(stage='layer0.qkv', rows_die=3072, rows_sm=rows,
                               K=k, split=split, chunk_len=16, groups=2,
                               weight_lines=rows*k//128, weight_bytes=rows*k,
                               arithmetic_intensity_macs_per_weight_byte=cols,
                               tested_cols=cols, physical_cols=e['cols'],
                               weight_Bpc=128, x_fragment_bits=128*cols*16,
                               result_bits=32*cols, row_scale_bytes=2,
                               x_macro_words=96,
                               replica_policy='one SM tested; 32 per die, two TP dies',
                               arithmetic='BF16 input; sequential contiguous K chunks; pairwise FP32 tree; one BF16 row-scale FP32 multiply'),
                physical_status='existing model only; no new hardware, SS/FF or routing claim',
                clock_status='inherited analytical clock; 1.2 GHz SS/FF headline remains unqualified',
                adoption=False,
                claim_boundary='Checkpoint producer/component gate preparation, not a full RTL token or an adopted performance lever.',
                remaining_full_token_exit=[
                    'All 32 SM row slices per die, all 36 layers and vocabulary head',
                    'RTL norm/QK/RoPE/FP8 KV/attention/SFU/residual and ordered TP scale composition',
                    'L2 gather, x broadcast and 32-SM barrier runtime; physical 16-column element',
                    'Bit-exact reference token and every checkpoint boundary with connected RTL cycle count fed to unified model',
                    'In-context SS setup/FF hold, 60ps/25ps uncertainties and hub routing gate'],
                source_sha256={p: sha(ROOT/p) for p in sorted(set(S.SMQ_SRC + [
                    'tools/uarch_model.py', 'tools/rtl_gpu_sm_exact.py',
                    'tools/w19_qwen_hbm_preflight.py', 'tools/hdc_golden.py',
                    'tools/qwen3_deployment_quality.py', 'tools/hdc_qwen_int8_image.py',
                    'compiler/models/qwen3-8b/checkpoint_source.json',
                    'results/floorplan/hbm_gpu/qwen_hbm_die.json']))})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cols', type=int, default=1)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f:
        json.dump(preflight(args.cols), f, indent=2, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()
