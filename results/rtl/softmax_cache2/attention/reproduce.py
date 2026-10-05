"""Rebuild matched complete-attention runs and reject stale source evidence."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
VERILATOR = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
INVENTORY = json.loads((HERE/'sources.json').read_text())


def verify():
    for group in INVENTORY.values():
        for name, expected in group.items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name


def main():
    verify()
    for variant in ('baseline', 'candidate'):
        build = ROOT/'build'/('attention_cache2_' + variant)
        cmd = [str(VERILATOR), '--binary', '--timing', '-j', '2', '-Wno-fatal',
               '--top-module', 'tb_a3_attention_sparse', '--Mdir', str(build)]
        for directory in ('rtl/abi3', 'rtl/lib', 'rtl/proto', 'rtl'):
            cmd += ['-y', directory]
        cmd += ['rtl/ot_fp32_rne_pkg.sv', 'rtl/abi3/ot_a3_engine_pkg.sv',
                'rtl/abi3/ot_a3_format_pkg.sv']
        if variant == 'candidate':
            cmd += ['results/rtl/softmax_cache2/candidate.sv']
        cmd += ['rtl/test/tb_a3_attention_sparse.sv']
        with (HERE/(variant+'_compile.log')).open('w') as out:
            subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, check=True)
        with (HERE/(variant+'.log')).open('w') as out:
            subprocess.run([str(build/'Vtb_a3_attention_sparse'), '+profile'],
                           cwd=ROOT/'build/kv_index_prefix_attention_vectors',
                           stdout=out, stderr=subprocess.STDOUT, check=True)
        log = (HERE/(variant+'.log')).read_text()
        assert 'PASS a3_attention_sparse: 9 transactions' in log and 'FAIL' not in log
    verify()


if __name__ == '__main__':
    main()
