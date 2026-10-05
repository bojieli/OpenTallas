#!/usr/bin/env python3
"""Preparation-only full-token plan validation; never an RTL exactness verdict."""
import argparse, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
PINS = ['rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp',
        'rtl/test/v41_runtime/ot_v41_rt_die.sv',
        'tools/w17_current_fastpp_die_rt.py',
        'tools/w17_current_fastpp_l20_sources.txt']

def validate(plan):
    errors = []
    stages = plan.get('stages', [])
    expected = [f'layer{i}' for i in range(40)] + ['final_norm', 'vocabulary_head']
    if [s.get('id') for s in stages] != expected:
        errors.append('ordered coverage must be layers0..39, final_norm, vocabulary_head')
    if plan.get('dut_lifetime') != 'persistent_per_physical_stage_and_rank':
        errors.append('actual DUT KV must persist per modeled physical stage/rank')
    if plan.get('transport') != 'finite_hardware_ready_valid':
        errors.append('stage hops require finite hardware ready/valid transport')
    if plan.get('host_activation_arithmetic') or plan.get('host_activation_gather'):
        errors.append('host arithmetic/gather cannot transport token activation')
    for i, s in enumerate(stages):
        sid = s.get('id', str(i))
        if s.get('reset') or s.get('reconstruct_dut'):
            errors.append(sid + ': reset/reconstruction forbidden at stage boundary')
        if s.get('golden_activation_load') or s.get('golden_current_kv_load'):
            errors.append(sid + ': golden producer injection forbidden')
        producer = 'token_input' if i == 0 else stages[i-1].get('id') + '.rtl_output'
        if s.get('activation_from') != producer:
            errors.append(sid + ': activation must come from ' + producer)
        if s.get('golden_role') != 'comparison_only':
            errors.append(sid + ': golden must be comparison only')
        if i < 40 and s.get('current_kv_from') != sid + '.dut_kv_writer':
            errors.append(sid + ': connected current-token KV writer required')
        if s.get('reload_state'):
            errors.append(sid + ': stage reload may not overwrite activation/KV/index/window state')
    return errors

def template():
    ids = [f'layer{i}' for i in range(40)] + ['final_norm','vocabulary_head']
    return dict(dut_lifetime='persistent_per_physical_stage_and_rank',
        transport='finite_hardware_ready_valid', host_activation_arithmetic=False,
        host_activation_gather=False, physical_stage_mapping='UNBOUND_W16_MODEL',
        physical_stage_count=None, conditional_stage_count_candidate=45, stages=[dict(
        id=s, activation_from='token_input' if i==0 else ids[i-1]+'.rtl_output',
        current_kv_from=s+'.dut_kv_writer' if i<40 else None,
        golden_role='comparison_only', reset=False, reconstruct_dut=False,
        golden_activation_load=False,golden_current_kv_load=False,reload_state=False,
        physical_stage='UNBOUND_W16_MODEL', rom_weights='stage_specific_pinned',
        implementation='UNBOUND')
        for i,s in enumerate(ids)])

def audit():
    files = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINS}
    wrapper = (ROOT/PINS[1]).read_text(); host = (ROOT/PINS[0]).read_text()
    return dict(status='PREPARATION_BLOCKED_NOT_SIMULATION_PASS', source_sha256=files,
        findings=dict(vm_read_export='export "DPI-C" function v41rt_vm_word' in wrapper,
            stage_reload_export='export "DPI-C" function v41rt_stage_reload' in wrapper,
            persistent_stage_loop='w17_connected_stage_loop' in host),
        missing_connections=[
            'W16 source-pinned physical stage count/mapping: conditional45 must not be inferred from42 functional operations',
            'replicated full-size stage/rank DUTs with stage-specific ROM weights and persistent actual KV',
            'finite hardware ready/valid stage-hop transport at modeled latency/capacity, no host activation gather/arithmetic',
            'top-level connected stage control with appropriate L0/indexed-layer organization at each physical stage',
            'all40 program/image generation consumes prior RTL activation, never per-layer golden H/PF/SSX',
            'connected current-token compressed-KV producer, not CKV own-row reencode fixture',
            'final norm and vocabulary head RTL paths and complete output/state comparison',
            'model composed measured stages, then contextual SS/FF physical gates'],
        schedule='existing bridge PASS -> PHW6 connected L0 -> current indexed L20 -> connected all40+head',
        launch_allowed=False, adopt=False)

def selftest():
    import copy
    good=template(); assert not validate(good)
    mutations=[('golden_activation_load',True),('golden_current_kv_load',True),
               ('reset',True),('reconstruct_dut',True),('reload_state',True),
               ('activation_from','golden.layer19'),('current_kv_from','fixture.ckv_ownrow')]
    for key,value in mutations:
        bad=copy.deepcopy(good); bad['stages'][20][key]=value; assert validate(bad), key
    bad=copy.deepcopy(good);bad['stages'].pop();assert validate(bad)
    return dict(symbolic_valid_plan=True, rejected_mutants=len(mutations)+1,
                scope='functional-edge validation only; physical mapping/count and stage implementations remain UNBOUND')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args()
    r=audit();r['symbolic_checks']=selftest();r['plan_template']=template()
    if a.plan:r['plan_errors']=validate(json.loads(a.plan.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    if a.plan and r['plan_errors']:raise SystemExit(1)
