#!/usr/bin/env python3
"""Direct-census generic prefix proof availability, not live elaboration/adoption.

Leaves the first proof package and six-width extension unchanged. No substitutes
are installed; indirect AW/CW/K specializations are outside this proof scope.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from prove_dsrom_generic_prefix_sat import ROOT, SOURCE_COMMIT, SOURCE, sha, classify, pinned, first_package_pins

CENSUS_COMMIT = '38f65a224720566fc68e32785e8f7622e8652b50'
CENSUS_DIR = 'results/rtl/w11_fastfp_prefix_sequential_gate_20261001'
SPECS = {'ot_hdc_ksadd_k': (8, 9, 12, 24, 26, 28, 31, 33, 48, 51), 'ot_hdc_inc_k': (24, 28, 31)}
MUTATIONS = {
    'direct_add_drop_carry': ('ot_hdc_ksadd_k', 51, 'assign cout = g[L][W];', "assign cout = 1'b0;"),
    'direct_add_flip_sum_bit0': ('ot_hdc_ksadd_k', 51, 'assign s = (a ^ b) ^ g[L][W-1:0];',
                               "assign s = ((a ^ b) ^ g[L][W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
    'direct_inc_drop_carry': ('ot_hdc_inc_k', 31, 'assign co = t[L][W];', "assign co = 1'b0;"),
    'direct_inc_flip_sum_bit0': ('ot_hdc_inc_k', 31, 'assign y = a ^ t[L][W-1:0];',
                               "assign y = (a ^ t[L][W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
}


def module_text(source: str, module: str) -> str:
    if module not in SPECS:
        raise ValueError('outside direct generic scope')
    matches = list(re.finditer(r'^module\s+' + re.escape(module) + r'\b.*?^endmodule\b[^\n]*', source, re.M | re.S))
    if len(matches) != 1:
        raise ValueError('expected one exact generic module')
    return matches[0].group() + '\n'


def miter(module: str, width: int) -> str:
    if module not in SPECS or type(width) is not int or width not in SPECS[module]:
        raise ValueError('outside direct generic scope')
    if module == 'ot_hdc_ksadd_k':
        return f'''module proof(input wire [{width-1}:0] a, b, input wire cin,
  output wire [{width}:0] actual, expected, output wire equal);
  wire [{width-1}:0] s;
  wire cout;
  ot_hdc_ksadd_k #(.W({width})) dut (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
  assign actual = {{cout, s}};
  assign expected = {{1'b0, a}} + {{1'b0, b}} + {{{{{width}{{1'b0}}}}, cin}};
  assign equal = (actual == expected);
endmodule
'''
    return f'''module proof(input wire [{width-1}:0] a, input wire inc,
  output wire [{width}:0] actual, expected, output wire equal);
  wire [{width-1}:0] y;
  wire co;
  ot_hdc_inc_k #(.W({width})) dut (.a(a), .inc(inc), .y(y), .co(co));
  assign actual = {{co, y}};
  assign expected = {{1'b0, a}} + {{{{{width}{{1'b0}}}}, inc}};
  assign equal = (actual == expected);
endmodule
'''


def prove_case(yosys: str, implementation: str, module: str, width: int, case_dir: Path, timeout: int = 60) -> dict:
    case_dir.mkdir()
    harness = miter(module, width)
    signals = 'a,b,cin,actual,expected,equal' if module == 'ot_hdc_ksadd_k' else 'a,inc,actual,expected,equal'
    script = ('read_verilog -sv implementation.sv miter.sv\n'
              'hierarchy -check -top proof\nproc\nflatten\nopt\ncheck -assert\n'
              f'sat -prove equal 1 -show {signals} -dump_json witness.json -timeout {timeout}\n')
    with tempfile.TemporaryDirectory(prefix='dsrom-direct-prefix-sat-') as scratch:
        scratch = Path(scratch)
        (scratch / 'implementation.sv').write_text(implementation)
        (scratch / 'miter.sv').write_text(harness)
        (scratch / 'run.ys').write_text(script)
        cmd = [yosys, '-Q', '-T', '-s', 'run.ys']
        try:
            r = subprocess.run(cmd, cwd=scratch, capture_output=True, text=True, timeout=timeout+15)
            returncode, log = r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b'', exc.stderr or b''
            log = (stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout)
            log += (stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr)
            log += '\nPROOF PROCESS TIMEOUT\n'
            returncode = None
        (case_dir / 'yosys.log').write_text(log)
        witness = scratch / 'witness.json'
        if witness.exists():
            shutil.copyfile(witness, case_dir / 'witness.json')
    return dict(module=module, width=width, verdict=classify(returncode, log), returncode=returncode,
                command=cmd, script=script, miter=harness, miter_sha256=sha(harness.encode()),
                implementation_sha256=sha(implementation.encode()), log_path=str(case_dir / 'yosys.log'),
                log_sha256=sha(log.encode()), witness_sha256=sha((case_dir / 'witness.json').read_bytes())
                if (case_dir / 'witness.json').exists() else None)


def run(output: Path, yosys: str) -> dict:
    executable = shutil.which(yosys)
    if not executable:
        raise ValueError('Yosys executable unavailable')
    executable = str(Path(executable).resolve())
    first = first_package_pins()
    census_pins = {}
    for name in ('consumer_width_census.json', 'generic_extension_scope.json'):
        path = f'{CENSUS_DIR}/{name}'
        data = subprocess.check_output(['git', 'show', f'{CENSUS_COMMIT}:{path}'], cwd=ROOT)
        census_pins[path] = dict(commit=CENSUS_COMMIT, sha256=sha(data))
        if name == 'generic_extension_scope.json':scope = json.loads(data)
    if scope['source_commit'] != SOURCE_COMMIT:
        raise ValueError('census source pin differs')
    consumers = {}
    for path, pin in scope['source_pins'].items():
        data = pinned(path)
        if sha(data) != pin['sha256']:
            raise ValueError(f'census source hash differs: {path}')
        consumers[path] = dict(commit=SOURCE_COMMIT, sha256=sha(data))
    notes = scope['resolved_width_notes']
    add_widths = sorted(set(notes['ksadd_literal_widths']) | {notes['fsqrt4_resolved']['ksadd_RW_plus_1'], notes['fsqrt4_resolved']['ksadd_Q_W_plus_2']})
    inc_widths = sorted(set(notes['inc_literal_widths']) | {notes['fsqrt4_resolved']['inc_Q_W_plus_2']})
    if add_widths != list(SPECS['ot_hdc_ksadd_k']) or inc_widths != list(SPECS['ot_hdc_inc_k']):
        raise ValueError('direct census widths differ from proof scope')
    source = pinned(SOURCE)
    implementations = {module: module_text(source.decode(), module) for module in SPECS}
    version = subprocess.check_output([executable, '-V'], text=True).strip()
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for module, widths in SPECS.items():
        for width in widths:
            case = prove_case(executable, implementations[module], module, width, output / f'{module}_w{width}')
            case['expected_verdict'] = 'PASS'
            cases.append(case)
            print(module, width, case['verdict'], flush=True)
    for name, (module, width, before, after) in MUTATIONS.items():
        if implementations[module].count(before) != 1:
            raise ValueError(f'mutation target not unique: {name}')
        case = prove_case(executable, implementations[module].replace(before, after), module, width, output / name)
        case.update(mutation=name, before=before, after=after, expected_verdict='FAIL')
        cases.append(case)
        print(name, case['verdict'], flush=True)
    artifacts = {str(path.relative_to(output)): dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size)
                 for path in sorted(output.rglob('*')) if path.is_file()}
    record = dict(schema='DSROM_direct_generic_prefix_combinational_SAT_availability_r1',
                  verdict='PASS_PREREQUISITE_ONLY' if all(c['verdict'] == c['expected_verdict'] for c in cases) else 'FAIL',
                  source_pin=dict(path=SOURCE, commit=SOURCE_COMMIT, sha256=sha(source)),
                  exact_modules={module: dict(text=text, sha256=sha(text.encode())) for module, text in implementations.items()},
                  census_pins=census_pins, consumer_source_pins=consumers,
                  direct_source_sites=scope['direct_generic_sites'], resolved_width_notes=notes,
                  availability_scope=SPECS, actual_live_elaboration_proven=False,
                  first_proof_package_byte_identity_pins=first,
                  dependency_tool_sha256=sha((ROOT / 'tools/prove_dsrom_generic_prefix_sat.py').read_bytes()),
                  proof_tool_sha256=sha(Path(__file__).read_bytes()),
                  proof_tests_sha256=sha((ROOT / 'tests/test_dsrom_direct_generic_prefix_sat.py').read_bytes()),
                  tools=dict(yosys=version, yosys_executable=executable,
                             yosys_executable_sha256=sha(Path(executable).read_bytes()), python=sys.version),
                  assumptions=[], cases=cases, artifacts=artifacts,
                  scope='All-input 2-state combinational proof availability for direct source-census widths. Add every s bit plus cout; increment every y bit plus co. No assertion of currently elaborated instances.',
                  excluded=['Indirect AW/CW/K footprints, 32-bit compare and 16-bit BF16 conditional wrappers', 'multiplier and CSA substitutions'],
                  remaining_gates=['Actual live compile/elaboration manifest including conditional parameters',
                                   'Sequential FP reset/valid/error/result/cycle equivalence', 'Future full-die gate before stand-in use'],
                  standins_installed=False, hardware_qualification=False, timing_claim=False, rate_claim=False, adoption=False)
    with (output / 'proof.json').open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--yosys', default='yosys')
    args = parser.parse_args()
    record = run(args.output, args.yosys)
    print(record['verdict'])
    raise SystemExit(0 if record['verdict'] == 'PASS_PREREQUISITE_ONLY' else 1)
