#!/usr/bin/env python3
"""Run the H9b previous-ready KR bridge exactness/reset/occupancy gate or mutant."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
D = 'rtl/hbm_accel/loader/service_native/'
SOURCES = [D+'ot_hbm_svc_kr_ready_bridge.sv', D+'ot_hbm_svc_ring_h9b.sv',
 'rtl/test/hbm_accel/svg_rel/tb_hbm_kr_ready_bridge.sv']
FAIL_REGEX = r'KR_BRIDGE_DATA_MISMATCH'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--mutant', action='store_true')
    ap.add_argument('--source-revision', default='8389e864f')
    a = ap.parse_args()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    pins = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in SOURCES}
    driver = str(Path(__file__).relative_to(ROOT))
    pins[driver] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    tag = 'mutant' if a.mutant else 'positive'
    digest = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]
    obj = work / f'obj_{tag}_{digest}'
    verilator = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    version = subprocess.check_output([verilator, '--version'], text=True).strip()
    if not re.search(r'Verilator 5\.050\b', version):
        raise SystemExit('requires the closure fleet Verilator 5.050: ' + version)
    binary = obj / 'Vtb_hbm_kr_ready_bridge'
    if not binary.exists():
        cmd = [verilator, '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb_hbm_kr_ready_bridge',
               '-O2', '--Mdir', str(obj), '-j', '8', f'-GMUT={int(a.mutant)}']
        cmd += [str(ROOT / f) for f in SOURCES]
        build = subprocess.run(cmd, capture_output=True, text=True)
        (work / f'{tag}_build.log').write_text(build.stdout + build.stderr)
        if build.returncode:
            raise SystemExit('build failed; see ' + str(work / f'{tag}_build.log'))
    run = subprocess.run([str(binary)], capture_output=True, text=True, cwd=work)
    log = run.stdout + run.stderr
    log_name = 'txn_mutant_fail.log' if a.mutant else 'txn_positive.log'
    (work / log_name).write_text(log)
    passed = (run.returncode != 0 and bool(re.search(FAIL_REGEX, log))) if a.mutant else (
        run.returncode == 0 and 'KR_BRIDGE_PASS' in log)
    result = dict(schema='opentallas.hbm_kr_ready_bridge.v1', verdict='PASS' if passed else 'FAIL',
                  mutant=a.mutant, mutant_parameter='MUT', fail_regex=FAIL_REGEX,
                  returncode=run.returncode, source_base_revision=a.source_revision,
                  source_sha256=pins, verilator=version, log=log_name,
                  summary=re.findall(r'^KR_BRIDGE_(?:PASS|FAIL).*$', log, re.M))
    (work / f'{tag}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['verdict', 'mutant', 'returncode', 'log', 'summary']}))
    if not passed:
        print(log[-5000:])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
