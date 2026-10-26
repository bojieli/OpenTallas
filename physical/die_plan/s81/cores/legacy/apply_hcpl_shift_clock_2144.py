#!/usr/bin/env python3
"""Apply the measured, opt-in HCPL clock recipe to a freshly generated repo kit.

Generate with gen_core_kit_legacy.py --module ot_dsrom_su_hcpost_lane_pr first.
No old runtime/netlist/view is imported, and no route entry point is enabled.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def apply(kit):
    kit = Path(kit).resolve()
    cfg = kit / 'config.mk'
    text = cfg.read_text()
    nickname = re.search(r'^export DESIGN_NICKNAME = (\S+)$', text, re.M)
    if not nickname or not re.search(r'^export DESIGN_NAME = ot_dsrom_su_hcpost_lane_pr$', text, re.M):
        raise ValueError('requires the canonical HCPL module kit')
    for corner, expected in [('TT', 250.0), ('FF', 202.5)]:
        found = re.search(rf'^export OT_VCLK_{corner} = (\S+)$', text, re.M)
        if not found or float(found[1]) != expected:
            raise ValueError(f'{corner}: clock contract changed; qualify a new recipe')
    if list((kit / 'run').glob('results/asap7/*/base/4*')) or (kit / 'run_original.sh').exists():
        raise ValueError('apply only once to a fresh kit before CTS')
    copies = {
        HERE / 'hcpl_shift_clock_2144.tcl': 'hcpl_shift_clock_2144.tcl',
        HERE / 'hcpl_shift_audit_2144.tcl': 'audit_shift_clock.tcl',
        HERE / 'hcpl_shift_phase_2144.sh': 'run_shift_phase.sh',
        REPO / 'tools/die_plan/leaf_affinity.tcl': 'leaf_affinity.tcl',
        REPO / 'tools/die_plan/repair_ff.tcl': 'repair_ff.tcl',
    }
    for src in copies:
        if not src.is_file():
            raise ValueError(f'missing repo source {src.relative_to(REPO)}')
    shutil.copyfile(kit / 'run_kit.sh', kit / 'run_original.sh')
    for src, name in copies.items():
        shutil.copyfile(src, kit / name)
    (kit / 'shift_pre_cts.tcl').write_text('source /work/hold_budget.tcl\nsource /work/hcpl_shift_clock_2144.tcl\n')
    (kit / 'shift_ff_vclk.sdc').write_text('set_clock_latency -source 202.5 [get_clocks vclk]\n')
    # The existing source recipe's DRV margins are retained; only mixed-scene hold is removed.
    drv = (kit / 'post_grt_drv.tcl').read_text()
    drv = '\n'.join(line for line in drv.splitlines() if not line.lstrip().startswith('repair_timing')) + '\n'
    (kit / 'shift_post_grt_drv.tcl').write_text(drv)
    (kit / 'shift_post_grt.tcl').write_text('source /work/shift_post_grt_drv.tcl\nsource /work/grt_post.tcl\n')
    text += ('\n# Opt-in bounded delay-chain clock groups; isolated fresh FF repair.\n'
             'export PRE_CTS_TCL = /work/shift_pre_cts.tcl\n'
             'export POST_GLOBAL_ROUTE_TCL = /work/shift_post_grt.tcl\n'
             'export SKIP_INCREMENTAL_REPAIR = 1\n')
    cfg.write_text(text)
    (kit / 'run_kit.sh').write_text('''#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd)
case "${2:-finish}" in
 place|cts|grt) exec bash "$K/run_shift_phase.sh" "${2}" "${3:-16}" "${4:-8}" ;;
 ff) exec bash "$K/run_shift_phase.sh" ff "${3:-16}" "${4:-8}" ;;
 *) echo "HCPL_SHIFT no route/finish before current die/flow review" >&2; exit 3 ;;
esac
''')
    (kit / 'shift_timing_guard.py').write_text('''import re, sys
if len(sys.argv) != 3: raise SystemExit('requires native TT and FF logs')
for path, corner in zip(sys.argv[1:], ('TT', 'FF')):
    s = open(path).read()
    m = re.search(r'HCPL_SHIFT TIMING (TT|FF) setup ([-\\d.]+) nsetup (\\d+) hold ([-\\d.]+) nhold (\\d+)', s)
    if not m or m[1] != corner:
        raise SystemExit('MISSING_GATE ' + path)
    if (corner == 'TT' and (float(m[2]) < 0 or int(m[3]))) or (corner == 'FF' and (float(m[4]) < 0 or int(m[5]))):
        raise SystemExit('FAILED_GATE ' + m[0])
    print('SHIFT_TIMING_PASS ' + m[0])
''')
    receipt = {'recipe': 'hcpl_shift_clock_2144', 'added_public_cycles': 0, 'clock_roots': 32,
               'route_enabled': False, 'inputs': {str(src.relative_to(REPO)): hashlib.sha256(src.read_bytes()).hexdigest() for src in copies}}
    (kit / 'shift_recipe.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kit', required=True)
    print(json.dumps(apply(ap.parse_args().kit), indent=2))
