"""Independent, archived source audit. Never imports or invokes a provider/runner.

The R64 reservation is retained. This separates constructor work from future
reservations without granting a smaller admission or measuring Python heap.
"""
import argparse
import ast
import hashlib
import gzip
import math
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'results/uarch/ds_hbm_r64_independent_scope_audit_20261003/inputs'
NEW = ['tools/ds_hbm_checkpointed_prefix_r63.py', 'tools/ds_hbm_checkpoint_execution_r63.py',
       'tools/ds_hbm_checkpoint_boundary_r62.py', 'tools/ds_hbm_output_root_guard_r59.py',
       'tools/ds_hbm_dual_constructor_r64.py', 'tools/ds_hbm_resources_r64.py']


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise ValueError(why)


def read(base, name):
    return json.loads((base / name).read_bytes())


def checked_inputs(base):
    inventory = read(base, 'input_sha256.json')
    actual = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()
              and p.name != 'input_sha256.json'}
    require(actual == set(inventory), 'complete archived input inventory differs')
    for name, wanted in inventory.items():
        p = (base / name).resolve()
        require(p.is_relative_to(base.resolve()) and sha(p) == wanted, 'archived input changed: ' + name)
    snapshots = read(base, 'source_snapshot_sha256.json')
    for name, wanted in snapshots.items():
        require(sha(base / 'sources' / name) == wanted, 'source snapshot mismatch: ' + name)
    for name, wanted in read(base, 'artifact_sha256.json').items():
        require(sha(base / Path(name).name) == wanted, 'original R64 artifact mismatch: ' + name)
    return snapshots


def calls(node):
    return [ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)]


def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def source_scope(base):
    def tree(name):
        return ast.parse((base / 'sources' / name).read_bytes())
    main = function(tree(NEW[0]), 'main')
    gate = next(i for i, n in enumerate(main.body) if 'source_gate' in calls(n))
    ram = next(i for i, n in enumerate(main.body) if 'memory_admission' in calls(n))
    mkdir = next(i for i, n in enumerate(main.body) if 'args.out.mkdir' in calls(n))
    require(gate < ram < mkdir, 'source disk/RAM guards must precede output and constructors')
    pre = next(n for n in ast.walk(main) if isinstance(n, ast.If)
               and ast.unparse(n.test) == 'args.preflight_only')
    pre_calls = calls(pre)
    require('construct' in pre_calls and any(isinstance(n, ast.Return) for n in pre.body),
            'preflight must construct cold objects and return')
    forbidden = {'engine.execute_operation', 'helper.capture_quiescent', 'restore_cold',
                 'helper.execute_remaining', 'helper.project_checkpoint'}
    require(not forbidden.intersection(pre_calls), 'preflight executes numerical/capture/restore work')
    require('helper.data_identity' in pre_calls and 'helper.scope_role_proof' in pre_calls,
            'cold identity/role checks missing')
    wrapper = function(tree('tools/ds_hbm_dual_constructor_r64.py'), 'main')
    names = calls(wrapper)
    require(names.index('enrollment.install') < names.index('original.main'), 'registered loader order')
    shared_tree = tree('tools/h4_hbm_w19_pc10_endpoints.py')
    cls = next(n for n in shared_tree.body if isinstance(n, ast.ClassDef)
               and n.name == 'ProductionSharedFactory')
    init = function(cls, '__init__')
    run = function(cls, '__call__')
    require('self.memories = {}' in ast.unparse(init), 'shared constructor must start empty')
    require('BoundSectorProvider' not in calls(init) and 'inputs' in calls(init),
            'shared raw ports must be lazy; source bytes must still be charged')
    require('BoundSectorProvider' in calls(run), 'actual shared allocation provider absent')
    return dict(disk_RAM_guard_before_output=True, registered_loader_before_runner=True,
                preflight_dual_constructors=True, preflight_returns_before_numerical_loop=True,
                shared_backing_lazy=True, source_bytes_loaded_not_free=True,
                cold_identity_and_role_equal_required=True)


