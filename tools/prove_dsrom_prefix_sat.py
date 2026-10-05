#!/usr/bin/env python3
"""Source-pinned combinational prerequisites for simulation-only prefix substitutions.

No source-list edits or stand-ins are installed. Sequential FP reset, valid,
error and cycle equivalence, then a full-die gate, remain required before use.
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
SPECS = {
    'ot_hdc_ksa': ('rtl/hdc/ot_hdc_fastfp.sv', (8, 12, 24, 28, 31, 48)),
    'ot_hdc_sk_cadd': ('rtl/hdc/v41/ot_hdc_sk_arith.sv', (8, 23, 24, 27, 48, 53)),
}
MUTATIONS = {
    'ksa_drop_carry': ('ot_hdc_ksa', 48, 'assign cout = g[W];', "assign cout = 1'b0;"),
    'ksa_flip_sum_bit0': ('ot_hdc_ksa', 48, 'assign s = (a ^ b) ^ g[W-1:0];',
                          "assign s = ((a ^ b) ^ g[W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
    'cadd_drop_s0_overflow': ('ot_hdc_sk_cadd', 53, 'assign s0 = {gg[W-1], hp ^ c0};',
                             "assign s0 = {1'b0, hp ^ c0};"),
    'cadd_drop_s1_overflow': ('ot_hdc_sk_cadd', 53, 'assign s1 = {gg[W-1] | pp[W-1], hp ^ c1};',
                             "assign s1 = {1'b0, hp ^ c1};"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def module_text(source: str, module: str) -> str:
    matches = list(re.finditer(r'^module\s+' + re.escape(module) + r'\b.*?^endmodule\b[^\n]*',
                              source, re.M | re.S))
    if len(matches) != 1:
        raise ValueError(f'expected one exact module: {module}')
    return matches[0].group() + '\n'


def miter(module: str, width: int) -> str:
    if module not in SPECS or type(width) is not int or width not in SPECS[module][1]:
        raise ValueError('outside pinned proof scope')
    if module == 'ot_hdc_ksa':
        return f'''module proof(input wire [{width-1}:0] a, b, input wire cin,
  output wire [{width}:0] actual, expected, output wire equal);
  wire [{width-1}:0] s;
  wire cout;
  ot_hdc_ksa #(.W({width})) dut (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
  assign actual = {{cout, s}};
  assign expected = {{1'b0, a}} + {{1'b0, b}} + {{{{{width}{{1'b0}}}}, cin}};
  assign equal = (actual == expected);
endmodule
'''
    return f'''module proof(input wire [{width-1}:0] a, b,
  output wire [{width}:0] s0, s1, expected0, expected1, output wire equal);
  ot_hdc_sk_cadd #(.W({width})) dut (.a(a), .b(b), .s0(s0), .s1(s1));
  assign expected0 = {{1'b0, a}} + {{1'b0, b}};
  assign expected1 = {{1'b0, a}} + {{1'b0, b}} + {width+1}'d1;
  assign equal = (s0 == expected0) && (s1 == expected1);
endmodule
'''


def classify(returncode: int, log: str) -> str:
    # A frontend/timeout/process failure is never a successful negative control.
    if returncode == 0 and 'SAT proof finished - no model found: SUCCESS!' in log:
        return 'PASS'
    if returncode == 0 and 'SAT proof finished - model found: FAIL!' in log:
        return 'FAIL'
    return 'ERROR'


def prove_case(yosys: str, implementation: str, module: str, width: int,
               case_dir: Path, timeout: int = 60) -> dict:
    case_dir.mkdir()  # Refuse to overwrite any previous verdict/log.
    harness = miter(module, width)
    signals = ('a,b,cin,actual,expected,equal' if module == 'ot_hdc_ksa'
               else 'a,b,s0,s1,expected0,expected1,equal')
    script = ('read_verilog -sv implementation.sv miter.sv\n'
              'hierarchy -check -top proof\nproc\nflatten\nopt\ncheck -assert\n'
              f'sat -prove equal 1 -show {signals} -dump_json witness.json -timeout {timeout}\n')
    with tempfile.TemporaryDirectory(prefix='dsrom-prefix-sat-') as scratch:
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
    return dict(module=module, width=width, verdict=classify(returncode, log),
                returncode=returncode, command=cmd, script=script, miter=harness,
                miter_sha256=sha(harness.encode()), implementation_sha256=sha(implementation.encode()),
                log_path=str(case_dir / 'yosys.log'), log_sha256=sha(log.encode()),
                witness_sha256=sha((case_dir / 'witness.json').read_bytes())
                if (case_dir / 'witness.json').exists() else None)


def run(output: Path, yosys: str) -> dict:
    executable = shutil.which(yosys)
    if not executable:
        raise ValueError('Yosys executable unavailable')
    executable = str(Path(executable).resolve())
    originals, pins = {}, {}
    for module, (path, _) in SPECS.items():
        pinned = subprocess.check_output(['git', 'show', f'{SOURCE_COMMIT}:{path}'], cwd=ROOT)
        if (ROOT / path).read_bytes() != pinned:
            raise ValueError(f'original source differs from pin: {path}')
        originals[module] = module_text(pinned.decode(), module)
        pins[path] = dict(commit=SOURCE_COMMIT, sha256=sha(pinned),
                          module=module, module_text=originals[module],
                          module_sha256=sha(originals[module].encode()))
    version = subprocess.check_output([executable, '-V'], text=True).strip()
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for module, (_, widths) in SPECS.items():
        for width in widths:
            case = prove_case(executable, originals[module], module, width, output / f'{module}_w{width}')
            case['expected_verdict'] = 'PASS'
            cases.append(case)
            print(module, width, case['verdict'], flush=True)
    for name, (module, width, before, after) in MUTATIONS.items():
        if originals[module].count(before) != 1:
            raise ValueError(f'mutation target not unique: {name}')
        mutant = originals[module].replace(before, after)
        case = prove_case(executable, mutant, module, width, output / name)
        case.update(mutation=name, before=before, after=after, expected_verdict='FAIL')
        cases.append(case)
        print(name, case['verdict'], flush=True)
    artifacts = {}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            artifacts[str(path.relative_to(output))] = dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size)
    # Every input is free: no assumptions, fixed operands, or sequential bound.
    record = dict(schema='DSROM_prefix_combinational_SAT_prerequisite_r1',
                  verdict='PASS_PREREQUISITE_ONLY' if all(c['verdict'] == c['expected_verdict'] for c in cases) else 'FAIL',
                  source_commit=SOURCE_COMMIT, source_pins=pins,
                  proof_tool_sha256=sha(Path(__file__).read_bytes()),
                  proof_tests_sha256=sha((ROOT / 'tests/test_dsrom_prefix_sat.py').read_bytes()),
                  tools=dict(yosys=version, yosys_executable=executable,
                             yosys_executable_sha256=sha(Path(executable).read_bytes()), python=sys.version),
                  scope='Combinational all-input 2-state SAT only. KSA every s bit plus cout; cadd both W+1-bit outputs including overflow.',
                  assumptions=[], cases=cases, artifacts=artifacts,
                  compound_width_authority={'8':'exponent differences', '23':'u_inc2', '24':'sum/compare/u_inc',
                                            '27':'quot u_r1/u_r2 local W=27', '48':'seed local W=48',
                                            '53':'quot u_xr WA24+WB29 -> mul W=53'},
                  excluded=['multiplier and CSA substitutions', 'generic ksadd_k/inc_k absent confirmed live census requirement'],
                  remaining_gates=['Actual live reachability/source census confirmation',
                                   'Sequential FP reset/valid/error/result/cycle equivalence',
                                   'Future full-die gate before stand-in use'],
                  standins_installed=False, hardware_qualification=False, timing_claim=False,
                  rate_claim=False, adoption=False)
    with (output / 'proof.json').open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new directory; existing evidence is never overwritten')
    parser.add_argument('--yosys', default='yosys')
    args = parser.parse_args()
    record = run(args.output, args.yosys)
    print(record['verdict'])
    return 0 if record['verdict'] == 'PASS_PREREQUISITE_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
