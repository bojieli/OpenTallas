#!/usr/bin/env python3
"""Run the real BF front control component gate and source-mutation negatives.

This gate covers fixed issue edges, live BF operand identity, real CFG/walkers,
and fault independence. It deliberately makes no numerical column, immutable
CFG7 workload, production throughput or physical qualification claim.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CORE = 'rtl/v41rom/ot_v41_bf_front_core.sv'
FILES = ['tests/s81/tb_bf_static_core.sv', CORE,
         'rtl/v41rom/ot_v41_rom_elem_w10.sv', 'rtl/v41rom/ot_v41_kreg.sv',
         'rtl/common/ot_prefix.sv', 'rtl/hdc/ot_hdc_cg.sv']
MUTANTS = {
    'ready_fallback': ('? prog_issue_pin : issue_available', '? (prog_issue_pin && issue_available) : issue_available'),
    'address_unchecked': ('prog_addr_pin != a_ctr ||', "1'b0 ||"),
    'program_operand_unchecked': ('prog_operand_pin != programme_operand ||', "1'b0 ||"),
    'captured_operand_unchecked': ('f_identity[f_rd] != programme_operand', "1'b0"),
}

def main():
    src = (ROOT / CORE).read_text()
    results = {}
    with tempfile.TemporaryDirectory(prefix='bf-static-core-') as tmp:
        tmp = Path(tmp)
        for name in ['positive', *MUTANTS]:
            rtl = src
            if name != 'positive':
                before, after = MUTANTS[name]
                assert rtl.count(before) == 1, (name, before)
                rtl = rtl.replace(before, after)
            generated = tmp / f'{name}.sv'
            generated.write_text(rtl)
            binary = tmp / f'{name}.vvp'
            cmd = ['iverilog', '-g2012', '-s', 'tb_bf_static_core', '-o', str(binary)]
            cmd += [str(generated) if f == CORE else str(ROOT / f) for f in FILES]
            build = subprocess.run(cmd, capture_output=True, text=True)
            if build.returncode:
                raise RuntimeError(build.stderr)
            run = subprocess.run(['vvp', str(binary)], capture_output=True, text=True)
            if name == 'positive':
                assert run.returncode == 0 and 'PASS BF static core' in run.stdout, run.stdout + run.stderr
            else:
                assert run.returncode != 0 and 'FATAL' in run.stdout, (name, run.stdout, run.stderr)
            results[name] = {'exit': run.returncode, 'output': run.stdout.strip()}
    hashes = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
              for f in FILES + ['tools/s81/bf_static_program.py', 'tools/s81/gen_bf_hier.py']}
    print(json.dumps({'scope': 'BF front core control component only; not numerical/native/throughput/physical qualification',
                      'production_parameters': {'NSEG':8, 'NCH':16, 'XF':8, 'NB':2, 'FAST':1, 'PP':1, 'QPIPE':1, 'QX':10, 'TCG':1},
                      'compiled_issue_slots':64, 'input_fault_variants':6,
                      'source_sha256':hashes, 'results':results}, indent=2))

if __name__ == '__main__':
    main()
