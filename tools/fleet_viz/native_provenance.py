"""Source-bound operation -> elaborated RTL -> routed leaf -> die qualification.

No status/category, path glob, or old numerical PASS proves an edge. Missing
receipts fail explicitly. Each artifact is pinned by immutable git commit+SHA256.
The operation gate is replayed from its pinned source against its real program
and binding manifest; its result alone never proves physical release.
"""
import collections
import gzip
import hashlib
import json
import math
import pathlib
import re
import subprocess
import tempfile
import threading
import time
import types

INDEX = 'results/arch/native_lifecycle_1014/index.json'
EXTERNAL = {'phy', 'off_chip_signal', 'off_chip_memory', 'interdie_wire', 'network_wire'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


class GitReader:
    def __init__(self, repo):
        self.repo = str(repo)
        self.cache = {}

    def git(self, *args):
        return subprocess.run(['git', '-C', self.repo, *args], capture_output=True,
                              check=True, timeout=20).stdout

    def read(self, ref):
        commit, path, pin = ref.get('commit', ''), ref.get('path', ''), ref.get('sha256', '')
        if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[0-9a-f]{64}', pin):
            raise ValueError('ARTIFACT_PROVENANCE_WEAK: immutable commit and SHA256 required')
        if not path or pathlib.PurePosixPath(path).is_absolute() or '..' in pathlib.PurePosixPath(path).parts:
            raise ValueError('ARTIFACT_PATH_INVALID')
        key = (commit, path)
        if key not in self.cache:
            self.cache[key] = self.git('show', commit + ':' + path)
        data = self.cache[key]
        if digest(data) != pin:
            raise ValueError('ARTIFACT_HASH_MISMATCH:' + path)
        return data


def load(reader, ref):
    return json.loads(reader.read(ref))


def error(edge, reason, **fields):
    return dict(edge=edge, reason=reason, **fields)


def replay_program(reader, gate_code, item):
    """Replay native_operation_coverage.py, materialising only pinned dependencies."""
    manifest = load(reader, item['bindings'])
    program = reader.read(item['program'])
    with tempfile.TemporaryDirectory(prefix='native-lifecycle-') as td:
        root = pathlib.Path(td)
        pp = root / ('program.json' if item['program']['path'].endswith('.json') else 'program.hex')
        pp.write_bytes(program)
        elab = manifest.get('elaboration') or {}
        dependencies = dict(elab.get('source_sha256') or {})
        if elab.get('netlist'):
            dependencies[elab['netlist']] = elab.get('netlist_sha256')
        for path, pin in dependencies.items():
            data = reader.read(dict(commit=item['bindings']['commit'], path=path, sha256=pin))
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        mod = types.ModuleType('pinned_native_operation_coverage')
        exec(compile(gate_code, 'pinned_native_operation_coverage.py', 'exec'), mod.__dict__)
        report = mod.audit(root, pp, manifest)
    return report, manifest


def qualify(reader, spec, token):
    defects, rows = [], []
    programs = spec.get('programs') or []
    if not programs:
        defects.append(error('token->program', 'CURRENT_PROGRAM_INVENTORY_MISSING'))
    try:
        inventory = load(reader, spec['program_inventory'])
        wanted = {p['id']: p['sha256'] for p in inventory['programs']}
        actual = {p['id']: p['program']['sha256'] for p in programs}
        if not wanted or wanted != actual or len(wanted) != len(inventory['programs']):
            defects.append(error('token->program', 'EMITTED_PROGRAM_INVENTORY_DIFFERS'))
    except (KeyError, ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError) as exc:
        defects.append(error('token->program', 'EMITTED_PROGRAM_INVENTORY_UNPROVEN:' + str(exc)))
    try:
        gate_code = reader.read(spec['operation_gate']).decode()
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        gate_code = None
        defects.append(error('program->elaboration', 'OPERATION_GATE_UNAVAILABLE:' + str(exc)))
    all_ids, physical = set(), spec.get('physical_bindings') or {}
    for item in programs:
        pid = item.get('id')
        if not pid or pid in all_ids:
            defects.append(error('token->program', 'PROGRAM_ID_MISSING_OR_DUPLICATE', program=pid))
        all_ids.add(pid)
        try:
            if gate_code is None:
                raise ValueError('pinned operation gate missing')
            report, binding = replay_program(reader, gate_code, item)
        except (KeyError, ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError) as exc:
            defects.append(error('program->elaboration', 'PROGRAM_AUDIT_UNAVAILABLE:' + str(exc), program=pid))
            continue
        for issue in report.get('errors', []):
            defects.append(error('program->elaboration', issue, program=pid))
        for name, component in binding.get('components', {}).items():
            if component.get('implementation') in ('rtl', 'macro'):
                continue
            if component.get('role') == 'expected_observer' and component.get('drives_dut') is False:
                continue
            exception = (spec.get('external_models') or {}).get(name)
            if (component.get('role') not in EXTERNAL or not exception
                    or exception.get('boundary_kind') not in EXTERNAL
                    or not exception.get('boundary_ports')
                    or not exception.get('scope')
                    or exception.get('supplies_internal_compute') is not False):
                defects.append(error('component->external_boundary', 'EXTERNAL_MODEL_EXCEPTION_UNPROVEN', component=name, program=pid))
        for op in report['operations']:
            oid = str(pid) + ':' + op['id']
            issues = [error('operation->elaborated_RTL', r) for r in op['reasons']]
            instance = op.get('instance')
            link = physical.get(instance)
            if link is None:
                issues.append(error('elaborated_RTL->routed_leaf', 'INSTANCE_HAS_NO_PHYSICAL_BINDING', instance=instance))
            else:
                issues += physical_chain(reader, link, binding, instance)
            rows.append(dict(id=oid, program=pid, operation_id=op['id'], opcode=op['opcode'],
                             instruction_sha256=op['instruction_sha256'], instance=instance,
                             native_operation_covered=op['native_operation_covered'],
                             native_qualified=not issues and not report['errors'], defects=issues,
                             leaf=link.get('master') if link else None))
    # Historical complete-operation receipts provide exact failing operations
    # even before their real replay inputs/elaboration have been published.
    # This path is deliberately incapable of qualification; it is evidence of
    # gaps, never a substitute for the program/elaboration/physical join above.
    for ref in spec.get('failure_operation_audits', []):
        try:
            raw = reader.read(ref)
            doc = json.loads(gzip.decompress(raw) if ref['path'].endswith('.gz') else raw)
            reports = doc.get('programs', [])
            if not reports:
                raise ValueError('operation audit has no emitted program receipts')
            for report in reports:
                pid = str(report.get('stage')) + ':rank' + str(report.get('rank'))
                for issue in report.get('errors', []):
                    defects.append(error('program->elaboration', issue, program=pid))
                for op in report.get('operations', []):
                    issues = [error('program->elaboration', 'PROGRAM_REPLAY_INPUTS_UNAVAILABLE')]
                    issues += [error('operation->elaborated_RTL', why) for why in op.get('reasons', [])]
                    if not op.get('instruction_sha256') or not report.get('program_sha256'):
                        issues.append(error('program->operation', 'INSTRUCTION_SOURCE_PIN_MISSING'))
                    issues.append(error('elaborated_RTL->routed_leaf', 'INSTANCE_HAS_NO_PROVEN_PHYSICAL_BINDING', instance=op.get('instance')))
                    rows.append(dict(id=pid+':'+str(op.get('id')), program=pid, operation_id=op.get('id'),
                                     opcode=op.get('opcode'), instruction_sha256=op.get('instruction_sha256'),
                                     program_sha256=report.get('program_sha256'), instance=op.get('instance'),
                                     native_operation_covered=False, native_qualified=False, defects=issues,
                                     evidence=ref, scope='FAILING_HISTORICAL_OPERATION_RECEIPT'))
            defects.append(error('program->elaboration', 'FULL_NATIVE_REPLAY_INPUTS_NOT_PUBLISHED'))
        except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
            defects.append(error('program->operation', 'OPERATION_AUDIT_SOURCE_INVALID:'+str(exc)))
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows):
        defects.append(error('program->operation', 'DUPLICATE_OPERATION_ID'))
    nodes = {}
    mapped = set()
    mapping = spec.get('node_operations') or {}
    token_ids = {n['id'] for n in token.get('nodes', [])}
    if not token_ids:
        defects.append(error('token->program', 'TOKEN_LIFECYCLE_EMPTY'))
    for node in token.get('nodes', []):
        ids = mapping.get(node['id']) or []
        issues = []
        if not ids:
            issues.append(error('token_node->operation', 'TOKEN_NODE_NOT_BOUND_TO_CURRENT_PROGRAM'))
        for oid in ids:
            if oid not in by_id:
                issues.append(error('token_node->operation', 'OPERATION_NODE_DANGLING', operation=oid))
            else:
                if oid in mapped:
                    issues.append(error('token_node->operation', 'OPERATION_MULTIPLY_MAPPED', operation=oid))
                mapped.add(oid)
        bound = [by_id[oid] for oid in ids if oid in by_id]
        nodes[node['id']] = dict(operations=ids, native_qualified=bool(bound) and not issues and all(r['native_qualified'] for r in bound),
                                 defects=issues + [dict(d, operation=r['id']) for r in bound for d in r['defects']])
    for nid in set(mapping) - token_ids:
        defects.append(error('token_node->operation', 'TOKEN_NODE_DANGLING', node=nid))
    for oid in sorted(set(by_id) - mapped):
        defects.append(error('operation->token_node', 'EMITTED_OPERATION_NOT_ON_TOKEN_LIFECYCLE', operation=oid))
    # A stale token lifecycle cannot become native-green by retaining a subset of its nodes.
    try:
        expected = reader.read(spec['token_graph'])
        if json.loads(expected) != token:
            defects.append(error('token->program', 'TOKEN_GRAPH_DIFFERS_FROM_PINNED_LIFECYCLE'))
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        defects.append(error('token->program', 'TOKEN_GRAPH_SOURCE_UNPROVEN:' + str(exc)))
    try:
        schedule = load(reader, spec['schedule'])
        expected_programs = {p['id']: p['program']['sha256'] for p in programs}
        if (schedule.get('program_sha256') != expected_programs or schedule.get('unplanned_stalls') != 0
                or schedule.get('exact_timeline') is not True or schedule.get('all_native_producers') is not True
                or schedule.get('runtime_backpressure') is not False):
            defects.append(error('operation->static_schedule', 'STATIC_NATIVE_TIMELINE_NOT_PROVEN'))
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        defects.append(error('operation->static_schedule', 'STATIC_SCHEDULE_RECEIPT_MISSING:' + str(exc)))
    all_errors = defects + [dict(d, operation=r['id']) for r in rows for d in r['defects']] + [dict(d, node=n) for n, r in nodes.items() for d in r['defects'] if d.get('edge') == 'token_node->operation']
    counts = collections.Counter(d['edge'] for d in all_errors)
    return dict(schema='opentallas.native_lifecycle.v1', design=spec.get('design'),
                native_qualified=bool(rows and nodes) and not all_errors,
                historical_scope='NUMERICAL_OR_PRICED_TOKEN_PATH_ONLY',
                operations=rows, nodes=nodes, defects=defects,
                summary=dict(programs=len(programs), operations=len(rows), token_nodes=len(nodes),
                             native_operations=sum(r['native_qualified'] for r in rows), defects=len(all_errors), missing_edges=dict(counts)))


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def physical_chain(reader, link, binding, instance):
    issues = []
    try:
        route = load(reader, link['route'])
        target_sources = (binding.get('elaboration') or {}).get('source_sha256') or {}
        actual_sources = route.get('rtl_sha256') or {}
        elab = binding.get('elaboration') or {}
        netlist = load(reader, dict(commit=link['target_commit'], path=elab['netlist'], sha256=elab['netlist_sha256']))
        module = netlist['modules'][elab['top']]
        parts = instance.split('/')
        if parts[0] != elab['top']:
            raise ValueError('instance outside elaborated top')
        for part in parts[1:]:
            module = netlist['modules'][module['cells'][part]['type']]
        module_pin = digest(json.dumps(module, sort_keys=True, separators=(',', ':')).encode())
        if route.get('elaborated_module_sha256') != module_pin:
            issues.append(error('elaborated_RTL->routed_leaf', 'ROUTE_ELABORATED_MODULE_MISMATCH'))
        native = route.get('native_boundary') or {}
        if native.get('reference') != 'phi_minus_R':
            issues.append(error('routed_leaf->native_boundary', 'NATIVE_CLOCK_REFERENCE_UNPROVEN'))
        for key, limit in [('launch_ps', 220), ('capture_ps', 190), ('spread_ps', 80)]:
            if not number(native.get(key)) or native[key] > limit:
                issues.append(error('routed_leaf->native_boundary', 'NATIVE_BOUNDARY_MISSING_OR_FAIL', quantity=key))
        if not actual_sources or any(target_sources.get(p) != h for p, h in actual_sources.items()):
            issues.append(error('elaborated_RTL->routed_leaf', 'ROUTE_RTL_SOURCE_STALE_OR_UNPROVEN'))
        if route.get('master') != link['master'] or route.get('status') != 'CLOSED':
            issues.append(error('elaborated_RTL->routed_leaf', 'ROUTED_MASTER_NOT_CLOSED_OR_MISMATCHED'))
        if (not number(route.get('tt_setup_ps')) or route['tt_setup_ps'] < 0
                or not number(route.get('ff_hold_ps')) or route['ff_hold_ps'] < 0
                or route.get('drc') != 0):
            issues.append(error('routed_leaf->TT_FF_DRC', 'LEAF_SIGNOFF_MISSING_OR_FAIL'))
        files = link.get('files') or {}
        if not all(k in files for k in ('lef', 'tt_lib', 'ff_lib')):
            issues.append(error('routed_leaf->physical_artifacts', 'ROUTED_ARTIFACT_SET_INCOMPLETE'))
        for name, ref in files.items():
            reader.read(ref)
            if (route.get('artifact_sha256') or {}).get(name) != ref['sha256']:
                issues.append(error('routed_leaf->physical_artifacts', 'ROUTE_ARTIFACT_HASH_MISMATCH', artifact=name))
        contract = load(reader, link['contract'])
        slot = (contract.get('slots') or {}).get(link['slot'])
        if not slot or slot.get('master') != link['master'] or slot.get('artifact_sha256') != route.get('artifact_sha256'):
            issues.append(error('routed_leaf->die_contract', 'CONTRACT_SLOT_OR_VIEW_HASH_MISMATCH'))
        db = load(reader, link['die_bind'])
        master = (db.get('masters') or {}).get(link['master'])
        if db.get('verdict') != 'PASS' or not master or master.get('verdict') != 'PASS' or not master.get('instances'):
            issues.append(error('die_contract->real_die_binding', 'ACTUAL_DIE_PORT_BIND_FAIL_OR_MISSING_MASTER'))
        die = reader.read(link['die_netlist'])
        if db.get('die_netlist_sha256') != digest(die) or db.get('contract_sha256') != link['contract']['sha256']:
            issues.append(error('die_contract->real_die_binding', 'DIE_BIND_PROVENANCE_MISMATCH'))
        grt = load(reader, link['grt'])
        if (grt.get('overflow') != 0 or grt.get('die_netlist_sha256') != digest(die)
                or grt.get('contract_sha256') != link['contract']['sha256']
                or (grt.get('view_sha256_by_master') or {}).get(link['master']) != route.get('artifact_sha256')):
            issues.append(error('real_die_binding->GRT', 'DIE_GRT_OVERFLOW_OR_SOURCE_MISMATCH'))
        sta = load(reader, link['die_sta'])
        if (sta.get('die_netlist_sha256') != digest(die) or sta.get('grt_sha256') != link['grt']['sha256']
                or not number(sta.get('tt_setup_ps')) or sta['tt_setup_ps'] < 0
                or not number(sta.get('ff_hold_ps')) or sta['ff_hold_ps'] < 0):
            issues.append(error('GRT->die_TT_FF', 'DIE_SIGNOFF_SOURCE_MISMATCH_OR_FAIL'))
    except (KeyError, ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError) as exc:
        issues.append(error('physical_chain', 'PHYSICAL_EDGE_RECEIPT_MISSING_OR_INVALID:' + str(exc)))
    return issues


