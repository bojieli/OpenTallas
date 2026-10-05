#!/usr/bin/env python3
"""Read-only composition of the existing Qwen GPU model before checkpoint RTL gates."""
import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

import uarch_model as U
import rtl_gpu_sm_exact as S

ROOT = Path(__file__).resolve().parents[1]
QWEN_AREA_RECORDS = [
    'results/physical_abi3/asap7/gpu/ot_gpu_tc_col_l16_092/physical.json',
    'results/physical_abi3/asap7/gpu/ot_gpu_bd_col_lb2_092/physical.json',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sm_snapshot(revision):
    pin = subprocess.check_output(['git','rev-parse',revision+'^{commit}'],cwd=ROOT,text=True).strip()
    def read(path):
        return subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
    tree = ast.parse(read('tools/rtl_gpu_sm_exact.py'))
    node = next(n for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id == 'SMQ_SRC' for t in n.targets))
    paths = ast.literal_eval(node.value)
    proof_path = 'results/rtl/ot_hdc_prefix_vec_equiv.json'
    proof = json.loads(read(proof_path))
    if proof['status'] != 'pass':
        raise ValueError('W13 simulation prefix equivalence failed')
    for path,digest in proof['source_sha256'].items():
        if hashlib.sha256(read(path)).hexdigest() != digest:
            raise ValueError('W13 simulation prefix equivalence source drift')
    return dict(commit=pin, source_sha256={p:hashlib.sha256(read(p)).hexdigest() for p in paths},
                prefix_equivalence=dict(path=proof_path,sha256=hashlib.sha256(read(proof_path)).hexdigest(),
                                        widths=proof['widths']))


def preflight(cols=1, sm_source_commit=None):
    for path in QWEN_AREA_RECORDS:
        if not (ROOT/path).is_file():
            raise ValueError(f'Missing model calibration record: {path}; expand sparse checkout')
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
                sm_snapshot=sm_snapshot(sm_source_commit) if sm_source_commit else None,
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
                source_sha256={p: sha(ROOT/p) for p in sorted(set(S.SMQ_SRC + QWEN_AREA_RECORDS + [
                    'tools/uarch_model.py', 'tools/rtl_gpu_sm_exact.py',
                    'tools/w19_qwen_hbm_preflight_w12.py', 'tools/hdc_golden.py',
                    'tools/qwen3_deployment_quality.py', 'tools/hdc_qwen_int8_image_w12.py',
                    'compiler/models/qwen3-8b/checkpoint_source.json',
                    'results/floorplan/hbm_gpu/qwen_hbm_die.json']))})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cols', type=int, default=1)
    ap.add_argument('--sm-source-commit')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    record = preflight(args.cols, args.sm_source_commit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()
