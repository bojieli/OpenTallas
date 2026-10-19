#!/usr/bin/env python3
"""Run the portable 6000-request H9b/BW transaction gate or identity mutant."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
D = 'rtl/hbm_accel/loader/service_native/'
SOURCES = [
    D + 'tb_hbm_pc_bw_safe_txn.sv',
    D + 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv',
    D + 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv',
    D + 'ot_hbm_svc_ring_h9b.sv',
    D + 'ot_hbm_svc_ring_bw_safe.sv',
    D + 'ot_hbm_svc_pin_skid2_h9.sv',
    D + 'ot_hbm_svc_pin_skid2_bw_safe.sv',
    'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv',
    'rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_safe.sv',
    'rtl/lib/ot_rst_relay.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
]
FAIL_REGEX = r'BW_SAFE_TXN_BEAT_MISMATCH'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--mutant', action='store_true')
    ap.add_argument('--source-revision', default='a9604c68e')
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
    binary = obj / 'Vtb'
    if not binary.exists():
        cmd = [verilator, '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb',
               '-O2', '--Mdir', str(obj), '-j', '8', f'-GMUT_ID_TAG={int(a.mutant)}']
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
        run.returncode == 0 and 'BW_SAFE_TXN PASS' in log)
    result = dict(schema='opentallas.hbm_pc_bw_safe_txn.v1', verdict='PASS' if passed else 'FAIL',
                  data_equivalence_pass='BW_SAFE_TXN_DATA_PASS' in log,
                  mutant=a.mutant, mutant_parameter='BW_MUT_ID_TAG', fail_regex=FAIL_REGEX,
                  returncode=run.returncode, source_base_revision=a.source_revision,
                  source_sha256=pins, verilator=version, log=log_name,
                  summary=re.findall(r'^BW_SAFE_TXN (?:PASS|FAIL).*$', log, re.M))
    (work / f'{tag}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['verdict', 'mutant', 'returncode', 'log', 'summary']}))
    if not passed:
        print(log[-5000:])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