def model_totals(base, name, phase, snapshots):
    model = read(base, name + '_model.json')
    plan = read(base, name + '_plan.json')
    require(model['source_sha256'] == plan['source_sha256'], 'model/plan source identity')
    pins = model['source_sha256']
    require(len(pins) == 50 and all(snapshots.get(p) == h for p, h in pins.items()), 'all50 R64 pins')
    require(plan['numerical_GO'] is False and plan['preflight_only'] is phase,
            'constructor-only versus numerical scope')
    require(model['output_root'] == plan['output_root'], 'output identity')
    require(plan['storage_proof']['sha256'] == sha(base / (name + '_model.json')), 'model proof')
    a = model['R64_additive_costs']
    framing = len(canonical(dict(last_call_stage='preflight_source_contract', stage_status='FAILED',
                                exception_type='AttributeError', reason='', traceback='')))
    lineage = len(canonical(pins)) + sum((base / 'sources' / p).stat().st_size for p in NEW)
    contract = len(canonical({'original_runner_source_sha256': pins['tools/ds_hbm_checkpointed_prefix_r55.py']}))
    text = a['source_and_graph_diagnostic_text_upper_bytes']
    diag = 6 * text + framing
    require(a['lineage_serialized_bytes'] == lineage, 'lineage exact source size')
    require(a['stage_or_terminal_file_upper_bytes'] == diag, 'diagnostic JSON escape/framing charge')
    require(a['checkpoint_extra_bytes'] == 6 * (lineage + contract), 'checkpoint six-copy charge')
    require(a['other_disk_extra_bytes'] == 2 * diag + lineage, 'two durable diagnostic disk charge')
    require(a['RAM_extra_bytes'] == 20 * lineage + 4 * (4 * text + diag), 'unicode/encoded diagnostic RAM charge')
    require(a['original_components_removed'] == 0 and a['original_sector_counts_and_guards_unchanged'],
            'R64 cannot remove inherited reservations')
    ram = model['RAM']; c = ram['components']
    require(sum(c.values()) == ram['coexistence_RAM_peak_bytes'], 'RAM components do not close')
    require(sum(model['checkpoint']['components'].values()) == model['checkpoint_new_bytes'], 'checkpoint components do not close')
    require(model['producer_journal_new_bytes'] + model['continuation_journal_new_bytes'] == model['journal_new_bytes'],
            'both journal reservations must remain')
    disk = sum(model[k] for k in ('journal_new_bytes', 'checkpoint_new_bytes', 'other_new_bytes'))
    return dict(phase=name, output_root=plan['output_root'], required_RAM_bytes=ram['coexistence_RAM_peak_bytes'],
                required_disk_bytes=disk, RAM_components=c,
                disk_components={k:model[k] for k in ('producer_journal_new_bytes', 'continuation_journal_new_bytes',
                                                       'checkpoint_new_bytes', 'other_new_bytes')},
                R64_additive_costs=a, constructor_execution_measured=False, guard_lowered=False)


def initial_aliases(base):
    m = json.loads(gzip.decompress((base / 'actual_manifest.json.gz').read_bytes()))
    v = m['initial_versions']; by_path = {}
    for rec in v:
        key = rec['path']; identity = (rec['sha256'],rec['payload_sha256'],rec['dtype'],tuple(rec['shape']))
        require(key not in by_path or by_path[key] == identity, 'same source path has conflicting payload identity')
        by_path[key] = identity
    recipe = m['checkpoint_initial_embedding']
    require(recipe['planes']==4 and recipe['ranks']==list(range(96)), 'initial embedding exact shape/rank identity')
    return dict(initial_version_records=len(v),unique_readonly_paths=len(by_path),
                readonly_mappings_not_an_owned_raw_sector_allocation=True,
                file_and_payload_hashes_touched_in_every_LockedArray_constructor=True,
                no_mapping_RAM_discount_applied=True,
                embedding_F32_repeat_bytes_per_constructor=4*5120*4,
                embedding_rank_keys_share_one_array_per_constructor=96,
                embedding_source='actual selected BF16 embed.weight row widened toF32 then repeated4planes',
                initial_pre_F32_bytes_per_constructor=4*4,
                actual_checkpoint_payload_read_in_this_audit=False)


