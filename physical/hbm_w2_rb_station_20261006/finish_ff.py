#!/usr/bin/env python3
"""Evaluate a completed W2 route, then repair FF hold with pinned Wegener helpers.

Original route/failed evidence are read-only. Every evaluation gets a new tree.
SS must meet +15 ps and DRC=0 before ECO. Final acceptance remeasures insertion
on the ECO database, independently of the helper's fixed input SDC verdict.
Run through the host admission guard (8 threads; same full-size station).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def evaluate(base, station_sdc, out):
    case = out/'work/orfs'
    dst = case/'results/asap7/w2/base'
    dst.mkdir(parents=True)
    for name in ('6_final.odb', '6_final.spef'):
        shutil.copyfile(base/name, dst/name)
    shutil.copyfile(station_sdc, case/'station.sdc')
    (case/'config.mk').write_text('# Isolated signoff copy; never used for P&R.\n')
    with (out/'signoff.log').open('w') as log:
        rc = subprocess.run([sys.executable, str(HERE/'signoff.py'), '--run', str(out)],
                            stdout=log, stderr=subprocess.STDOUT).returncode
    result = json.loads((out/'signoff.json').read_text())
    result['process_exit'] = rc
    return result, case/'signoff.sdc'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--route', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    route, out = a.route.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='STARTED', route=str(route), acceptance_ps=dict(SS=15, FF=15),
                  ECO_SESSION='ff', original_route_modified=False)
    try:
        base = next(route.glob('work/orfs/results/asap7/*/base'))
        for n in ('5_2_route.odb', '6_final.odb', '6_final.spef'):
            record.setdefault('input_sha256', {})[n] = sha(base/n)
        record['input_sha256']['station.sdc'] = sha(route/'station.sdc')
        drc_log = next(route.glob('work/orfs/logs/asap7/*/base/5_2_route.json'))
        record['DRC'] = json.loads(drc_log.read_text()).get('detailedroute__route__drc_errors')
        pre, strict_sdc = evaluate(base, route/'station.sdc', out/'pre')
        record['pre'] = pre
        if record['DRC'] != 0 or not pre['accept']['SS_ok']:
            record['status'] = 'NEEDS_STRUCTURAL_SETUP_OR_DRC_FIX'
            return 1
        if pre['accept']['FF_ok'] and pre['process_exit'] == 0:
            record['status'] = 'PASS_WITHOUT_ECO'
            return 0
        # Keep the exact measured-insertion signoff contract for both helper sessions.
        ob = out/'strict_input'
        ob.mkdir()
        shutil.copyfile(strict_sdc, ob/'6_final.sdc')
        shutil.copyfile(base/'6_final.spef', ob/'6_final.spef')
        helper = HERE/'ff_eco'
        pins = json.loads((helper/'source.json').read_text())
        for name, digest in pins['sha256'].items():
            if sha(helper/name) != digest:
                raise ValueError(f'helper drift: {name}')
        record['helper'] = pins
        env = dict(os.environ, ECO_SESSION='ff', ACC_SS='15', ACC_FF='15', THREADS='8', PASSES='1')
        env.pop('WINDOW_ONLY', None)
        cmd = ['bash', str(helper/'hold_eco.sh'), str(base), str(ob), str(out/'eco'),
               'ot_hbm_native_frame_station_rb_NO3_SAFE']
        with (out/'eco_driver.log').open('w') as log:
            rc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        record['eco_exit'] = rc
        if rc:
            record['status'] = 'FF_ECO_FAILED_PRESERVED'
            return 1
        eco = json.loads((out/'eco/result.json').read_text())
        record['eco'] = eco
        if eco.get('session') != 'ff':
            raise ValueError('expected FF-only repair session')
        final_base = next((out/'eco/orfs/results/asap7').glob('*/base')).resolve()
        final, _ = evaluate(final_base, route/'station.sdc', out/'final')
        record['final'] = final
        ok = (eco.get('drc') == 0 and not eco.get('errors') and final['process_exit'] == 0
              and final['accept']['SS_ok'] and final['accept']['FF_ok'])
        record['status'] = 'PASS_STRICT_REMEASURED_SS_FF' if ok else 'FAIL_STRICT_REMEASURED_SS_FF'
        return 0 if ok else 1
    except Exception as exc:
        record['status'] = 'FAILED_EVIDENCE_PRESERVED'
        record['error'] = repr(exc)
        raise
    finally:
        (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps({'status': record['status'], 'record': str(out/'result.json')}))


if __name__ == '__main__':
    raise SystemExit(main())
