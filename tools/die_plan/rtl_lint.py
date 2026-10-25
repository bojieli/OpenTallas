#!/usr/bin/env python3
"""Fail before synthesis on implicit nets, unresolved hierarchy or undriven RTL.
Runs inside the kit container, using one blackbox liberty view per macro.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def config(kit):
    values = {}
    text = (kit / 'config.mk').read_text().replace('\\\n', ' ')
    for key, value in re.findall(r'^\s*(?:override\s+)?export\s+(\w+)\s*[:?]?=\s*(.*?)\s*$', text, re.M):
        values[key] = value.split()
    return values


def script(kit, mount='/work'):
    cfg = config(kit)
    top = cfg.get('DESIGN_NAME', [])
    sources = cfg.get('VERILOG_FILES', [])
    if len(top) != 1 or not sources:
        raise ValueError('config needs one DESIGN_NAME and nonempty VERILOG_FILES')
    libs, seen = [], set()
    for p in sorted((kit / 'macros').glob('*.lib*'), key=lambda p: ('_tt.lib' not in p.name, p.name)):
        key = re.sub(r'_(tt|ff|ss)\.lib(?:\.gz)?$|\.lib(?:\.gz)?$', '', p.name)
        if key not in seen:
            seen.add(key)
            libs.append(f'read_liberty -lib -ignore_miss_func {mount}/macros/{p.name}')
    defines = ['-DSYNTHESIS'] + [v if v.startswith('-D') else '-D'+v for v in cfg.get('VERILOG_DEFINES', [])]
    includes = ['-I'+v for v in cfg.get('VERILOG_INCLUDE_DIRS', []) + cfg.get('SYNTH_INCLUDE_DIRS', [])]
    return '\n'.join(libs + ['verilog_defines ' + ' '.join(dict.fromkeys(defines))] +
                     ['read_verilog -sv -defer -noautowire ' + ' '.join(includes + [s]) for s in sources] +
                     [f'hierarchy -check -top {top[0]}', 'proc', 'check -assert']) + '\n'


def run(kit, yosys='yosys'):
    out = kit / 'rtl_lint.json'
    try:
        ys = kit / 'rtl_lint.ys'
        ys.write_text(script(kit))
        result = subprocess.run([yosys, '-q', '-s', str(ys)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = result.stdout
        (kit / 'rtl_lint.log').write_text(log)
        record = dict(verdict='PASS' if result.returncode == 0 else 'FAIL', rc=result.returncode,
                      errors=re.findall(r'^ERROR:.*$', log, re.M), command=[yosys, '-q', '-s', str(ys)])
    except (OSError, ValueError) as error:
        record = dict(verdict='NOT RUN', rc=2, errors=[str(error)])
    out.write_text(json.dumps(record, indent=1) + '\n')
    print('RTL_LINT', record['verdict'], 'errors', len(record['errors']))
    return 0 if record['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kit', type=Path)
    parser.add_argument('--yosys', default='yosys')
    args = parser.parse_args()
    raise SystemExit(run(args.kit.resolve(), args.yosys))