def typed_home_audit(base):
    data = json.loads(gzip.decompress((base / 'PC11_19_native_home_slice.json.gz').read_bytes()))
    require(data['native_count'] == 2213 and data['total_home_count'] == 290730, 'full program/home origin')
    rows = []
    widths = {'F32':4, 'U32':4, 'I64':8, 'BOOL':1}
    for op in data['instructions']:
        for tid in sorted({r['template'] for r in op['rank_bindings']}):
            t = data['templates'][tid]; dt = {}; code = {}
            for ins in t['code']:
                name = ins['op']; src = ins['src']; attrs = ins['attrs']
                if name in ('CONST','LOAD'): dtype = attrs['dtype']
                elif name in ('IOTA','F2I'): dtype = 'I64'
                elif name in ('FCMP_EQ','FCMP_LT','FCMP_GT','ASSERT'): dtype = 'BOOL'
                elif name == 'BITCAST_U': dtype = 'U32'
                elif name == 'BITCAST_F' or name == 'I2F' or name in ('FADD','FMUL','FMAX','FMIN','DIV','SQRT','LDEXP'): dtype = 'F32'
                elif name == 'SELECT':
                    require(dt[src[1]] == dt[src[2]], 'SELECT typed arms differ');dtype = dt[src[1]]
                else:
                    require(name in ('AND','OR','XOR','SHL','SHR','IADD','ISUB','IMUL','BROADCAST','RESHAPE',
                                     'SLICE','TAKE','TRANSPOSE','CONCAT'), 'unknown primitive dtype: '+name)
                    dtype = dt[src[0]]
                dt[ins['dst']] = dtype;code[ins['dst']] = ins
            for w in op['writes']:
                result = w['native_result_binding']['result']
                require(result in t['outputs'], 'declared writer output missing')
                reg = t['outputs'][result];elements = math.prod(code[reg]['shape'])
                dtype = dt[reg];payload = elements * widths[dtype]
                ranks = [r['rank'] for r in op['rank_bindings'] if r['template']==tid and not r.get('empty_owned_extent')]
                selected = [h for h in data['homes'] if h['version']==w['version']]
                for rank in ranks:
                    actual = sum(h['word_count']*4 for h in selected if rank in h['rank_group'])
                    require(actual == payload, 'typed writer/home byte extent differs: PC'+str(op['pc'])+' '+result)
                rows.append(dict(PC=op['pc'], family=op['family'],template=tid,version=w['version'],
                                 result=result,dtype=dtype,elements=elements,bytes_per_rank=payload,
                                 ranks_checked=len(ranks),home_indices=w['home_indices']))
    return dict(origin_file_sha256=data['source_sha256'], archived_slice_is_metadata_only=True,
                extraction_scope='original instructions11..19, referenced templates and all declared writer homes',
                producer_payload_read=False, numerical_execution=False, rows=rows)


