#!/usr/bin/env python3
"""Route a complete 32-row WINDOW column at its existing parent boundaries."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--width', type=int, choices=(128, 256), required=True)
    p.add_argument('--util', type=int, choices=(55, 60), default=55)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cmd = ['python3', 'tools/run_abi3_physical.py', '--view', 'asap7',
           '--top', 'ot_dsrom_window_column', '--param', f'WIDTH={a.width}',
           '--source', 'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_stage_pipeline.sv',
           '--clock-period-ns', '0.8333333333333333',
           '--clock-uncertainty-ns', '0.060', '--clock-uncertainty-hold-ns', '0.025',
           '--orfs-corner', 'WC', '--hold-corners', 'WC,BC',
           '--io-delay-fraction', '0.2', '--stages', 'pnr',
           '--core-utilization', str(a.util), '--place-density', '0.65',
           '--max-fanout', '32', '--max-transition-ns', '0.15',
           '--hold-margin-ns', '0.008', '--orfs-var', 'ADDER_MAP_FILE=',
           '--routing-layers', 'M2', 'M9',
           '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
           '--purpose', 'characterization', '--nickname-tag', f'window_column_w{a.width}_u{a.util}',
           '--keep-workdir', str(out/'work'), '--output', str(out/'physical.json')]
    (out/'command.json').write_text(json.dumps(cmd, indent=2)+'\n')
    rc = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, OT_ORFS_NUM_CORES='16')).returncode
    (out/'terminal.exit').write_text(str(rc)+'\n')
    raise SystemExit(rc)

if __name__ == '__main__':
    main()
