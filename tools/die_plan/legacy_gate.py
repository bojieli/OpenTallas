"""Fail-closed LEC and extracted-clock insertion gates for modern legacy kits.

Invoked inside the kit's admitted ORFS container. Old receipts are retained;
only a newly produced EQUIVALENT or TT+FF global-routing PASS can advance.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def retain(path):
    if path.exists():
        path.rename(path.with_name(path.name + f'.previous.{time.time_ns()}'))


def load(path):
    return json.loads(path.read_text())


def run(kit, stage, netlist=None, execute=subprocess.run):
    kit = Path(kit)
    marker = kit / ('FAIL_PREFLOOR' if stage == 'lec' else 'FAIL_POSTCTS')
    try:
        if stage == 'lec':
            netlist = Path(netlist)
            tool = kit / 'lec.py'
            if not tool.is_file() or not netlist.is_file():
                raise ValueError('missing LEC tool or synthesized netlist')
            out = kit / 'lec'
            out.mkdir(exist_ok=True)
            receipt = out / 'lec.json'
            retain(receipt)
            log = kit / 'lec_run.log'
            retain(log)
            with log.open('w') as stream:
                result = execute([sys.executable, '-I', str(tool), str(kit), '--netlist', str(netlist),
                                  '--out', str(out)], stdout=stream, stderr=subprocess.STDOUT)
            verdict = load(receipt).get('verdict')
            if result.returncode != 0 or verdict != 'EQUIVALENT':
                raise ValueError(f'LEC {verdict}, exit {result.returncode}')
            print('OT_LEGACY_GATE LEC EQUIVALENT')
            return 0
        if stage != 'grt':
            raise ValueError(f'unknown gate {stage}')
        candidates = list((kit / 'run/results/asap7').glob('*/base/5_1_grt.odb'))
        if len(candidates) != 1:
            raise ValueError('expected exactly one real 5_1_grt.odb')
        config = (kit / 'config.mk').read_text()
        settings = {}
        for key in ('OT_VCLK_TT', 'OT_VCLK_FF', 'LAYER_PARASITICS_FILE'):
            matches = re.findall(r'^export\s+' + key + r'\s*=\s*(\S+)\s*$', config, re.M)
            if len(matches) != 1:
                raise ValueError(f'missing or ambiguous {key}')
            settings[key] = matches[0]
        if any(not math.isfinite(float(settings[k])) or float(settings[k]) <= 0
               for k in ('OT_VCLK_TT', 'OT_VCLK_FF')):
            raise ValueError('nonpositive corner insertion bound')
        rc_path = Path(settings['LAYER_PARASITICS_FILE'])
        # /work is the canonical mounted kit path in production; tests may use
        # a temporary kit directory with the same generated config contents.
        rc_file = kit / rc_path.relative_to('/work') if rc_path.is_relative_to('/work') else rc_path
        if not rc_file.is_file():
            raise ValueError('missing configured calibrated RC file')
        if not (kit / 'postcts_gate.tcl').is_file():
            raise ValueError('missing postcts gate')
        for corner in ('TT', 'FF'):
            receipt = kit / f'postcts_gate_{corner.lower()}.json'
            log = kit / f'postcts_gate_{corner}.log'
            retain(receipt)
            retain(log)
            env = dict(os.environ, **settings, OT_POSTCTS_GRT='1', OT_CORNER=corner,
                       ODB=str(candidates[0]), OT_POSTCTS_TOL='20.0')
            with log.open('w') as stream:
                result = execute(['openroad', '-exit', str(kit / 'postcts_gate.tcl')],
                                 env=env, stdout=stream, stderr=subprocess.STDOUT)
            d = load(receipt)
            numeric = [float(d[k]) for k in ('bound_ps', 'dev_ps', 'tol_ps', 'pinreg_mean_ps')]
            if (not all(math.isfinite(v) for v in numeric) or not 0 <= d['dev_ps'] <= d['tol_ps'] <= 20.0
                    or abs(d['pinreg_mean_ps'] - d['bound_ps']) > d['tol_ps']
                    or result.returncode != 0 or d.get('verdict') != 'PASS' or d.get('corner') != corner
                    or d.get('parasitics') != 'global_routing' or d.get('pinreg_n', 0) <= 0
                    or abs(float(d['bound_ps']) - float(settings[f'OT_VCLK_{corner}'])) > 1e-6
                    or float(d['dev_ps']) > float(d['tol_ps'])):
                raise ValueError(f'{corner} global-routing insertion gate failed: {d.get("verdict")} exit {result.returncode}')
        print('OT_LEGACY_GATE GRT TT/FF PASS')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        with marker.open('a') as stream:
            stream.write(f'legacy {stage} gate: {error}\n')
        print(f'OT_LEGACY_GATE {stage} FAIL: {error}', file=sys.stderr)
        return 5 if stage == 'lec' else 6


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit')
    p.add_argument('stage', choices=('lec', 'grt'))
    p.add_argument('--netlist')
    a = p.parse_args()
    return run(a.kit, a.stage, a.netlist)


if __name__ == '__main__':
    raise SystemExit(main())
