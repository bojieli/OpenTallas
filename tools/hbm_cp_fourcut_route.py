#!/usr/bin/env python3
"""One source-faithful CP four-cut context; retain finite fences through CTS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-root', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--fast-owner', action='store_true')
    parser.add_argument('--resume-canonical', type=Path,
                        help='Retained canonical RTLIL after an unsuccessful mapping invocation')
    parser.add_argument('--canonical-sha256')
    parser.add_argument('--resume-resized-sha256',
                        help='Reuse the mapped netlist and physical stages through validated3_4')
    args = parser.parse_args()
    job = args.job_root.resolve()
    import hbm_cp_parent_context as context
    # Verify the already generated, committed source envelope; do not mutate
    # the pinned clean source checkout during physical execution.
    from hbm_cp_source_validation import hbm_cp_validate_allocated_sources
    cp = json.loads((ROOT/context.CONTRACT).read_text())['CP']
    checked = hbm_cp_validate_allocated_sources(ROOT, cp, fourcut=True,fast_owner=args.fast_owner)
    inputs = json.loads((ROOT/'physical/hbm_cp_parent_context_20261005/inputs.json').read_text())
    assert inputs['parameters']['SU_FOUR_COMBINATIONAL_CUTS'] == 1
    assert inputs['checked_sources'] == checked
    model = json.loads((ROOT/inputs['four_cut_model']).read_text())
    assert sha(ROOT/inputs['four_cut_model']) == inputs['four_cut_model_sha256']
    exact = json.loads((ROOT/model['exact_measurement']).read_text())
    for source, digest in exact['source_sha256'].items():
        assert sha(ROOT/source) == digest, source
    allocation = json.loads((ROOT/'results/physical/hbm_cp_cts_allocation_20261005/model.json').read_text())
    hook = ROOT/allocation['hook']
    assert sha(hook) == allocation['hook_sha256']
    original = json.loads((ROOT/'results/physical/hbm_cp_parent_context_20261005/r1/physical.json').read_text())
    argv = original['runner']['argv'][1:]
    for option, value in [('--keep-workdir', job/'work'),
                          ('--output', job/'physical.json'),
                          ('--nickname-tag', 'harvey_cp_fourcut_context_r1')]:
        argv[argv.index(option)+1] = str(value)
    if args.fast_owner:
        assert inputs['parameters']['SU_FAST_OWNER_FRONTIER']==1
        argv += ['--param', 'SU_FAST_OWNER_FRONTIER=1']
    argv += ['--param', 'SU_FOUR_COMBINATIONAL_CUTS=1',
             '--step-tcl', 'PRE_DETAIL_PLACE=physical/hbm_cp_parent_context_20261005/cts_membership.tcl']
    record = dict(schema='hbm.cp.fourcut.context-route.v1', argv=argv,
        checked_sources=checked, exact_gate=model['exact_measurement'],
        exact_sha256=sha(ROOT/model['exact_measurement']),
        physical_inputs_sha256=sha(ROOT/'physical/hbm_cp_parent_context_20261005/inputs.json'),
        hook_sha256=sha(hook), source_changed=True, synthesis_required=True,
        old_R6_preserved=True, fences_changed=False, pins_changed=False,
        setup_ps=60, hold_ps=25, source_phase_ps=0,
        added_RTL_FF=0, added_RTL_cycles=0, adopted=False,fast_owner=args.fast_owner)
    job.mkdir(parents=True, exist_ok=True)
    (job/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')
    if args.prepare_only:
        return 0
    case = job/'work/orfs'
    case.mkdir(parents=True, exist_ok=True)
    (case/'tmp').mkdir(exist_ok=True)  # ORFS TMPDIR=/work/tmp is container-local.
    canonical = args.resume_canonical.resolve() if args.resume_canonical else None
    if canonical:
        assert canonical.is_relative_to(case)
        assert canonical.name == '1_1_yosys_canonicalize.rtlil'
        assert sha(canonical) == args.canonical_sha256
        record['retained_canonical_sha256'] = sha(canonical)
        record['canonical_frontend_reused'] = True
        (job/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')
    frozen = {}
    if args.resume_resized_sha256:
        checkpoints = list((case/'results').rglob('3_4_place_resized.odb'))
        assert len(checkpoints) == 1 and sha(checkpoints[0]) == args.resume_resized_sha256
        for path in checkpoints[0].parent.iterdir():
            stage = path.name.split('_')
            if path.suffix not in ('.odb', '.sdc', '.v', '.rtlil') or 'failed' in path.name:
                continue
            if stage[0] in ('1', '2') or (stage[0]=='3' and len(stage)>1 and stage[1] in ('1','2','3','4')):
                frozen[path] = sha(path)
        mapped = checkpoints[0].parent/'1_2_yosys.v'
        assert mapped in frozen
        record.update(synthesis_required=False, synthesis_reused=True,
            resume_resized_sha256=args.resume_resized_sha256,
            upstream_sha256={str(p.relative_to(case)):h for p,h in frozen.items()})
        (job/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')
    shutil.copyfile(hook, case/'cts_membership.tcl')
    patch = '''from pathlib import Path
import hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl')
s=p.read_text()
needle='set result [catch { log_cmd detailed_placement } msg]'
assert s.count(needle)==2, 'Installed CTS legalization API changed'
print(json.dumps(dict(original_cts_sha256=hashlib.sha256(s.encode()).hexdigest(),membership_calls=2)))
p.write_text(s.replace(needle,'source /work/cts_membership.tcl\\n'+needle))
'''
    (case/'bind_cts_membership.py').write_text(patch)
    import run_abi3_physical as driver
    original_run = driver.run
    def run(command, **kwargs):
        if command[:3] == ['docker', 'run', '--rm'] and 'make DESIGN_CONFIG=/work/config.mk' in command[-1]:
            if frozen and '1_2_yosys.v && chmod a+w' in command[-1]:
                assert sha(mapped) == frozen[mapped]
                return subprocess.CompletedProcess(command, 0,
                    stdout='REUSED_VALIDATED_FOURCUT_MAPPED_NETLIST '+sha(mapped)+'\n', stderr='')
            command = list(command)
            if frozen:
                keep=[]
                for path in frozen:
                    keep.extend(['-o','/work/'+str(path.relative_to(case))])
                command[-1] = command[-1].replace('make DESIGN_CONFIG=/work/config.mk',
                    'make '+shlex.join(keep)+' DESIGN_CONFIG=/work/config.mk',1)
            if canonical:
                command[-1] = command[-1].replace('make DESIGN_CONFIG=/work/config.mk',
                    'make -o /work/'+str(canonical.relative_to(case))+' DESIGN_CONFIG=/work/config.mk',1)
            command[-1] = 'python3 /work/bind_cts_membership.py || exit $?; '+command[-1]
        return original_run(command, **kwargs)
    driver.run = run
    rc = driver.main(argv)
    for path,digest in frozen.items():
        assert sha(path) == digest, 'Earlier physical stage changed: '+str(path)
    if canonical:
        assert sha(canonical) == args.canonical_sha256, 'Retained canonical frontend changed'
    (job/'route.exit').write_text(str(rc)+'\n')
    if list(case.glob('results/**/6_final.odb')):
        # Separate corner sessions use actual propagated CTS and extracted RC;
        # all_registers -data_pins distinguishes FF endpoints from literal */D.
        try:
            context.corner_sta(case, job/'corner_sta.json')
            (job/'corner.exit').write_text('0\n')
        except Exception as error:
            (job/'corner.error').write_text(repr(error)+'\n')
            (job/'corner.exit').write_text('1\n')
        import hbm_cp_context_loaded_ir as loaded
        import sys
        saved = sys.argv
        sys.argv = [str(ROOT/'tools/hbm_cp_context_loaded_ir.py'),
                    '--orfs', str(case), '--output', str(job/'loaded_ir')]
        try:
            loaded.main()
            (job/'loaded_ir.exit').write_text('0\n')
        except Exception as error:
            (job/'loaded_ir.error').write_text(repr(error)+'\n')
            (job/'loaded_ir.exit').write_text('1\n')
        finally:
            loaded.context_decision(job/'loaded_ir')
            sys.argv = saved
    else:
        (job/'loaded_ir_skipped.txt').write_text('No terminal routed ODB; preserve actual flow failure.\n')
    (job/'terminal.exit').write_text(str(rc)+'\n')
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
