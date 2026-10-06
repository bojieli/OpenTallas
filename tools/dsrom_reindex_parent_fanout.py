#!/usr/bin/env python3
"""Wait for the owned mapped checkpoint, then admit one distinct full P&R.

Run one controller per CTS variant. No synthesis duplication or live-job edits.
The existing host guard and five-second CPU/RAM/disk checks stay unchanged.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

from dsrom_reindex_parent_physical import CTS_VARIANTS, ROOT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--variant', choices=CTS_VARIANTS, required=True)
    a = p.parse_args()
    d = a.scratch.resolve()
    name = 'route_r9_cts_' + a.variant
    launch = d / (name + '.launch.json')
    # Exclusive creation prevents a second controller for this same variant.
    with launch.open('x') as f:
        json.dump(dict(source_root=str(ROOT), variant=a.variant,
                       dependency=str(d / 'route_r9'), workers=16,
                       reservation_GiB=40, parent_qualified=False), f)
    base = d / 'route_r9/work/orfs/results/asap7/opentallas_ot_dsrom_reindex_parent_physctx_asap7_reindex_parent/base'
    while not ((base / '1_synth.odb').is_file() and (base / '1_2_yosys.v').is_file()):
        if (d / 'route_r9.launch.exit').exists():
            (d / (name + '.dependency_error.json')).write_text(json.dumps(
                dict(reason='R9 returned without completed mapped checkpoint',
                     route_exit=(d / 'route_r9.launch.exit').read_text().strip(),
                     duplicate_synthesis_launched=False)) + '\n')
            raise SystemExit(1)
        time.sleep(15)
    headroom = d / 'route-headroom-5s.py'
    while subprocess.run(['python3', str(headroom), name + '_pre']).returncode:
        time.sleep(15)
    # Check actual retained inventory in addition to the existing guard's floor.
    inventory = int(subprocess.check_output(['du', '-sb', str(d / 'route_r9/work')], text=True).split()[0])
    pre = json.loads((d / (name + '_pre.json')).read_text())
    if pre['available_disk_GiB'] * 2**30 < 3 * inventory:
        raise SystemExit('Insufficient disk against actual retained R9 inventory')
    command = ['bash', '-c',
        'source ~/.opentallas-env; python3 "$1/route-headroom-5s.py" "$2" && '
        'python3 "$3/tools/dsrom_reindex_parent_physical.py" --out "$1/$4" '
        '--exact "$1/gather_r8/gather.json" --mapped-route "$1/route_r9" --cts-variant "$5"',
        'kc8-fanout', str(d), name + '_post', str(ROOT), name, a.variant]
    with (d / (name + '.launch.log')).open('x') as log:
        result = subprocess.run(['/srv/opentallas-scratch/admit.sh', '40', '--', *command],
                                stdout=log, stderr=subprocess.STDOUT)
    (d / (name + '.launch.exit')).write_text(str(result.returncode) + '\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
