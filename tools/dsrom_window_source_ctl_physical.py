"""Margin-first route of the WINDOW source control leaf (ot_dsrom_window_source_ctl MARGIN=1).

Route SDC at 770 ps (60 ps setup / 25 ps hold uncertainty), sign-off at 833.333 ps on the routed
database (SS setup, FF hold).  Accept SS >= +40 ps, FF >= +15 ps, DRC 0.  No IO waiver: every
port carries 20 % of the period as external delay (154 ps at the route period).  The leaf excludes
the staging array, the row merge and the HBM wmux (separate neighbours).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_source_ctl.sv',
    'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_writer_pipeline.sv',
    'rtl/dsrom_sys/s81_window_la/ot_dsrom_window_stream_la_s81.sv',
    'rtl/chip/ot_chip_v41x_window_stage4.sv',
    'rtl/chip/ot_chip_v41x_window_row_codec.sv']
DIE = 480.0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    out = a.out.resolve()
    (out / 'work/orfs/tmp').mkdir(parents=True, exist_ok=True)
    cmd = ['python3', 'tools/run_abi3_physical.py', '--view', 'asap7', '--top', 'ot_dsrom_window_source_ctl',
           *[x for s in SOURCES for x in ('--source', s)],
           '--param', 'MARGIN=1', '--param', 'REFILL_OWNER_SAFE=1', '--param', 'REFILL_CREDITS=8',
           '--param', 'LA_ISSUE_PC=1',
           '--clock-period-ns', '0.770', '--clock-uncertainty-ns', '0.060',
           '--clock-uncertainty-hold-ns', '0.025', '--orfs-corner', 'WC', '--hold-corners', 'WC,BC',
           '--io-delay-fraction', '0.2', '--stages', 'pnr', '--hold-margin-ns', '0.020',
           '--max-fanout', '32',
           '--die-area', '0', '0', str(DIE), str(DIE), '--core-area', '5', '5', str(DIE - 5), str(DIE - 5),
           '--place-density', '0.5', '--orfs-var', 'ADDER_MAP_FILE=',
           '--orfs-var', 'IO_PLACER_H=M4 M6 M8', '--orfs-var', 'IO_PLACER_V=M5 M7 M9',
           '--orfs-var', 'TMPDIR=/work/tmp', '--routing-layers', 'M2', 'M9',
           '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
           '--purpose', 'characterization', '--nickname-tag', 'window_source_ctl_margin_r1',
           '--keep-workdir', str(out / 'work'), '--output', str(out / 'physical.json')]
    sha = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    rec = dict(command=cmd, source_sha256={s: sha(s) for s in SOURCES},
               driver_sha256=sha('tools/run_abi3_physical.py'),
               route_period_ps=770, signoff_period_ps=1000 / 1.2, setup_uncertainty_ps=60,
               hold_uncertainty_ps=25, accept=dict(SS_setup_ps=40, FF_hold_ps=15, DRC=0),
               IO_waiver=False, io_delay_fraction=0.2,
               IO_pin_layers={'horizontal': ['M4', 'M6', 'M8'], 'vertical': ['M5', 'M7', 'M9']},
               die_um=[DIE, DIE],
               pin_budget='~13.6k signal ports; retained 1550 um probe measured 24.45 legal positions per um '
                          'of perimeter on these layers -> ~46.9k positions at 480 um, ~29 % use',
               model='tools/uarch_model.py dsrom_window_source_ctl_margin_model',
               excluded_neighbours=['ot_dsrom_window_stage_pipeline (+68 columns)',
                                    'ot_dsrom_window_row_merge_pipeline', 'ot_dsrom_hbm_wmux'],
               parent_context_proof=False, adoption=False)
    (out / 'recipe.json').write_text(json.dumps(rec, indent=2) + '\n')
    if a.execute:
        env = dict(os.environ, OT_ORFS_NUM_CORES='16')
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        (out / 'terminal.exit').write_text(str(r.returncode) + '\n')
        raise SystemExit(r.returncode)


if __name__ == '__main__':
    main()