class NativeLifecycle:
    def __init__(self, repo, token_dir, ref='origin/main', period=15):
        self.reader = GitReader(repo)
        self.token_dir = pathlib.Path(token_dir)
        self.ref, self.period = ref, period
        self.lock, self.cache = threading.Lock(), {}

    def api(self, design):
        if not re.fullmatch('[a-z0-9_]+', design or ''):
            return dict(native_qualified=False, defects=[error('lifecycle_manifest', 'INVALID_DESIGN')], nodes={}, operations=[])
        with self.lock:
            try:
                commit = self.reader.git('rev-parse', self.ref).decode().strip()
                key = (commit, design)
                token_file = self.token_dir / 'data' / (design + '.json')
                token = json.loads(token_file.read_text())
                token_pin = digest(token_file.read_bytes())
                hit = self.cache.get(key)
                if hit and hit[0] == token_pin:
                    return hit[1]
                index = json.loads(self.reader.git('show', commit + ':' + INDEX))
                spec = index.get('designs', {}).get(design)
                if spec is None:
                    spec = dict(design=design)
                result = qualify(self.reader, spec, token)
                # The current-gap audit adds actionable owner/reason evidence, never qualification.
                try:
                    audit = load(self.reader, index['current_gap_audit'])
                    result['current_gap_groups'] = [g for g in audit['gap_groups'] if g['die'] in spec.get('dies', [])]
                except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
                    result['gap_audit_error'] = str(exc)
                result['source_commit'] = commit
                self.cache[key] = (token_pin, result)
                self.cache = {k:v for k,v in self.cache.items() if k[0] == commit}
                return result
            except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
                return dict(schema='opentallas.native_lifecycle.v1', design=design, native_qualified=False,
                            historical_scope='NUMERICAL_OR_PRICED_TOKEN_PATH_ONLY', operations=[], nodes={},
                            defects=[error('lifecycle_manifest', 'SOURCE_UNAVAILABLE:' + str(exc))])
