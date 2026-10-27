#!/usr/bin/env python3
"""Cheap kit admission checks before an expensive synthesis/route allocation.

Runs the existing SDC/FF-binding, cast-form, master-slice and staged-file checks.
This is a static gate; RTL elaboration, netlist LEC/face/fanout, PG and routed
corner checks remain mandatory later stages, and are not reported as passed here.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdc_lint
import rtl_lint

# Inputs consumed by make must survive removal of the generator worktree.
INPUT_VARS = ('VERILOG_FILES', 'VERILOG_INCLUDE_DIRS', 'SYNTH_INCLUDE_DIRS',
              'SDC_FILE', 'ADDITIONAL_LEFS', 'ADDITIONAL_LIBS', 'ADDITIONAL_GDS',
              'PRE_SYNTH_TCL', 'POST_SYNTH_TCL', 'PRE_FLOORPLAN_TCL',
              'POST_FLOORPLAN_TCL', 'PRE_CTS_TCL', 'POST_CTS_TCL',
              'POST_GLOBAL_ROUTE_TCL', 'LAYER_PARASITICS_FILE', 'SET_RC_TCL')
REQUIRED = ('config.mk', 'constraint.sdc', 'sdc_lint.json', 'pins.json',
            'lec.py', 'rtl_lint.py', 'face_guard.py', 'signoff.py')


def check(kit):
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
    return dict(schema='opentallas.kit_preflight.v1', kit=str(kit),
                verdict='FAIL' if issues else 'PASS', checks=checks, issues=issues,
                deferred=['RTL elaboration/SELRANGE', 'synthesis face/fanout/port binding/LEC',
                          'placed and routed PG', 'TT setup / FF hold', 'routed LEC'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args(argv)
    record = check(args.kit)
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
