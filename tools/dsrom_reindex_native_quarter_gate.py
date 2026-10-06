#!/usr/bin/env python3
"""Build one frozen fullshape native quarter, then one seed plus negative controls.

No flat64 build, scorer stand-in, synthesis, constraint change or parent credit.
Caller admits the measured peak with the host's unchanged guard. This runner
checks actual CPU/RAM/disk again after admission before starting the frontend.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RTL = [
    'rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_native_quarter.sv',
    'rtl/dsrom_sys/reindex_parent/tb_dsrom_reindex_native_quarter.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv',
    'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
    'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv',
    'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
    'rtl/proto/ot_fp32_add_rne_pipe.sv',
]
FIXTURE = ROOT / 'results/rtl/dsrom_reindex_parent_20261005/native_quarter_runtime_prepared'
FROZEN_SCORER = '44c844d08bb11dbf5ed89f810c7f5f80d7db8208dbab90d4e658f1ee2451abbe'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def capacity(path):
    def cpu():
        a = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
        return sum(a[:8]), a[3] + a[4]
    before = cpu()
    time.sleep(5)
    after = cpu()
    memory = int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines()
                      if v.startswith('MemAvailable:'))) * 1024
    cores = os.cpu_count()
    return dict(load1=os.getloadavg()[0], cores=cores,
                idle_cores=cores * (after[1] - before[1]) / (after[0] - before[0]),
                available_RAM_GiB=memory / 2**30,
                available_disk_GiB=shutil.disk_usage(path).free / 2**30,
                epoch=time.time())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--expected-peak-gib', type=int, default=96)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    record = dict(scope='One unchanged native NS4/NK4/IW20 quarter, not fullparent',
                  seed=1062026, workers=16, expected_peak_GiB=a.expected_peak_gib,
                  source_sha256={f: sha(ROOT / f) for f in RTL},
                  fixture_sha256={f: sha(FIXTURE / f) for f in ['query.mem', 'keys.mem', 'expected.mem']},
                  parent_qualified=False, physical_qualified=False, runs=[])
    prepared = json.loads((FIXTURE / 'fixture.json').read_text())
    assert record['fixture_sha256'] == prepared['fixture_sha256']
    assert record['source_sha256']['rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv'] == FROZEN_SCORER
    for path in RTL[:2]:
        assert record['source_sha256'][path] == prepared['source_sha256'][path]
    def save():
        (a.out / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    record['post_admission_capacity'] = c = capacity(a.out)
    save()
    if c['load1'] >= c['cores'] or c['idle_cores'] < 16 or c['available_RAM_GiB'] < a.expected_peak_gib + 100 or c['available_disk_GiB'] < 30:
        record['verdict'] = 'CAPACITY_REFUSAL_NO_FRONTEND'
        save()
        return 3
    obj = a.out / 'obj'
    cmd = [os.environ.get('VERILATOR', 'verilator'), '--binary', '--timing', '-j', '16',
           '-O2', '--output-split', '20000', '--output-split-cfuncs', '500',
           '--x-assign', 'unique', '--x-initial', 'unique', '-Wno-fatal',
           '--top-module', 'tb_dsrom_reindex_native_quarter', '--Mdir', str(obj),
           *[str(ROOT / f) for f in RTL]]
    record['build_argv'] = cmd
    record['verilator_version'] = subprocess.check_output([cmd[0], '--version'], text=True).strip()
    save()
    with (a.out / 'build.log').open('x') as log:
        record['build_exit'] = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    save()
    if record['build_exit']:
        record['verdict'] = 'BUILD_FAIL_PRESERVED'
        save()
        return 1
    exe = obj / 'Vtb_dsrom_reindex_native_quarter'
    record['executable_sha256'] = sha(exe)
    for name, options, expected in [('golden', [], 'PASS_KC8_NATIVE_QUARTER'),
                                    ('negative_score', ['+NEGATIVE_SCORE=1'], 'golden mismatch'),
                                    ('negative_ids', ['+NEGATIVE_IDS=1'], 'index not consecutive')]:
        cmd = [str(exe), '+verilator+seed+1062026', f'+FIXTURE={FIXTURE}', *options]
        with (a.out / (name + '.log')).open('x') as log:
            rc = subprocess.run(cmd, cwd=a.out, stdout=log, stderr=subprocess.STDOUT).returncode
        text = (a.out / (name + '.log')).read_text()
        passed = expected in text and ((rc == 0) if name == 'golden' else (rc != 0))
        record['runs'].append(dict(name=name, argv=cmd, exit_code=rc, pass_=passed))
        save()
        print(name, rc, passed, flush=True)
        if not passed:
            record['verdict'] = 'NATIVE_QUARTER_FAIL_PRESERVED'
            save()
            return 1
        if name == 'golden':
            record['numerical_terminal'] = re.search(r'PASS_KC8_NATIVE_QUARTER[^\n]+', text).group(0)
    record['verdict'] = 'NATIVE_QUARTER_PASS'
    record['unknown_payload_coverage'] = 'Verilator unique two-state substitutions in invalid slots; not four-state X propagation qualification'
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