def audit(base=DEFAULT):
    base = Path(base)
    snapshots = checked_inputs(base)
    phases = [model_totals(base, 'preflight', True, snapshots), model_totals(base, 'runtime', False, snapshots)]
    require([{k:p[k] for k in ('phase','output_root','required_disk_bytes','required_RAM_bytes')} for p in phases]
            == read(base,'summary.json'), 'summary differs')
    continuation = read(base, 'phase_component_evidence/continuation_model.json')
    next_scope = continuation['next_contiguous_scope']
    require([p['PC'] for p in next_scope['per_PC_components']] == list(range(11,20)), 'PC11..19 contiguous coverage')
    requests = sum(p['source_owned_sector_request_component_upper'] for p in next_scope['per_PC_components'])
    require(requests == 3132192 and next_scope['compact_journal_component_bytes'] == requests * 45056,
            'source-owned continuation requests/disk charge')
    scopes = continuation['checkpoint_strategy']['contiguous_scopes']
    require([pc for s in scopes for pc in range(s['first_PC'],s['last_PC']+1)] == list(range(11,2213)),
            'whole2213 continuation scope coverage')
    host = read(base,'pve1_metadata.json')
    host['RAM_margin_bytes'] = host['MemAvailable_bytes'] - phases[0]['required_RAM_bytes']
    host['disk_margin_bytes'] = host['disk_available_bytes'] - phases[0]['required_disk_bytes']
    host['placement_admitted'] = host['RAM_margin_bytes'] >= 0 and host['disk_margin_bytes'] >= 0 and all(host['source_paths'].values())
    require(not host['actual_job_launched'], 'metadata audit must not launch')
    return dict(schema='DS_R64_INDEPENDENT_SCOPE_AND_CONTINUATION_AUDIT_V1',
        verdict='PASS_SOURCE_RESERVATION_AUDIT_NOT_RESOURCE_ADMISSION',
        canonical_source_commit='a4f36c2661cf74145e28ec5b41f99b4a52007739',
        canonical_record_commit='c46c016d6bf19498cf51861c06c89a408349049a',
        source_snapshots=len(snapshots), plan_pins=50, original_artifacts=8,
        source_checks=source_scope(base), phases=phases, typed_output_home_checks=typed_home_audit(base),
        initial_source_aliases=initial_aliases(base), dual_constructor_lifetime=dict(
            simultaneously_retained=['original/bound native+homes+dispatch graphs','producer provider/witness/observed/engine',
                'cold provider/witness/observed/engine','original and cold manifests','constructor lineage/group-plan metadata',
                'immutable image mappings and actual selected embedding arrays','independent expected-output witnesses (verification only)',
                'two journal dictionaries and10 control streams','source-contract identity/serialized diagnostics'],
            constructor_temporaries=['deepcopied declared manifest','lineage regeneration graphs','source hash/decode arrays',
                'gzip/JSON encodings','identity/role canonical trees'],
            lazy_before_operations=['RF/state sector providers','scratch port backing','3072 PC10 shared instances',
                'produced activation/version arrays','checkpoint payload/restored tables'],
            preflight_control_streams_per_constructor=5, preflight_journal_files_expected_per_constructor=11,
            source_bootstrap_and_control_reservation_bytes_per_constructor=131072+5*8192,
            preflight_success_artifacts=['bound_native.json.gz','bound_homes.json.gz','storage_home_binding.json',
                'actual_manifest.json.gz','initialization_provenance.json','receipt.json','checkpoint_boundary_stage.json'],
            all_future_journal_checkpoint_reservations_retained=True, exact_observed_disk_or_heap=None),
        PC11_19=next_scope, complete_continuation_scopes=len(scopes),
        finite_aperture_components=continuation['finite_aperture_components'], prospective_PVE1=host,
        limitations=['No constructor, numeric operator, capture or restore executed in this audit.',
            'R64 holds runtime-sized reservation in preflight; lowering it needs a separately source-priced successor.',
            'Diagnostics formula bounds modeled source/graph text and JSON escaping, not arbitrary exception-string length.',
            'Twenty graph slots and interpreter object prices are conservative source allowances, not observed allocator/SQLite peaks.',
            'PC11..19 journal component uses45056B/request; actual compact density and whole dictionary/index peak not measured.',
            'Physical RF/state/shared aperture is distinct from Python partial-sector object cost;512GB need remains unproved.',
            'Whole history/query/codec state and all provider constructor aliases still need phase composition before continuation admission.',
            'PVE1 paths and capacity require fresh admission after Chandra allocation; no migration, source substitution or payload read.'],
        actual_execution=False, resource_admission=False, physical_credit=False, live_or_original_edits=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,default=DEFAULT)
    p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
    result=canonical(audit(args.inputs))+b'\n'
    if args.verify:require(args.verify.read_bytes()==result,'audit replay differs')
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(result)
    print('PASS_SOURCE_AUDIT_NO_CONSTRUCTORS_NO_ADMISSION')

if __name__=='__main__':main()
