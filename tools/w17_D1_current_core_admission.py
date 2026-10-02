"""Portable source/cap admission review only. Contains no compiler launcher."""
import argparse
import hashlib
import json
from pathlib import Path
import re

EVIDENCE = Path('results/uarch/w17_D1_current_core_probe_20261002')
BENCH = Path('rtl/test/w17_D1_current_core_probe')
PIN = '4e38326d6f361bc85e660f48c59c355e2bb95274'
GIB = 1024 ** 3
GUARDS = {
    'ot_hdc_fp32_add_lat_CUTS_must_match_LAT',
    'ot_hdc_fp32_mul_lat_CUTS_must_match_LAT',
    'ot_hdc_v41x_vec_LV_must_be_1_to_7',
    'ot_hdc_v41x_vec_lane_ALAT_must_be_3_or_4_and_at_most_MLAT',
}


def strict_int(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError('Invalid integral cap')
    return value


def validate_plan(plan):
    if plan['source_pin'] != PIN or plan['historical_attention_reused']:
        raise ValueError('Wrong source admission')
    c = plan['caps']
    fixed = dict(whole_seconds=2100, frontend_seconds=900, compile_link_seconds=900,
                 runtime_seconds=240, reserve_seconds=60, aggregate_memory_bytes=64*GIB,
                 frontend_AS_bytes=64*GIB, CXX_AS_bytes=3*GIB, runtime_AS_bytes=24*GIB,
                 native_link_AS_bytes=4*GIB, swap_bytes=0, frontend_threads=2,
                 compile_threads=16, runtime_threads=2, output_bytes=4*GIB,
                 file_bytes=512*1024**2, log_bytes=16*1024**2,
                 host_memory_reserve_bytes=32*GIB, host_disk_reserve_bytes=16*GIB,
                 pids_max=48)
    for name, expected in fixed.items():
        if strict_int(c[name], 0, 2**63-1) != expected:
            raise ValueError('Unreviewed cap change: ' + name)
    if sum(c[k] for k in ('frontend_seconds', 'compile_link_seconds', 'runtime_seconds', 'reserve_seconds')) != c['whole_seconds']:
        raise ValueError('Whole budget does not compose')
    if c['compile_threads'] * c['CXX_AS_bytes'] > c['aggregate_memory_bytes'] - 16*GIB:
        raise ValueError('Aggregate compiler budget exceeded')
    for key, mask in [('frontend_affinity',[14,15]), ('runtime_affinity',[14,15]),
                      ('compile_affinity',list(range(8,24)))]:
        for cpu in c[key]:
            strict_int(cpu, 0, 1023)
        if c[key] != mask:
            raise ValueError('Unreviewed CPU mask')
    if c['no_retry'] is not True or c['stop_first_failure'] is not True:
        raise ValueError('Unsafe process policy')
    if plan['model_limits']['causal_service_bound'] != 'BOUND_MISSING':
        raise ValueError('Unsupported causal deadline')
    geometry = plan['source_geometry']
    expected_geometry = dict(FULL_SHAPE=1, SUN=256, SUM=64, CL_DEPTH=512, CL_RELAY=0,
                             ROM_PHW=6, K_MEM=1<<24, WIN_STACK=0,
                             WINDOW_REFILL_CREDITS=1, NPC=32, REFPB=3, CLK_PS=1000, MEM_MODE=0)
    for key, value in expected_geometry.items():
        if type(geometry[key]) is not int or geometry[key] != value:
            raise ValueError('Wrong full source geometry: ' + key)
    command = plan['commands']['frontend']
    if '-DV41_ATT_CUT' not in command or '--timing' not in command:
        raise ValueError('Missing actual cut/timed ABI')
    if '--build' in command or '--exe' in command:
        raise ValueError('Unbounded frontend child compile')
    if plan['whole_token'] or plan['live_changes']:
        raise ValueError('Unsupported runtime scope')
    return True


def inverse_wrapper(text):
    text = re.sub(r'// D1_CURRENT_OBSERVATION_BEGIN\n.*?// D1_CURRENT_OBSERVATION_END\n', '', text, flags=re.S)
    return text.replace('module ot_v41_rt_die_D1_current #(\n    parameter bit SIM_D1=0,',
                        'module ot_v41_rt_die #(')


def ordinary_owner_gaps(inventory):
    return set(inventory['unresolved_potential_references']) - GUARDS


def admission_predicate(values, drop=None):
    # Source truth table, not an event or service completion provider.
    required = ['waited', 'q_gate', 'm0_gate', 'me_ready', 'kv_ok', 'not_kvd_v', 'win_idle']
    return all(values[k] for k in required if k != drop)


def validate_native_order(text):
    loop = text[text.index('while(!ctx->gotFinish())'):]
    if not loop.index('top->eval()') < loop.index('top->eventsPending()') < loop.index('ctx->time(top->nextTimeSlot())'):
        raise ValueError('Changed native event phase')
    if 'if(ctx->gotFinish())break;' not in loop:
        raise ValueError('Finish must precede no-pending diagnosis')
    if 'ctx->threads(1)' not in text or 'ctx->randReset(0)' not in text:
        raise ValueError('Changed native initialization')


def verify_host_tools(root):
    """Optional read-only tool/support hash check; never executes a compiler."""
    e = Path(root) / EVIDENCE
    identity = json.loads((e/'tool_identity.json').read_text())
    for item in identity['tools']:
        data = Path(item['path']).read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Host tool identity mismatch: ' + item['path'])
    vroot = Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050')
    for item in json.loads((e/'verilator_support_inventory.json').read_text()):
        data = (vroot/item['path']).read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Host support ABI mismatch: ' + item['path'])
    return {'status':'READ_ONLY_HOST_TOOL_SUPPORT_HASH_PASS', 'execution_admitted':False}


def verify(root):
    root = Path(root); e = root / EVIDENCE
    load = lambda name: json.loads((e/name).read_text())
    plan = load('plan.json')
    # Validate caps before reading sources or resolving any execution input.
    validate_plan(plan)
    for item in load('artifact_manifest.json'):
        path = root / item['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe source artifact path')
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Source artifact hash mismatch: ' + item['path'])
    manifest = load('source_manifest.json')
    if manifest['source_pin'] != PIN:
        raise ValueError('Manifest source pin mismatch')
    for item in manifest['files']:
        data = (root/item['artifact_path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Pinned source mismatch')
    inventory = load('module_owner_inventory.json')
    if ordinary_owner_gaps(inventory):
        raise ValueError('Unbound ordinary module owner')
    if any(len(v) != 1 for v in inventory['owners'].values()):
        raise ValueError('Ambiguous module owner')
    original = (e/'source_authority/rtl/test/v41_runtime/ot_v41_rt_die.sv').read_text()
    copied = (root/BENCH/'ot_v41_rt_die_D1_current.sv').read_text()
    if inverse_wrapper(copied) != original:
        raise ValueError('Wrapper inverse differs from pinned source')
    block = copied.split('// D1_CURRENT_OBSERVATION_BEGIN')[1].split('// D1_CURRENT_OBSERVATION_END')[0]
    if re.search(r'\bforce\b|dut\.[\w.\[\]:+]+\s*(?:<=|=(?!=))', block):
        raise ValueError('Forced source state')
    validate_native_order((root/BENCH/'native_main.cpp').read_text())
    frontend = plan['commands']['frontend']
    selected = [x for x in frontend if x.endswith(('.sv','.v'))]
    if any(x.endswith('/ot_v41_rt_die.sv') for x in selected):
        raise ValueError('Original wrapper and copied wrapper both selected')
    for source in manifest['die_sources'] + manifest['attention_sources']:
        if source == 'rtl/test/v41_runtime/ot_v41_rt_die.sv':
            continue
        if '{ROOT}/'+str(EVIDENCE)+'/source_authority/'+source not in selected:
            raise ValueError('Omitted supplied source: ' + source)
    go = load('GO_template.json')
    if go['authorized'] is not False or go['runtime_authorized'] is not False:
        raise ValueError('Template cannot authorize a process')
    if go['plan_sha256'] != hashlib.sha256((e/'plan.json').read_bytes()).hexdigest():
        raise ValueError('GO template plan mismatch')
    return dict(status='SOURCE_CLOSURE_NATIVE_ABI_CAP_PROPOSAL_REVIEW_PASS',
                source_files=len(manifest['files']), ordinary_owner_gaps=0,
                parameter_traps_retained=len(GUARDS), elaborated=False,
                compiled=False, runtime_admitted=False, service_bound='BOUND_MISSING')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))
