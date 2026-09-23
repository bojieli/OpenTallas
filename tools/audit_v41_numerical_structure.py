#!/usr/bin/env python3
"""Static dependency screen for pinned V4.1 routed block structure."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277/inference/kernel.py')


def bound(k, block=32, product_latency=1, merge_latency=1):
    if k <= 0 or block <= 0 or k % block or min(product_latency, merge_latency) < 1:
        raise ValueError('Requires positive integral blocks and latencies')
    # Unlimited independent partial engines. Scalar ordered block computation
    # is a specified candidate, not a claim about vendor tensor-core association.
    return block * product_latency + (k // block) * merge_latency


def main():
    m = json.loads((ROOT / 'configs/models/candidates/deepseek-v4.1-flash.json').read_text())
    op = m['metadata']['operator_config']
    ks = [op['hidden_size'], op['moe_intermediate_size']]
    sources = ['runtime/reference/formats.py', 'runtime/reference/swiglu.py',
               'runtime/reference/matrix.py', 'runtime/reference/deepseek_v41_oracle.py',
               'rtl/abi3/ot_a3_lane_pipelined.sv',
               'tools/audit_v41_numerical_structure.py',
               'configs/models/candidates/deepseek-v4.1-flash.json']
    out = {
        'schema': 'opentallas.v41-numerical-structure.v1',
        'status': 'conditional_block_architecture_requires_numerical_and_physical_qualification',
        'vendor_kernel_sha256': hashlib.sha256(VENDOR.read_bytes()).hexdigest(),
        'source_revision': m['source_revision'],
        'routed_block_k': 32, 'projection_k': ks,
        'partial_counts_per_output': [k // 32 for k in ks],
        'candidate_expert_only_us_at_1ghz': {
            str(latency): m['num_layers'] * sum(bound(k, product_latency=latency, merge_latency=latency) for k in ks) / 1000
            for latency in (1, 2, 3)},
        'candidate_scope': 'Parallel independent 32-product scalar ordered partials, then K-ordered FP32 partial accumulation; six experts and gate/up parallel, down dependent. Excludes scales, quantization, activation, transport and resource limits. Not vendor bit-equivalence or measured latency.',
        'correction': 'Whole-K g4 74.24us is conditional on a different recurrence and cannot reject the pinned block-structured vendor kernel.',
        'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
    }
    (ROOT / 'results/architecture/v41_numerical_structure.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
