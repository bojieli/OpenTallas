"""Reprice the three GPU comparator paths after the index-source fairness fix.

Preserve the actual previous analytical output; no GPU generation or native
execution. ROM numerators use the unchanged, source-pinned routed-wire result.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

import uarch_model as u

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_gpu_index_scan_correction_20261003'
BASE = 'b8d265e1130503d6dbbe72206618f801154f6022'
CTXS = (3072, 8192, 200000, 1048576)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def function_pins(source):
    tree = ast.parse(source)
    names = {'_cons_adjust', 'cons_v41_rom', 'hub_edge_hop_wire_s', '_v41_graph'}
    return {node.name: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
            for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names}


def generate():
    old = json.loads((OUT / 'before.json').read_text())
    source = ROOT / 'tools/uarch_model.py'
    previous = subprocess.check_output(['git', 'show', BASE + ':tools/uarch_model.py'], cwd=ROOT, text=True)
    if function_pins(previous) != function_pins(source.read_text()):
        raise ValueError('ROM wire functions changed: cannot reuse frozen numerator')
    wire_path = ROOT / 'results/uarch/dsrom_hub_edge_wires_20261003/model.json'
    wire = json.loads(wire_path.read_text())
    after = dict(tier2=u.gpu_tier2(), economics=u.gpu_economics(),
                 contexts={str(ctx): dict(seconds=u.gpu_tier2_v41_ctx(ctx),
                                          mtp_seconds=u.gpu_tier2_v41_ctx(ctx, 6),
                                          full_score_seconds=u.gpu_tier2_v41_ctx(ctx, candidate_gather=False))
                           for ctx in CTXS})
    # JSON records stringify numeric calibration-map keys; compare that same
    # representation rather than reporting an unrelated numerical change.
    after = json.loads(json.dumps(after))
    if old['tier2'][0] != after['tier2'][0] or old['economics']['qwen'] != after['economics']['qwen']:
        raise ValueError('unrelated Qwen GPU comparator changed')
    contexts = {}
    for ctx in CTXS:
        scan = u.v41_gpu_index_scan(ctx)
        legacy = ctx * 38 * u.A.IDX_KEY_B
        before_s = old['contexts'][str(ctx)]['seconds']; now = after['contexts'][str(ctx)]
        contexts[str(ctx)] = dict(index_scan=scan, full_score_scan=u.v41_gpu_index_scan(ctx, candidate_gather=False),
                                 old_index_bytes=legacy, old_over_canonical_bytes=legacy / scan['bytes'],
                                 before_AR_tok_s=1 / before_s, after_AR_tok_s=1 / now['seconds'],
                                 after_full_score_AR_tok_s=1 / now['full_score_seconds'],
                                 token_latency_delta_us=(now['seconds'] - before_s) * 1e6,
                                 gpu_rate_gain_pct=100 * (before_s / now['seconds'] - 1))
    ratios = []
    for numerator in wire['results']:
        ctx = numerator['ctx']; gpu = after['contexts'][str(ctx)]
        ratios.append(dict(mapping=numerator['id'], ctx=ctx,
                           ROM_AR_tok_s=numerator['ar_tok_s'], ROM_MTP_tok_s=numerator['mtp_tok_s'],
                           GPU_AR_tok_s=1 / gpu['seconds'], GPU_full_score_AR_tok_s=1 / gpu['full_score_seconds'],
                           ROM_over_GPU_AR_before=numerator['ar_tok_s'] * old['contexts'][str(ctx)]['seconds'],
                           ROM_over_GPU_AR=numerator['ar_tok_s'] * gpu['seconds'],
                           ROM_over_GPU_AR_full_score=numerator['ar_tok_s'] * gpu['full_score_seconds'],
                           ROM_over_GPU_MTP_before=numerator['mtp_tok_s'] * old['contexts'][str(ctx)]['seconds'] / 1.94,
                           ROM_over_GPU_MTP=numerator['mtp_tok_s'] * gpu['seconds'] / 1.94))
    inputs = ['tools/uarch_model.py', 'tools/dsrom_gpu_index_scan_correction.py',
              'tools/arch_budget_v41.py', 'tools/decode_critical_path.py', 'tools/hdc_golden_v41.py',
              'compiler/models/deepseek-v4.1-flash/inference_config.json',
              'configs/models/candidates/deepseek-v4.1-flash.json',
              'results/rtl/w19_hbm_tp96_program_oreduce.json',
              'results/uarch/dsrom_gpu_index_scan_correction_20261003/before.json',
              'results/uarch/dsrom_hub_edge_wires_20261003/model.json']
    return dict(schema='opentallas.dsrom.gpu-index-source-correction.v1', previous_source_revision=BASE,
                source_sha256={s: sha(ROOT / s) for s in inputs},
                unchanged_wire_result_sha256=sha(wire_path), unchanged_ROM_function_pins=function_pins(previous),
                before=old, after=after, contexts=contexts, comparative_ratios=ratios,
                assumptions=dict(canonical='same 8 scans, source ratios/KV sharing and candidate cap as ROM analytical budget',
                                 candidate_gather='last4 scans limited to2048 blocks x8; conditional software optimization, not current native execution',
                                 literal_source='golden and current TP96 native n compute full late4 scores before masking; full-score sensitivity retained',
                                 unchanged='weight/fixed/collective fit, packing68B/key, TP8, power, storage capacity; comparison MTP keeps existing1.94x tier2 multiplier',
                                 qualification='tier2 calibrated projection only; no new acceptance, hardware clock, native execution or physical credit'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT / 'model.json')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    data = json.dumps(generate(), indent=2, sort_keys=True) + '\n'
    if args.verify:
        if args.out.read_text() != data:
            raise ValueError('repricing record differs from exact replay')
        print('PASS_EXACT_ANALYTICAL_REPLAY')
    else:
        if args.out.exists() and args.out.read_text() != data:
            raise ValueError('refuse to overwrite a different record')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data)
        print(args.out)


if __name__ == '__main__':
    main()
