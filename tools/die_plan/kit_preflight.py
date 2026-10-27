#!/usr/bin/env python3
"""Cheap kit admission checks before an expensive synthesis/route allocation.

Runs the existing SDC/FF-binding, cast-form, master-slice and staged-file checks.
This is a static gate; RTL elaboration, netlist LEC/face/fanout, PG and routed
corner checks remain mandatory later stages, and are not reported as passed here.
"""
import argparse
import re
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdc_lint
import rtl_lint
import kit_contract

# Inputs consumed by make must survive removal of the generator worktree.
INPUT_VARS = ('VERILOG_FILES', 'VERILOG_INCLUDE_DIRS', 'SYNTH_INCLUDE_DIRS',
              'SDC_FILE', 'ADDITIONAL_LEFS', 'ADDITIONAL_LIBS', 'ADDITIONAL_GDS',
              'PRE_SYNTH_TCL', 'POST_SYNTH_TCL', 'PRE_FLOORPLAN_TCL',
              'POST_FLOORPLAN_TCL', 'PRE_CTS_TCL', 'POST_CTS_TCL',
              'POST_GLOBAL_ROUTE_TCL', 'LAYER_PARASITICS_FILE', 'SET_RC_TCL')
REQUIRED = ('config.mk', 'constraint.sdc', 'sdc_lint.json', 'pins.json',
            'lec.py', 'rtl_lint.py', 'face_guard.py', 'signoff.py')


# FLOW-MCMM-GRT 2026-10-27 (S81-ECO-2 CHECKED, ot_s81sl_vq TT -64.57 / 88 EP): an FF-only GRT repair step
# (`make grt CORNER=BC CORNERS=bc`) loads the FF libraries only and never repairs TT setup on the GRT parasitics.  A
# two-corner kit (CORNERS tc bc) with the per-corner vclk binding must run the two-scene step (grt_scenes.sh).
FF_ONLY_GRT = re.compile(r"(?:\bgrt|do-5_1_grt)\s+CORNER=BC\s+CORNERS=bc\b")
RUNNERS = ('run_kit.sh', 'run_kit_kv.sh', 'run_kit_hbm.sh')
SCENE_FILES = ('grt_scenes.sh', 'grt_ff_scene.sdc', 'orfs_hold_mm.py', 'orfs_hold_mm.tcl', 'vclk_corner.tcl',
               'vclk_measured_hold.tcl', 'vclk_ref.py')


def grt_scenes_errors(kit):
    """[errors]: two-corner kit whose runner repairs at GRT in an FF-only session, or lacks the scene helpers."""
    kit = Path(kit)
    if not (kit/'config.mk').is_file():
        return []
    import kit_modes
    v = kit_modes.mk_vars((kit/'config.mk').read_text(errors='replace'))
    if kit_modes.corners(v.get('CORNERS')) != ['tc', 'bc'] or not v.get('OT_VCLK_FF'):
        return []
    errors = []
    for name in RUNNERS:
        if not (kit/name).is_file():
            continue
        text = (kit/name).read_text(errors='replace')
        for m in FF_ONLY_GRT.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            errors.append(f'{name}:{line}: FF-only GRT repair step on a tc+bc kit (FF libraries only: TT setup is '
                          'never repaired on GRT parasitics); use grt_scenes.sh (regenerate with main tools)')
        if 'grt_scenes.sh' in text:
            errors += [f'{name} runs grt_scenes.sh but the kit lacks {f}' for f in SCENE_FILES if not (kit/f).is_file()]
    return errors


