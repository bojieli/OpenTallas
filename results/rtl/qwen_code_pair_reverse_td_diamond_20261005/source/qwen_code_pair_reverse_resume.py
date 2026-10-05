#!/usr/bin/env python3
"""Explicit Claude TD-only/diamond successor of the retained reverse-bank flow.

Copies immutable inputs and stages through I/O placement; never synthesizes or
repeats floorplanning. Geometry, SDC, macros and capture membership stay intact.
Invoke this caller through the existing 64-GiB EPYC admission guard.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

IMAGE = 'sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
RETAINED = ('1_2_yosys.v', '1_2_yosys.sdc', '1_synth.odb', '1_synth.sdc',
            '2_1_floorplan.odb', '2_1_floorplan.sdc', '2_2_floorplan_macro.odb',
            '2_3_floorplan_tapcell.odb', '2_4_floorplan_pdn.odb',
            '2_floorplan.odb', '2_floorplan.sdc', '3_1_place_gp_skip_io.odb',
            '3_2_place_iop.odb', 'clock_period.txt')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--retained-work', type=Path, required=True)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--claude-td-diamond', action='store_true', required=True)
    a = ap.parse_args()
    old, src, work = [p.resolve() for p in (a.retained_work, a.source_dir, a.work)]
    base = next((old / 'results/asap7').glob('*/base'))
    config = (old / 'config.mk').read_text()
    assert 'export PLACE_DENSITY = 0.55\n' in config
    assert 'GPL_ROUTABILITY_DRIVEN' not in config and 'DETAIL_PLACEMENT_ARGS' not in config
    assert all((base / name).is_file() for name in RETAINED)
    bindings = json.loads((old / 'capture_bindings.json').read_text())
    assert len(bindings) == 2880
    work.mkdir(parents=True, exist_ok=False)
    inputs = ('mapped.v', 'mapped.json', 'constraint.sdc', 'regions.tcl',
              'local_capture_regions.tcl', 'capture_bindings.json', 'side_effects.mk',
              'route_manifest.json')
    for name in inputs:
        shutil.copy2(old / name, work / name)
    shutil.copytree(old / 'slot', work / 'slot')
    target = work / base.relative_to(old)
    target.mkdir(parents=True)
    frozen = {}
    for name in RETAINED:
        shutil.copy2(base / name, target / name)
        frozen[name] = sha(target / name)
        assert frozen[name] == sha(base / name)
    (work / 'config.mk').write_text(config +
        '\n# Claude GPL/DPL diagnosis: no physical/constraint change.\n'
        'export GPL_ROUTABILITY_DRIVEN = 0\n'
        'export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer\n')
    manifest = dict(retained_work=str(old), source_dir=str(src), image=IMAGE,
                    caller_sha256=sha(Path(__file__)), retained_stage_sha256=frozen,
                    input_sha256={name: sha(work / name) for name in inputs},
                    slot_sha256={str(p.relative_to(work / 'slot')): sha(p)
                                 for p in (work / 'slot').rglob('*') if p.is_file()},
                    config_deltas={'GPL_ROUTABILITY_DRIVEN': 0,
                                   'DETAIL_PLACEMENT_ARGS': '-use_diamond_legalizer'},
                    authority='claude_to_codex_pauli_kant_erdos_gpl_divergence.md',
                    cores=16, synthesis_repeated=False, floorplan_repeated=False)
    (work / 'successor.json').write_text(json.dumps(manifest, indent=2) + '\n')
    result = '/work/' + str(base.relative_to(old)) + '/'
    # Old-stage targets are explicitly frozen even if make sees changed config.
    freeze = ' '.join('-o ' + result + name for name in RETAINED)
    make = ('make -f Makefile -f /work/side_effects.mk '
            'DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base '
            'NUM_CORES=16 -j16 ' + freeze + ' ')
    cmd = ['docker', 'run', '--rm', '-v', f'{src}:/src:ro', '-v', f'{work}:/work',
           '-w', '/OpenROAD-flow-scripts/flow', IMAGE, 'bash', '-lc',
           'source /OpenROAD-flow-scripts/env.sh; ' + make + result +
           '3_3_place_gp.odb && ' + make + 'finish']
    with (work / 'route.log').open('w') as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    (work / 'route.exit').write_text(str(rc) + '\n')
    assert all(sha(target / name) == digest for name, digest in frozen.items())
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
