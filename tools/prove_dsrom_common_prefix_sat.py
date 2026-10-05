#!/usr/bin/env python3
"""Seven common-prefix combinational prerequisites; no substitutions installed.

Sequential fadd CUT379/LAT8, bmul2 LAT5, bterm2_w10 TW17/LAT11, wrapper
integration and a future full-die gate remain separate requirements.
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
BASE_COMMIT = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
SOURCE_COMMIT = '4e38326d6f361bc85e660f48c59c355e2bb95274'
CENSUS_COMMIT = '9696a5b920013eaa176f8ffe9995bef54da5d50f'
CENSUS_DIR = 'results/rtl/w11_field_common_prefix_coverage_gap_20261001'
SOURCE = 'rtl/common/ot_prefix.sv'
SOURCE_SHA = '01de55a0d8c474008eb4446e41e00788d466b5dfb2e2e8d85a0b70ff931f8cfc'
SPECS = {'ot_v41_ksadd': (12, 24, 28, 42), 'ot_v41_inc': (24, 25, 42)}
MUTATIONS = {
    'common_add_drop_carry': ('ot_v41_ksadd', 42, 'assign cout = g[L][W];', "assign cout = 1'b0;"),
    'common_add_flip_sum_bit0': ('ot_v41_ksadd', 42, 'assign s = (a ^ b) ^ g[L][W-1:0];',
                               "assign s = ((a ^ b) ^ g[L][W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
    'common_inc_drop_carry': ('ot_v41_inc', 42, 'assign co = t[L][W];', "assign co = 1'b0;"),
    'common_inc_flip_sum_bit0': ('ot_v41_inc', 42, 'assign y = a ^ t[L][W-1:0];',
                               "assign y = (a ^ t[L][W-1:0]) ^ {{(W-1){1'b0}}, 1'b1};"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed(path: str, commit: str) -> bytes:
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)


def module_text(source: str, module: str) -> str:
    if module not in SPECS:
        raise ValueError('outside common-prefix scope')
    matches = list(re.finditer(r'^module\s+' + re.escape(module) + r'\b.*?^endmodule\b[^\n]*', source, re.M | re.S))
    if len(matches) != 1:
        raise ValueError('expected one exact common-prefix module')
    return matches[0].group() + '\n'


def miter(module: str, width: int) -> str:
    if module not in SPECS or type(width) is not int or width not in SPECS[module]:
        raise ValueError('outside common-prefix scope')
    if module == 'ot_v41_ksadd':
        return f'''module proof(input wire [{width-1}:0] a, b, input wire cin,
  output wire [{width}:0] actual, expected, output wire equal);
  wire [{width-1}:0] s;
  wire cout;
  ot_v41_ksadd #(.W({width})) dut (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
  assign actual = {{cout, s}};
  assign expected = {{1'b0, a}} + {{1'b0, b}} + {{{{{width}{{1'b0}}}}, cin}};
  assign equal = (actual == expected);
endmodule
'''
    return f'''module proof(input wire [{width-1}:0] a, input wire inc,
  output wire [{width}:0] actual, expected, output wire equal);
  wire [{width-1}:0] y;
  wire co;
  ot_v41_inc #(.W({width})) dut (.a(a), .inc(inc), .y(y), .co(co));
  assign actual = {{co, y}};
  assign expected = {{1'b0, a}} + {{{{{width}{{1'b0}}}}, inc}};
  assign equal = (actual == expected);
endmodule
'''


def classify(returncode: int, log: str) -> str:
    if returncode == 0 and 'SAT proof finished - no model found: SUCCESS!' in log:
        return 'PASS'
    if returncode == 0 and 'SAT proof finished - model found: FAIL!' in log:
        return 'FAIL'
    return 'ERROR'


def prove_case(yosys: str, implementation: str, module: str, width: int, case_dir: Path, timeout: int = 60) -> dict:
    case_dir.mkdir()  # Refuse to overwrite any prior failure or success evidence.
    harness = miter(module, width)
    signals = 'a,b,cin,actual,expected,equal' if module == 'ot_v41_ksadd' else 'a,inc,actual,expected,equal'
    script = ('read_verilog -sv implementation.sv miter.sv\n'
              'hierarchy -check -top proof\nproc\nflatten\nopt\ncheck -assert\n'
              f'sat -prove equal 1 -show {signals} -dump_json witness.json -timeout {timeout}\n')
    with tempfile.TemporaryDirectory(prefix='dsrom-common-prefix-sat-') as scratch:
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


def authorities() -> dict:
    census_pins, data = {}, {}
    for name in ('record.json', 'census.json', 'source_pins.json'):
        path = f'{CENSUS_DIR}/{name}'
        raw = committed(path, CENSUS_COMMIT)
        data[name] = json.loads(raw)
        census_pins[path] = dict(commit=CENSUS_COMMIT, sha256=sha(raw))
    record, census, audit = data['record.json'], data['census.json'], data['source_pins.json']
    if record['source_commit'] != SOURCE_COMMIT or census['required_widths'] != {k:list(v) for k,v in SPECS.items()}:
        raise ValueError('census source or scope differs')
    manifest_path = audit['manifest_path']
    raw_manifest = committed(manifest_path, BASE_COMMIT)
    manifest = json.loads(raw_manifest)
    if (sha(raw_manifest) != audit['manifest_sha256'] or manifest['source_commit'] != SOURCE_COMMIT
            or len(manifest['source_sha256']) != 145
            or manifest['source_sha256'] != {a['path']:a['sha256'] for a in audit['audit']}):
        raise ValueError('145-source manifest binding differs')
    source = committed(SOURCE, SOURCE_COMMIT)
    if sha(source) != SOURCE_SHA or (ROOT / SOURCE).read_bytes() != source:
        raise ValueError('common-prefix bytes differ from source pin')
    consumers = {}
    for site in census['direct_sites']:
        path = site['path']
        if path not in consumers:
            raw = committed(path, SOURCE_COMMIT)
            if sha(raw) != manifest['source_sha256'][path] or (ROOT / path).read_bytes() != raw:
                raise ValueError(f'consumer bytes differ: {path}')
            consumers[path] = dict(commit=SOURCE_COMMIT, sha256=sha(raw))
        lines = committed(path, SOURCE_COMMIT).decode().splitlines()
        if lines[site['line']-1].strip() != site['source_line'].strip():
            raise ValueError('census source site differs')
    return dict(census_pins=census_pins,
                manifest_pin=dict(path=manifest_path, commit=BASE_COMMIT, sha256=sha(raw_manifest),
                                  source_commit=SOURCE_COMMIT, source_count=145,
                                  comparison='All 145 manifest hashes equal pinned census audit; no new full-manifest byte audit or elaboration.'),
                source_pin=dict(path=SOURCE, commit=SOURCE_COMMIT, sha256=sha(source)),
                consumer_source_pins=consumers, direct_sites=census['direct_sites'],
                compile_binding=record['compile_binding'])


def run(output: Path, yosys: str) -> dict:
    executable = shutil.which(yosys)
    if not executable:
        raise ValueError('Yosys executable unavailable')
    executable = str(Path(executable).resolve())
    authority = authorities()
    source = committed(SOURCE, SOURCE_COMMIT).decode()
    implementations = {module:module_text(source,module) for module in SPECS}
    version = subprocess.check_output([executable, '-V'], text=True).strip()
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for module,widths in SPECS.items():
        for width in widths:
            case = prove_case(executable,implementations[module],module,width,output / f'{module}_w{width}')
            case['expected_verdict'] = 'PASS'
            cases.append(case)
            print(module,width,case['verdict'],flush=True)
    for name,(module,width,before,after) in MUTATIONS.items():
        if implementations[module].count(before) != 1:
            raise ValueError(f'mutation target not unique: {name}')
        case = prove_case(executable,implementations[module].replace(before,after),module,width,output/name)
        case.update(mutation=name,before=before,after=after,expected_verdict='FAIL')
        cases.append(case)
        print(name,case['verdict'],flush=True)
    artifacts = {str(path.relative_to(output)):dict(sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
                 for path in sorted(output.rglob('*')) if path.is_file()}
    result = dict(schema='DSROM_common_prefix_combinational_SAT_prerequisite_r1',
                  verdict='PASS_PREREQUISITE_ONLY' if all(c['verdict']==c['expected_verdict'] for c in cases) else 'FAIL',
                  **authority, exact_modules={m:dict(text=s,sha256=sha(s.encode())) for m,s in implementations.items()},
                  proof_tool_sha256=sha(Path(__file__).read_bytes()),
                  proof_tests_sha256=sha((ROOT/'tests/test_dsrom_common_prefix_sat.py').read_bytes()),
                  tools=dict(yosys=version,yosys_executable=executable,
                             yosys_executable_sha256=sha(Path(executable).read_bytes()),python=sys.version),
                  assumptions=[],cases=cases,artifacts=artifacts,
                  scope='Seven unrestricted 2-state combinational proofs of common-prefix full sum and carry only; no sequential qualification or stand-in use.',
                  preserved_hdc_proof_commits=['29ace40b6f563c980c0b42b7d6eba32c91a2fc93','b9ef68334b00ea9609cda40213484c31553d7411'],
                  prior_hdc_proofs_repeated=False,
                  remaining_gates=['Sequential fadd CUT379:8 cycles; bmul2:5 cycles; bterm2_w10 TW17:11 cycles',
                                   'Reset/valid/error/result/tag/cycle equivalence including occupied pipeline resets',
                                   'Bounded wrapper integration and future full-die gate before source substitution'],
                  standins_installed=False,source_selection=False,hardware_qualification=False,
                  timing_claim=False,rate_claim=False,adoption=False)
    with (output/'proof.json').open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--yosys',default='yosys')
    args = parser.parse_args()
    record = run(args.output,args.yosys)
    print(record['verdict'])
    raise SystemExit(0 if record['verdict']=='PASS_PREREQUISITE_ONLY' else 1)
