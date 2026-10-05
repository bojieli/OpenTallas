#!/usr/bin/env python3
"""Separate combinational prerequisite for the live generic prefix-adder widths.

Installs no substitutions. Sequential FP reset/valid/error/result/cycle and a
future full-die gate are required before simulation stand-in use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '4e38326d6f361bc85e660f48c59c355e2bb95274'
FIRST_PROOF_COMMIT = '29ace40b6f563c980c0b42b7d6eba32c91a2fc93'
SOURCE = 'rtl/hdc/ot_hdc_prefix.sv'
MODULE = 'ot_hdc_ksadd_k'
WIDTHS = (8, 12, 24, 28, 31, 48)
CONSUMERS = ('rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv')
MUTATIONS = {
    'generic_drop_carry': ('assign cout = g[L][W];', "assign cout = 1'b0;"),
    'generic_flip_sum_bit0': ('assign s = (a ^ b) ^ g[L][W-1:0];',
                              "assign s = ((a ^ b) ^ g[L][W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def module_text(source: str) -> str:
    matches = list(re.finditer(r'^module\s+' + MODULE + r'\b.*?^endmodule\b[^\n]*', source, re.M | re.S))
    if len(matches) != 1:
        raise ValueError('expected one exact generic-adder module')
    return matches[0].group() + '\n'


def miter(width: int) -> str:
    if type(width) is not int or width not in WIDTHS:
        raise ValueError('outside pinned generic-adder scope')
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


def classify(returncode: int, log: str) -> str:
    if returncode == 0 and 'SAT proof finished - no model found: SUCCESS!' in log:
        return 'PASS'
    if returncode == 0 and 'SAT proof finished - model found: FAIL!' in log:
        return 'FAIL'
    return 'ERROR'


def prove_case(yosys: str, implementation: str, width: int, case_dir: Path, timeout: int = 60) -> dict:
    case_dir.mkdir()  # Never overwrite an earlier verdict or log.
    harness = miter(width)
    script = ('read_verilog -sv implementation.sv miter.sv\n'
              'hierarchy -check -top proof\nproc\nflatten\nopt\ncheck -assert\n'
              f'sat -prove equal 1 -show a,b,cin,actual,expected,equal -dump_json witness.json -timeout {timeout}\n')
    with tempfile.TemporaryDirectory(prefix='dsrom-generic-prefix-sat-') as scratch:
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
    return dict(module=MODULE, width=width, verdict=classify(returncode, log), returncode=returncode,
                command=cmd, script=script, miter=harness, miter_sha256=sha(harness.encode()),
                implementation_sha256=sha(implementation.encode()), log_path=str(case_dir / 'yosys.log'),
                log_sha256=sha(log.encode()), witness_sha256=sha((case_dir / 'witness.json').read_bytes())
                if (case_dir / 'witness.json').exists() else None)


def pinned(path: str, commit: str = SOURCE_COMMIT) -> bytes:
    original = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)
    if (ROOT / path).read_bytes() != original:
        raise ValueError(f'original differs from pin: {path}')
    return original


def first_package_pins() -> dict:
    paths = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r',
                                     FIRST_PROOF_COMMIT], cwd=ROOT, text=True).splitlines()
    if len(paths) != 25:
        raise ValueError('first proof package inventory differs')
    return {path: dict(commit=FIRST_PROOF_COMMIT, sha256=sha(pinned(path, FIRST_PROOF_COMMIT))) for path in paths}


def run(output: Path, yosys: str) -> dict:
    executable = shutil.which(yosys)
    if not executable:
        raise ValueError('Yosys executable unavailable')
    executable = str(Path(executable).resolve())
    retained = first_package_pins()
    source = pinned(SOURCE)
    implementation = module_text(source.decode())
    consumers = {}
    for path in CONSUMERS:
        data = pinned(path)
        sites = [dict(line=i, width=int(match.group(1)), text=line.strip())
                 for i, line in enumerate(data.decode().splitlines(), 1)
                 if (match := re.search(r'ot_hdc_ksadd_k\s*#\(\.W\((\d+)\)\)', line))]
        consumers[path] = dict(commit=SOURCE_COMMIT, sha256=sha(data), instance_sites=sites)
    if sorted({site['width'] for c in consumers.values() for site in c['instance_sites']}) != list(WIDTHS):
        raise ValueError('confirmed consumer width census differs')
    version = subprocess.check_output([executable, '-V'], text=True).strip()
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for width in WIDTHS:
        case = prove_case(executable, implementation, width, output / f'ot_hdc_ksadd_k_w{width}')
        case['expected_verdict'] = 'PASS'
        cases.append(case)
        print(MODULE, width, case['verdict'], flush=True)
    for name, (before, after) in MUTATIONS.items():
        if implementation.count(before) != 1:
            raise ValueError(f'mutation target not unique: {name}')
        case = prove_case(executable, implementation.replace(before, after), 48, output / name)
        case.update(mutation=name, before=before, after=after, expected_verdict='FAIL')
        cases.append(case)
        print(name, case['verdict'], flush=True)
    artifacts = {str(path.relative_to(output)): dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size)
                 for path in sorted(output.rglob('*')) if path.is_file()}
    record = dict(schema='DSROM_generic_prefix_combinational_SAT_prerequisite_r1',
                  verdict='PASS_PREREQUISITE_ONLY' if all(c['verdict'] == c['expected_verdict'] for c in cases) else 'FAIL',
                  source_pin=dict(path=SOURCE, commit=SOURCE_COMMIT, sha256=sha(source), module=MODULE,
                                  module_text=implementation, module_sha256=sha(implementation.encode())),
                  consumer_source_pins=consumers, consumer_authority='Parent confirms these consumers are in actual submitted live source list; literal sites independently checked at source pin. No full-die elaboration performed.',
                  first_proof_package_byte_identity_pins=retained,
                  proof_tool_sha256=sha(Path(__file__).read_bytes()),
                  proof_tests_sha256=sha((ROOT / 'tests/test_dsrom_generic_prefix_sat.py').read_bytes()),
                  tools=dict(yosys=version, yosys_executable=executable,
                             yosys_executable_sha256=sha(Path(executable).read_bytes()), python=sys.version),
                  assumptions=[], cases=cases, artifacts=artifacts,
                  scope='All-input 2-state combinational equality of every sum bit plus carry to widened behavioral a+b+cin.',
                  excluded=['generic inc_k without confirmed live instance', 'multiplier and CSA substitutions'],
                  remaining_gates=['Formal live reachability/source census by parent reviewer',
                                   'Sequential FP reset/valid/error/result/cycle equivalence', 'Future full-die gate before stand-in use'],
                  standins_installed=False, hardware_qualification=False, timing_claim=False, rate_claim=False, adoption=False)
    with (output / 'proof.json').open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new directory; retained evidence is never overwritten')
    parser.add_argument('--yosys', default='yosys')
    args = parser.parse_args()
    record = run(args.output, args.yosys)
    print(record['verdict'])
    return 0 if record['verdict'] == 'PASS_PREREQUISITE_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
