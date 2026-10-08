#!/usr/bin/env python3
"""Prepare the actual reduced SU vehicle before admitting its costly RTL build.

Run from an extracted, inventory-checked candidate archive, on the execution
host using its configured Python environment and existing pinned checkpoint.
This runs golden prefill and VC.vehicle_records, not just module imports.
It performs no RTL compilation and provides no RTL exactness verdict. The
vehicle preparation itself allocates model/state memory, so run it under the
host's measured admission guard. Use a fresh --out path to retain failures.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from source_archive import check_runtime


def prepare(inventory):
    for key, value in inventory['runtime_environment'].items():
        if key != 'OPENTALLAS_BUILD':
            raise ValueError(f'Unsupported runtime environment key: {key}')
        os.environ[key] = value
    packages = {}
    for name, expected in inventory['runtime_python_packages'].items():
        actual = importlib.metadata.version(name)
        if expected and actual != expected:
            raise ValueError(f'{name} version {actual} differs from expected {expected}')
        packages[name] = actual
    runtime = check_runtime(inventory['runtime_files'])
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'tools'))
    import hbm_su_div64 as D
    import rtl_hdc_v41x_vec_campaign as VC
    D.install()
    D.C.P['ddiv'] = 64
    D.C.apply(VC)
    # This is the campaign's own path: Model -> prompt/oracle -> golden_prefill
    # -> ISA execution -> capture of every stream operation's starting state.
    records, crom, wrom, metadata = VC.vehicle_records()
    if not records or not crom.size or not wrom.size:
        raise ValueError('Actual vehicle preparation returned empty stimulus')
    return dict(status='PREPARED_ONLY', runtime_verified=runtime,
                python_packages=packages, vehicle=metadata,
                recorded_operations=len(records), crom_words=int(crom.size),
                wrom_words=int(wrom.size), selected_ddiv=64,
                scope='Actual reduced vehicle golden preparation; no RTL compile or exactness verdict')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    # Reserve the output before performing preparation; exceptions leave an
    # explicit terminal failure receipt and propagate a nonzero exit status.
    with a.out.open('x') as output:
        try:
            record = prepare(json.loads(a.inventory.read_text()))
        except Exception as error:
            json.dump(dict(status='PREPARATION_FAILED', error_type=type(error).__name__, error=str(error)), output, indent=2)
            output.write('\n')
            raise
        json.dump(record, output, indent=2)
        output.write('\n')
    print('PREPARED_ONLY: actual SU vehicle stimulus; no RTL verdict')


if __name__ == '__main__':
    main()
