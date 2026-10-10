#!/usr/bin/env python3
"""CPU-only minimum-bank exactness gate with the physical SRAM model."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'tests/rtl/tb_hbm_svc_dma_sram_bank.sv',
    'rtl/common/ot_secded.sv',
    'rtl/hbm/hbm_svc_dma_sram_bank.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
]


def run():
    records = []
    with tempfile.TemporaryDirectory(prefix='hbm-bank-') as scratch:
        for mutant in (0, 1):
            output = str(Path(scratch) / f'bank-{mutant}.vvp')
            command = ['iverilog', '-g2012', '-DOT_MEM_NO_INIT', '-I', 'rtl/common',
                       '-s', 'tb_hbm_svc_dma_sram_bank',
                       f'-Ptb_hbm_svc_dma_sram_bank.MUT={mutant}', '-o', output, *SOURCES]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
            result = subprocess.run(['vvp', output], cwd=ROOT, capture_output=True, text=True)
            passed = result.returncode == 0 and 'PASS transactions=' in result.stdout
            records.append({'mutant': mutant, 'returncode': result.returncode,
                            'stdout': result.stdout, 'stderr': result.stderr,
                            'expected_outcome': 'PASS' if mutant == 0 else 'FAIL_wrong_ECC_column',
                            'gate_pass': passed if mutant == 0 else not passed})
    pin = SOURCES + ['rtl/common/ot_secded_cols.svh',
                     'tools/hbm_svc_dma_sram_bank_model.py',
                     'tools/run_hbm_svc_dma_sram_bank_bench.py']
    evidence = {'scope': 'one bank, one real 128x256 macro model; CPU, no full-array simulation',
                'macro_initialization': 'disabled; absent rows never publish uninitialized data',
                'physical_signoff': 'not established by this bench',
                'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in pin},
                'records': records, 'verdict': 'PASS' if all(r['gate_pass'] for r in records) else 'FAIL'}
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    evidence = run()
    payload = json.dumps(evidence, indent=2) + '\n'
    if args.output:
        # Immutable evidence: never overwrite a previous verdict.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as f:
            f.write(payload)
    print(payload)
    raise SystemExit(0 if evidence['verdict'] == 'PASS' else 1)
