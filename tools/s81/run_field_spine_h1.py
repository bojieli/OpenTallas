#!/usr/bin/env python3
"""DS-ROM field spine v13b (d0178820d, source-identical pinned RTL of physical/s81_pq_r128_expanded) re-routed under
flow-hold RULE H1 (s81-fieldphase 2026-10-07): the die-link hold budget is carried once, by the sender's output min
delay, so the block's input min is 0 against its boundary-register arrival (was -50) in the routing SDC, the CTS / GRT
reference-pin hooks and the sign-off SDC.  Everything else is the v13b recipe (770 ps routing clock, 60/25 ps, WC/BC
hold corners, HM 40 ps, slew margin 40 %, kept quantiser / multiplier modules).

    python3 tools/s81/run_field_spine_h1.py --R 128 --geom x550 --work W --output W/c1r128_h1x.json [--pnr-stop-after cts]
    python3 tools/s81/run_field_spine_h1.py --R 16  --geom u35  --work W --output W/c1r16_h1.json
geom x550: the expanded 550.368 um slot of physical/s81_pq_r128_expanded/model.json (owner 55-60 % utilisation rule);
geom u35:  --core-utilization 35, the v13b R16 recipe (physical/dsrom_field_spine/phys13.sh)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
PIN = Path('physical/s81_pq_r128_expanded')
BASE = Path('physical/s81_field_spine_h1')
sys.path.insert(0, str(ROOT/'tools'))


def command(R, geom, work, output):
    binding = json.loads((ROOT/PIN/'source_binding.json').read_text())
    for f in binding['files']:
        if hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest() != f['sha256']:
            raise ValueError('Pinned input changed: '+f['path'])
    args = ['--view', 'asap7', '--top', 'ot_v41_pqc_spine_screen']
    for f in binding['files']:
        if f['role'] == 'RTL':
            args += ['--source', f['path']]
    args += ['--clock-period-ns', '.770', '--clock-uncertainty-ns', '.060',
             '--clock-uncertainty-hold-ns', '.025', '--corner', 'TT', '--orfs-corner', 'WC',
             '--hold-corners', 'WC,BC', '--max-transition-ns', '--max-fanout', '32',
             '--orfs-var', 'ADDER_MAP_FILE=', '--orfs-var', 'NUM_CORES=16',
             '--orfs-var', 'VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS',
             '--orfs-var', 'SYNTH_KEEP_MODULES=ot_dsrom_aq12m_mul ot_dsrom_aq12m',
             '--sdc-append', str(BASE/'io_budget_h1.sdc'),
             '--slew-margin-percent', '40', '--hold-margin-ns', '.040',
             '--param', 'PQ=1', '--param', f'R={R}', '--stages', 'pnr',
             '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
             '--keep-heavy-artifacts', '--nickname-tag', f's81fs_h1_r{R}_{geom}',
             '--keep-workdir', str(work), '--output', str(output)]
    for stage, name in [('PRE_CTS', 'io_ref_pre_h1.tcl'), ('PRE_GLOBAL_ROUTE', 'io_ref_pre_h1.tcl'),
                        ('POST_CTS', 'io_ref_post_h1.tcl'), ('POST_GLOBAL_ROUTE', 'io_ref_post_h1.tcl')]:
        args += ['--step-tcl', stage+'='+str(BASE/name)]
    if geom == 'x550':
        model = json.loads((ROOT/PIN/'model.json').read_text())
        args += ['--die-area', '0', '0']+[str(v) for v in model['geometry']['die_um']]
        args += ['--core-area']+[str(v) for v in model['geometry']['core_box_um']]
    elif geom == 'u35':
        args += ['--core-utilization', '35']
    else:
        raise ValueError(geom)
    return args


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--R', type=int, choices=(16, 128), required=True)
    p.add_argument('--geom', choices=('x550', 'u35'), required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--pnr-stop-after')
    a = p.parse_args()
    args = command(a.R, a.geom, a.work, a.output)
    if a.pnr_stop_after:
        args += ['--pnr-stop-after', a.pnr_stop_after]
    import run_abi3_physical as flow
    flow.build_parser().parse_args(args)
    if a.prepare_only:
        print(json.dumps(dict(status='PREPARED_NOT_RUN', argv=args, physical_closed=False), indent=2))
        return 0
    rc = flow.main(args, synth_timeout=None, flow_timeout=None)
    if rc or a.pnr_stop_after:
        return rc
    return subprocess.call([sys.executable, str(ROOT/'tools/w18/corner_sta.py'),
                            '--orfs-dir', str(a.work/'orfs'), '--post-sdc', str(BASE/'signoff_h1.sdc'),
                            '--output', str(a.output.with_name(a.output.stem+'_corner_sta.json'))], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
