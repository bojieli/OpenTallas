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
    parser.add_argument('--phase-parallel', action='store_true', help='Changed exact18-bit phase validation; one contextual source vehicle')
    parser.add_argument('--owner-veto-polarity',action='store_true',help='Changed full192 sameedge negative owner/output frontier')
    parser.add_argument('--control-tail', action='store_true', help='Changed-source retained CP control/output-tail cut; requires finite pin/via repair')
    parser.add_argument('--gpl-repair', action='store_true', help='One source-identical GPL0307 continuation from retained IO')
    parser.add_argument('--variant', type=int, choices=(1,2,3), default=1,
                        help='Distinct installed GPL/DRT seeds, unchanged constraints and density')
    parser.add_argument('--resume-canonical', type=Path,
                        help='Retained canonical RTLIL after an unsuccessful mapping invocation')
    parser.add_argument('--canonical-sha256')
    parser.add_argument('--resume-cts-sha256', help='Resume validated CTS with mapped/floorplan/placement frozen')
    parser.add_argument('--resume-io-sha256', help='Resume actual validated mapped/PDN/IO objects without upstream replay')
    parser.add_argument('--resume-resized-sha256',
                        help='Reuse the mapped netlist and physical stages through validated3_4')
    args = parser.parse_args()
    job = args.job_root.resolve()
    import hbm_cp_parent_context as context
    # Verify the already generated, committed source envelope; do not mutate
    # the pinned clean source checkout during physical execution.
    from hbm_cp_source_validation import hbm_cp_validate_allocated_sources
    cp = json.loads((ROOT/context.CONTRACT).read_text())['CP']
    checked = hbm_cp_validate_allocated_sources(ROOT, cp, fourcut=True,fast_owner=args.fast_owner,phase_parallel=args.phase_parallel,control_tail=args.control_tail,owner_veto=args.owner_veto_polarity)
    input_path=ROOT/('physical/hbm_cp_parent_context_20261005/owner_veto_inputs.json' if args.owner_veto_polarity else ('physical/hbm_cp_parent_context_20261005/control_tail_inputs.json' if args.control_tail else ('physical/hbm_cp_parent_context_20261005/phase_parallel_inputs.json' if args.phase_parallel else 'physical/hbm_cp_parent_context_20261005/inputs.json')))
    inputs = json.loads(input_path.read_text())
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
    finite = None
    if args.fast_owner:
        assert inputs['parameters']['SU_FAST_OWNER_FRONTIER']==1
        finite_path = ROOT/'results/uarch/hbm_cp_fast_parent_allocation_20261006/model.json'
        finite = json.loads(finite_path.read_text())
        assert finite['source_commit'].startswith('e0e05a19e')
        assert finite['boundary_bits']==12 and finite['external_pins']==236
        assert finite['charged_body_total_um2'] <= finite['cell_budget_um2']
        assert len(set(finite['M7']['reserved_factor_track_X_DBU']))==12
        for path,digest in finite['hooks_sha256'].items():
            assert sha(ROOT/path)==digest, path
        for option,values in [('--die-area',finite['local_die_um']),
                              ('--core-area',finite['local_core_um'])]:
            index=argv.index(option)+1
            argv[index:index+4]=[str(v) for v in values]
        index=argv.index('--step-tcl')+1
        assert argv[index].startswith('POST_IO_PLACEMENT=')
        argv[index]='POST_IO_PLACEMENT=physical/hbm_cp_parent_context_20261005/fast_frontier_post_io.tcl'
        argv += ['--step-tcl', 'PRE_GLOBAL_PLACE=physical/hbm_cp_parent_context_20261005/fast_frontier_unique_regions.tcl',
                 '--step-tcl', 'PRE_GLOBAL_ROUTE=physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl',
                 '--orfs-var', f'GPL_RANDOM_SEED={args.variant}',
                 '--orfs-var', f'OR_SEED={args.variant}',
                 '--orfs-var', 'PLACE_DENSITY_LB_ADDON=']
        argv += ['--param', 'SU_FAST_OWNER_FRONTIER=1']
    if args.phase_parallel:
        assert inputs['parameters']['SU_PARALLEL_PHASE_VALIDATION']==1
        if not args.gpl_repair:
            assert not (args.resume_canonical or args.resume_cts_sha256 or args.resume_io_sha256 or args.resume_resized_sha256), "Changed RTL needs fresh synthesis"
        argv += ['--param','SU_PARALLEL_PHASE_VALIDATION=1']
        argv[argv.index('--nickname-tag')+1]='harvey_cp_phase_parallel_context_r1'
    if args.control_tail:
        assert args.fast_owner and args.phase_parallel and args.variant==1 and not args.gpl_repair
        assert not (args.resume_canonical or args.resume_cts_sha256 or args.resume_io_sha256 or args.resume_resized_sha256), 'Changed control-tail RTL requires synthesis'
        assert inputs['parameters']['SU_CONTROL_TAIL_CUT']==1
        assert model['charged_body_upper_um2']<=model['conservative_body_budget_um2']
        argv += ['--param','SU_CONTROL_TAIL_CUT=1','--orfs-var','MAX_PLACE_STEP_COEF=1.01']
        argv[argv.index('--place-density')+1]='0.55'
        argv[argv.index('--nickname-tag')+1]='harvey_cp_control_tail_context_r1'
        access=inputs['finite_pin_via_repair_contract']
        assert sha(ROOT/access['allocation_path'])==access['allocation_sha256']
        canonical_access=json.loads((ROOT/access['allocation_path']).read_text())
        assert canonical_access['allocation_accepted'] and canonical_access['conditional_defect_hunt_ready']
        assert canonical_access['used']==236 and canonical_access['private_factor_bits']==12
        for path,digest in canonical_access['hashes'].items():
            assert sha(ROOT/path)==digest, 'Canonical access dependency changed: '+path
        assert access['all_pins']==236 and access['minimum_pitch_um']==0.128
        for path,digest in access['hooks_sha256'].items():
            assert sha(ROOT/path)==digest, 'Pin access hook changed: '+path
        index=argv.index('--step-tcl')+1
        assert argv[index]=='POST_IO_PLACEMENT=physical/hbm_cp_parent_context_20261005/fast_frontier_post_io.tcl'
        argv[index]='POST_IO_PLACEMENT=physical/hbm_die_abstracts_20261006/integration/cp_control_tail_access/post_io.tcl'
    if args.owner_veto_polarity:
        assert args.control_tail and args.phase_parallel and args.fast_owner and args.variant==1
        assert inputs['parameters']['SU_OWNER_VETO_POLARITY']==1
        assert model['association_upper_um2']<=model['association_budget_um2']
        argv += ['--param','SU_OWNER_VETO_POLARITY=1']
        argv[argv.index('--nickname-tag')+1]='harvey_cp_owner_veto_context_r1'
    argv += ['--param', 'SU_FOUR_COMBINATIONAL_CUTS=1',
             '--step-tcl', 'PRE_DETAIL_PLACE=physical/hbm_cp_parent_context_20261005/cts_membership.tcl']
    if finite:
        argv[-1]='PRE_DETAIL_PLACE=physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl'
    record = dict(schema='hbm.cp.fourcut.context-route.v1', argv=argv,
        checked_sources=checked, exact_gate=model['exact_measurement'],
        exact_sha256=sha(ROOT/model['exact_measurement']),
        physical_inputs_sha256=sha(input_path),
        hook_sha256=sha(hook), source_changed=True, synthesis_required=True,
        old_R6_preserved=True, fences_changed=False, pins_changed=False,
        setup_ps=60, hold_ps=25, source_phase_ps=0,
        added_RTL_FF=0, added_RTL_cycles=0, adopted=False,fast_owner=args.fast_owner)
    if finite:
        record.update(finite_parent_model='results/uarch/hbm_cp_fast_parent_allocation_20261006/model.json',
            finite_parent_model_sha256=sha(finite_path), finite_allocation=finite,
            placement_seed=args.variant, detailed_route_seed=args.variant,
            analytical_inputs_until_actual_CTS=True,
            parent_supply_drop_unmeasured=True,
            explicit_modeled_density=0.5,automatic_density_prequery_disabled=True,
            canonical_initial_placement_removes_empty_core=True,
            membership_after_port_buffering=True)
    # Validate the actual pinned packet before --prepare-only can succeed.
    # The tapcell gate has one canonical file-join dependency; other installed
    # CP hooks source literal /src paths. No Tcl hook is rewritten or waived.
    dependencies=set()
    for index,option in enumerate(argv[:-1]):
        if option in ('--source','--sdc-append'):
            dependencies.add(argv[index+1])
        elif option=='--step-tcl':
            dependencies.add(argv[index+1].split('=',1)[1])
        elif option=='--orfs-var' and argv[index+1].startswith('PDN_TCL=/src/'):
            dependencies.add(argv[index+1].split('/src/',1)[1])
    pending=list(dependencies)
    import re
    while pending:
        path=pending.pop()
        file=ROOT/path
        if not file.is_file():raise FileNotFoundError('Pinned CP packet missing required input: '+path)
        if file.suffix!='.tcl':continue
        children=re.findall(r'^source /src/([^\s]+)',file.read_text(),re.MULTILINE)
        if path=='physical/common/ot_macro_track_assert_hook.tcl':
            children.append('physical/common/ot_macro_track_snap.tcl')
        for child in children:
            if child not in dependencies:dependencies.add(child);pending.append(child)
    record['physical_dependencies_sha256']={path:sha(ROOT/path) for path in sorted(dependencies)}
    if args.control_tail:
        record.update(control_tail=True,explicit_modeled_density=0.55,gpl_max_phi_coef=1.01,
            physical_ready=inputs.get('finite_pin_via_repair_ready',False),
            physical_blocker=None if inputs.get('finite_pin_via_repair_ready',False) else 'Turing canonical CP236 pin-access acceptance pending',
            pin_access=inputs['finite_pin_via_repair_contract'],pins_changed=True,
            parent_IR_budget_conditional=True)
        if not args.prepare_only and not record['physical_ready']:
            raise ValueError(record['physical_blocker'])
    if args.owner_veto_polarity:
        record.update(owner_veto_polarity=True,complete_current_owner_bits=192,source_changed=True)
    if args.gpl_repair:
        assert args.phase_parallel and args.fast_owner and args.variant==1
        assert args.resume_io_sha256 and not (args.resume_canonical or args.resume_cts_sha256 or args.resume_resized_sha256)
        repair_path=ROOT/'results/physical/hbm_cp_phase_parallel_parent_context_20261006/r3_gpl_repair/model.json'
        repair=json.loads(repair_path.read_text())
        assert repair['retained_IO_sha256']==args.resume_io_sha256
        assert repair['fixed_MAX_PLACE_STEP_COEF']==1.01 and repair['fixed_place_density']==0.55
        for name,key in [('3_2_place_iop.odb','retained_IO_sha256'),('1_2_yosys.v','retained_mapped_sha256')]:
            found=list((job/'work/orfs/results').rglob(name))
            assert len(found)==1 and sha(found[0])==repair[key], 'GPL repair requires exact retained '+name
        for path,digest in repair['RTL_source_sha256'].items():
            assert sha(ROOT/path)==digest, 'GPL source-identical repair changed '+path
        argv += ['--orfs-var','MAX_PLACE_STEP_COEF=1.01']
        argv[argv.index('--place-density')+1]='0.55'
        record.update(argv=argv,physical_repair='GPL0307 smaller max_phi_coef',
            explicit_modeled_density=0.55,gpl_max_phi_coef=1.01,
            source_changed=False,synthesis_required=False,synthesis_reused=True,
            retained_IO_sha256=repair['retained_IO_sha256'],
            gpl_repair_model_sha256=sha(repair_path))
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
    if args.resume_resized_sha256 or args.resume_io_sha256 or args.resume_cts_sha256:
        checkpoint_name = '4_1_cts.odb' if args.resume_cts_sha256 else ('3_4_place_resized.odb' if args.resume_resized_sha256 else '3_2_place_iop.odb')
        checkpoint_digest = args.resume_cts_sha256 or args.resume_resized_sha256 or args.resume_io_sha256
        checkpoints = list((case/'results').rglob(checkpoint_name))
        assert len(checkpoints) == 1 and sha(checkpoints[0]) == checkpoint_digest
        for path in checkpoints[0].parent.iterdir():
            stage = path.name.split('_')
            if path.suffix not in ('.odb', '.sdc', '.v', '.rtlil') or 'failed' in path.name:
                continue
            if (args.resume_cts_sha256 and stage[0]=='4') or stage[0] in ('1', '2') or (stage[0]=='3' and len(stage)>1 and stage[1] in (('1','2','3','4','5','place') if args.resume_cts_sha256 else (('1','2','3','4') if args.resume_resized_sha256 else ('1','2')))):
                frozen[path] = sha(path)
        mapped = checkpoints[0].parent/'1_2_yosys.v'
        assert mapped in frozen
        record.update(synthesis_required=False, synthesis_reused=True,
            resume_resized_sha256=args.resume_resized_sha256,resume_io_sha256=args.resume_io_sha256,resume_cts_sha256=args.resume_cts_sha256,
            upstream_sha256={str(p.relative_to(case)):h for p,h in frozen.items()})
        (job/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')
    if finite:
        (case/'cts_membership.tcl').write_text(
            'source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl\n')
    else:
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
    if finite:
        # Same installed canonical GPL as Noether a0076e760/c3f2e5fb0:
        # initial placement removes an empty top-level component. The earlier
        # automatic-density prequery cannot initialize that empty component.
        # Preserve exact modeled density0.5 and bind newly inserted IO cells
        # after native port buffering, before canonical initial placement.
        patch += '''
p=Path('/OpenROAD-flow-scripts/flow/scripts/global_place.tcl')
s=p.read_text()
needle='proc do_placement { global_placement_args } {'
assert s.count(needle)==1, 'Installed GPL port-buffer/placement API changed'
s=s.replace(needle,'source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl'+chr(10)+needle)
p.write_text(s)
p=Path('/OpenROAD-flow-scripts/flow/scripts/global_route.tcl')
s=p.read_text()
needle='    log_cmd detailed_placement'
assert s.count(needle)==2, 'Installed GRT repair legalization API changed'
s=s.replace(needle,'    source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl'+chr(10)+needle)
p.write_text(s)
'''
    if args.gpl_repair or args.control_tail:
        patch="""from pathlib import Path
import hashlib
p=Path('/OpenROAD-flow-scripts/flow/scripts/global_place.tcl')
s=p.read_text()
assert hashlib.sha256(s.encode()).hexdigest()=='05a7a124580f8a023113ad1f4d56c15e61c3640142f4581c27d5ebaa6aa59e33', 'Installed canonical GPL changed'
assert 'lappend global_placement_args -max_phi_coef $::env(MAX_PLACE_STEP_COEF)' in s
"""+patch
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
