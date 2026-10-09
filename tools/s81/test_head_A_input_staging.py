#!/usr/bin/env python3
"""Check aligned input transport against a supplied unmodified bundle source."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--original', type=Path, required=True)
    a = ap.parse_args()
    bundle = a.root / 'rtl/v41rom/ot_dsrom_head_bundle.sv'
    bench = a.root / 'rtl/test/s81/tb_head_A_input_staging.sv'
    delay = a.root / 'rtl/hdc/ot_hdc_delay.sv'
    original = a.original.read_text().replace('module ot_dsrom_head_bundle', 'module head_bundle_original')
    def strings(source):
        return source.replace('$sformatf("%sb", INSTANCE)', '"b"').replace('$sformatf("%sa%0d", INSTANCE, q)', '"a"')
    source = bundle.read_text()
    cases = {'baseline': source,
             'misaligned_payload': source.replace('.W(305), .D(A_INPUT_STAGES)', '.W(305), .D(A_INPUT_STAGES==0 ? 0 : A_INPUT_STAGES+1)'),
             'lost_B_data': source.replace('.d({row_in, xsa, bd_r})', ".d({row_in, xsa, A_INPUT_STAGES==0 ? bd_r : 32'd0})")}
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix='s81-A-staging-') as temp:
        d = Path(temp)
        (d / 'original.sv').write_text(strings(original))
        for name, variant in cases.items():
            assert name == 'baseline' or variant != source
            (d / 'candidate.sv').write_text(strings(variant))
            compile_result = subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(d/'sim'),
                str(delay), str(d/'original.sv'), str(d/'candidate.sv'), str(bench)], capture_output=True, text=True)
            if compile_result.returncode:
                raise RuntimeError(compile_result.stderr)
            result = subprocess.run(['vvp', str(d/'sim')], capture_output=True, text=True)
            outcomes[name] = dict(exit=result.returncode, output=result.stdout.strip())
            assert (result.returncode == 0) == (name == 'baseline'), outcomes[name]
    print(json.dumps(dict(pass_transport=True, stages=[0,4], bits_per_A=307,
        scope='transport-only element traffic stubs; no numerical or physical qualification',
        original_sha256=hashlib.sha256(a.original.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), cases=outcomes), indent=2))

if __name__ == '__main__':
    main()