def check(kit, plan_dir=None, contract=False):
    kit = Path(kit).resolve()
    issues, checks = [], {}
    def run(name, fn):
        try:
            errors = fn()
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors = [f'{type(error).__name__}: {error}']
        checks[name] = dict(verdict='FAIL' if errors else 'PASS', errors=errors)
        issues.extend(f'{name}: {error}' for error in errors)
    run('staged_tools', lambda: [f'missing {name}' for name in REQUIRED if not (kit/name).is_file()])
    cfg = rtl_lint.config(kit) if (kit/'config.mk').is_file() else {}
    def staged_inputs():
        errors = []
        if len(cfg.get('DESIGN_NAME', [])) != 1 or not cfg.get('VERILOG_FILES'):
            errors.append('one DESIGN_NAME and nonempty VERILOG_FILES required')
        for var in INPUT_VARS:
            for value in cfg.get(var, []):
                # ORFS platform references expand inside the admitted container;
                # all literal /work references, including hooks, must be staged.
                if value.startswith('/work/') and not (kit/value[6:]).exists():
                    errors.append(f'{var}: unstaged {value}')
                elif value.startswith('/') and not value.startswith(('/work/', '/OpenROAD-flow-scripts/')):
                    errors.append(f'{var}: host-only path {value}; stage under /work')
        for name in ('run_kit.sh', 'run_kit_kv.sh'):
            if (kit/name).is_file():
                # Parse syntax without executing the runner or any shell substitution.
                import subprocess
                result = subprocess.run(['bash', '-n', str(kit/name)], capture_output=True, text=True)
                if result.returncode:
                    errors.append(f'{name}: {result.stderr.strip()}')
        return errors
    run('staged_inputs', staged_inputs)
    run('sdc_and_ff_binding', lambda: sdc_lint.lint_kit_files(kit))
    run('grt_scenes', lambda: grt_scenes_errors(kit))
    def cast_forms():
        hits = rtl_lint.yosys_cast_scan(rtl_lint._kit_sources(kit))
        return [f'{path}:{line}: {rule}: {snippet}' for path, entries in hits.items()
                for line, rule, snippet in entries]
    run('yosys_cast_forms', cast_forms)
    if (kit/'master_slice.json').is_file():
        def slice_check():
            import master_slice
            report = master_slice.check_kit(kit)
            return report.get('issues', [])
        run('master_slice', slice_check)
    # PREFLIGHT-2 (OWNER 10-27): the shared kit contract, one check per recent bug class (kit_contract.py)
    # Binding (fail-closed) on hard-core kits; recorded as advisory on other kits (partition tiles) unless forced.
    binding = contract or kit_contract.is_core_kit(kit)
    advisory = {}
    for name, row in kit_contract.run_all(kit, plan_dir).items():
        if binding:
            checks[name] = row
            issues.extend(f'{name}: {error}' for error in row['errors'])
        else:
            advisory[name] = row
    return dict(schema='opentallas.kit_preflight.v2', kit=str(kit), contract=list(kit_contract.CHECKS),
                contract_binding=binding, contract_advisory=advisory,
                verdict='FAIL' if issues else 'PASS', checks=checks, issues=issues,
                deferred=['RTL elaboration/SELRANGE', 'synthesis face/fanout/port binding/LEC',
                          'placed and routed PG', 'TT setup / FF hold', 'routed LEC'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--plan-dir', type=Path, help='plan dir resolving freeze.json pins_file (optional)')
    ap.add_argument('--no-emit', action='store_true', help='do not write <kit>/preflight.json')
    ap.add_argument('--contract', action='store_true', help='kit contract binding on any kit (default: core kits)')
    args = ap.parse_args(argv)
    record = check(args.kit, args.plan_dir, args.contract)
    if not args.no_emit:
        # latest verdict beside freeze.json (timestamped --out receipts stay immutable)
        import os
        import tempfile
        kd = Path(record['kit'])
        with tempfile.NamedTemporaryFile('w', dir=kd, prefix='.preflight.', delete=False) as handle:
            handle.write(json.dumps(record, indent=1)+'\n')
        os.replace(handle.name, kd/'preflight.json')
    if args.out:
        # Never overwrite an existing failure/success receipt.
        with args.out.open('x') as handle:
            handle.write(json.dumps(record, indent=1)+'\n')
    print('KIT_PREFLIGHT', record['verdict'], 'issues', len(record['issues']))
    for issue in record['issues'][:30]:
        print('  -', issue)
    return int(record['verdict'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
