#!/usr/bin/env python3
"""Package oracle-fed service arithmetic vectors; no formatter/commit proof."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from qwen_tp8_native_layer_oracle import fp8_decode


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(oracle_dir, die, out):
    report = json.loads((oracle_dir / 'oracle.json').read_text())
    rank = report['ranks'][str(die)]
    source = oracle_dir / f'die{die}'
    out.mkdir(parents=True, exist_ok=True)
    for src, dst in (('Q_input_fp32.hex', 'q.hex'), ('ATTN_fp32.hex', 'gold.hex')):
        (out / dst).write_bytes((source / src).read_bytes())
    # Invert finite E4M3 exactly. These rows have already undergone the
    # golden SU store rounding; do not introduce another FP32 quantization.
    lookup = {int(bits): code for code, bits in enumerate(fp8_decode(np.arange(256, dtype=np.uint8)).view(np.uint32))
              if code not in (127, 255)}
    lookup[0] = 0
    rows = []
    for kind in ('K', 'V'):
        previous = np.frombuffer((source / f'prior_{kind}_fp8.bin').read_bytes(), dtype=np.uint8).reshape(-1, 128)
        current = [int(word, 16) for word in (source / f'new_{kind}_row_fp32.hex').read_text().split()]
        if len(current) != 128 or previous.shape[0] != report['position']:
            raise ValueError('oracle K/V row count mismatch')
        last = np.array([lookup[bits] for bits in current], dtype=np.uint8)
        for row in [*previous, last]:
            rows.append(row[::-1].tobytes().hex())
    (out / 'kv.hex').write_text('\n'.join(rows) + '\n')
    metadata = {'schema': 'opentallas.qwen-tp8-checkpoint-service-vectors.v1',
                'status': 'ORACLE_FED_SERVICE_ARITHMETIC_COMPONENT_ONLY', 'die': die,
                'payload_layer': report.get('payload_layer', 0),
                'x_source': report.get('x_source', {'kind':'checkpoint_embedding'}),
                'collective_reference_profile': report.get('collective_reference_profile','legacy_linear8'),
                'position': report['position'], 'source_oracle_sha256': sha(oracle_dir / 'oracle.json'),
                'fused_program_sha256': rank['lowered_program_sha256'],
                'oracle_input_policy': report['input_policy'],
                'source_sha256': {'packager': sha(__file__), 'oracle': report['source_sha256']},
                'vector_sha256': {name: sha(out / name) for name in ('q.hex', 'kv.hex', 'gold.hex')},
                'claim_boundary': 'Actual checkpoint-derived Q/current KV plus declared FP8 history and independent expected attention outputs. Current KV is PRELOADED from oracle: this fixture does not prove actual SU/formatter/landing commit composition.'}
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f"packaged actual checkpoint-derived service case die{die}, context{report['position']+1}; store composition unproved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oracle', type=Path, required=True)
    parser.add_argument('--die', type=int, choices=range(8), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    package(args.oracle, args.die, args.out)

if __name__ == '__main__':
    main()
