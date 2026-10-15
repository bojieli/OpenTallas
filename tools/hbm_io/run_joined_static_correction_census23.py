#!/usr/bin/env python3
"""Prepare strict census of the passed PHY512/core487 joined profile.

Default prepares source bindings and Yosys script only. --run requires prior
ownership clearance and admission through ot-run. No scalar/library map here.
Caller native endpoints and their SRAM are explicitly outside this hierarchy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from fec_clock_census import census

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'rtl/hbm_accel/io_static_20261015/static_correction_census23_inputs.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(manifest):
    observed = {p: sha(ROOT / p) for p in manifest['sha256']}
    if observed != manifest['sha256']:
        changed = [p for p in observed if observed[p] != manifest['sha256'][p]]
        raise ValueError('Source differs from passed census binding: ' + ', '.join(changed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--run', action='store_true', help='Run only after ownership clearance and ot-run admission')
    parser.add_argument('--yosys', default=str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'))
    args = parser.parse_args()
    manifest = json.loads((ROOT / MANIFEST).read_text())
    verify(manifest)
    out = args.out.resolve()
    if any(ch.isspace() for ch in str(out)):
        raise ValueError('Yosys output path must not contain whitespace')
    out.mkdir(parents=True, exist_ok=False)
    tools = [Path(__file__), Path(__file__).with_name('fec_clock_census.py'), ROOT / MANIFEST]
    checker = {str(p.relative_to(ROOT)): sha(p) for p in tools}
    source = dict(manifest, checker_sha256=checker,
                  scope='ACTUAL_JOINED_PHY512_CORE487_23_ROOT_GENERIC_CENSUS_ONLY')
    (out / 'source.json').write_text(json.dumps(source, indent=2) + '\n')
    top = manifest['top']
    script = 'read_verilog -sv -D SYNTHESIS -Irtl/dsrom_sys/s81_link ' + ' '.join(manifest['sources']) + '\n'
    script += f'hierarchy -check -top {top}\nproc\nflatten\nopt\nmemory_map\nopt\ncheck -assert\nwrite_json {out}/netlist.json\nstat\n'
    (out / 'census.ys').write_text(script)
    if not args.run:
        print(json.dumps({'status': 'PREPARED_ONLY_NO_SYNTHESIS', 'top': top,
                          'independent_scalar_clocks': len(manifest['clocks']),
                          'out': str(out)}))
        return 0
    start = time.monotonic()
    with (out / 'yosys.log').open('w') as log:
        result = subprocess.run([args.yosys, '-s', str(out / 'census.ys')],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - start
    verify(manifest)
    if checker != {str(p.relative_to(ROOT)): sha(p) for p in tools}:
        raise ValueError('Census checker changed during synthesis')
    if result.returncode:
        (out / 'failure.json').write_text(json.dumps({'yosys_exit': result.returncode,
                                                     'elapsed_seconds': elapsed}, indent=2) + '\n')
        return result.returncode
    count = census(json.loads((out / 'netlist.json').read_text()), top, manifest['clocks'])
    count.update(source)
    count.update(elapsed_seconds=elapsed, netlist_sha256=sha(out / 'netlist.json'),
                 yosys_log_sha256=sha(out / 'yosys.log'), physical_qualified=False)
    count['open'] = ['Scalar/library mapped inventory and actual leaf partition',
                     'Actual pin capacity, CTS, compensated clock phases and CDC qualification',
                     'TT setup / FF hold / DRC closure and full-system native schedule']
    (out / 'receipt.json').write_text(json.dumps(count, indent=2) + '\n')
    print(json.dumps({k: count[k] for k in ('total_flop_bits', 'maximum_root_bits',
                                           'measured_cts_exception_required')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
