#!/usr/bin/env python3
"""Experimental MESH collector DSREP8/band-spread form; no plan adoption or P&R."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    por = ROOT / 'physical/die_plan/s81_head/plan_of_record/l48ve'
    plan = json.loads(gzip.decompress((por / 'source_plan.json.gz').read_bytes()))
    side = gzip.decompress((por / 'source_sidecar.json.gz').read_bytes())
    typ = plan['partition_types']['hd_mesh']
    typ['contents'][0]['params'].update(RBL='1', BQ='10')
    typ['clock']['landing_ring_dsrep'] = {'buses': ['coll_ia', 'coll_ib'], 'dsrep': 8}
    # Preserve the exact published census/assets while moving this private plan.
    def relocate(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith(('native_domains/', 'assets/', 'core_pins/')):
                    obj[k] = str(por / v)
                else:
                    relocate(v)
        elif isinstance(obj, list):
            for v in obj:
                relocate(v)
    relocate(plan)
    pin = out / 'source_plan.json'
    pin.write_text(json.dumps(plan, indent=1))
    sidepath = out / 'source_sidecar.json'
    sidepath.write_bytes(side)
    def run(*args):
        subprocess.run([sys.executable, '-I', *map(str, args)], check=True, env=env)
    env = dict(os.environ, OT_CONS_KIT='1', OT_CONS_UTIL='0.35',
               OT_CONS_MAX_LAYER='M6', OT_SKIP_PRECTS_METRICS='1', OT_FSM_NONE_WIRES='hunt')
    run(ROOT / 'tools/die_plan/ring_band_spread.py', pin, sidepath,
        out / 'plan.json', out / 'spread_report.json', '--types', 'hd_mesh', '--spread', '7',
        '--bisect', '--tag', 'CODEX-HEAD-MESH-1113')
    # Official generator keeps all independent contracts, lint, LEC and physical gates.
    run(ROOT / 'tools/die_plan/gen.py', 'phys', out / 'plan.json', '--out', out / 'kits',
        '--rtl-root', ROOT, '--types', 'hd_mesh', '--clock-landing', sidepath,
        '--util', '0.35', '--max-wire-um', '80', '--hold-ff-margin', '15',
        '--cland-pinslot', 'hd_mesh', '--trial')
    kit = out / 'kits/hd_mesh'
    for name in ('DO_NOT_COUNT', 'HOLD_ROUTE', 'HOLD_CTS'):
        (kit / name).write_text('Experimental collector form: inspect actual PLACE before any later stage.\n')
    (out / 'calendar.json').write_text(json.dumps({
        'compared_to': 'existing RBL1/BQ10 vA/vB', 'added_pin_cycles': 0,
        'existing_RBL_TX_pin_cycles': 1, 'RX_pin_cycles': 0,
        'adoption': 'NONE', 'release_eligible': False}, indent=2) + '\n')
    print(kit)


if __name__ == '__main__':
    main()
