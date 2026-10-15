"""Proof-backed display grouping; historical rows and integration verdicts remain intact."""
import collections
import copy
import hashlib
import json
import re

CONFIG = 'tools/fleet_viz/master_identity.json'


def module_body(text, name):
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', text or '', flags=re.S)
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b(.*?)\bendmodule\b', text, re.S)
    if not m:
        raise ValueError('missing module ' + name)
    return m.group(1)


def normalized(body):
    return re.sub(r'\s+', '', body)


def physical_identity(repo, member):
    kit, top = member['kit'], member['module']
    spec = json.loads(repo.read(kit + '/spec.json'))
    if spec.get('top') != top:
        raise ValueError('kit top mismatch')
    spec.pop('name', None); spec.pop('top', None); spec.pop('job', None)
    signature = [json.dumps(spec, sort_keys=True)]
    for name in ('floorplan.json', 'clock.sdc', 'signoff.sdc', 'kit.env'):
        text = repo.read(kit + '/' + name)
        if text is None:
            raise ValueError('missing physical identity ' + kit + '/' + name)
        # Only the two declared identifiers may differ. Pin names, coordinates,
        # clocks, periods, params, layers, macros and constraints must all match.
        for old, new in ((kit.rsplit('/', 1)[-1], '__KIT__'), (top, '__TOP__')):
            text = re.sub(r'(?<![A-Za-z0-9_$])' + re.escape(old) + r'(?![A-Za-z0-9_$])', new, text)
        if name.endswith('.json'):
            text = json.dumps(json.loads(text), sort_keys=True)
        signature.append(text)
    return signature


def view_reuse_identity(repo, group, candidates):
    """A pinned reviewed source proof plus the exact existing routed view.

    Re-check RTL alpha-renaming separately below, every transitive source hash,
    original CLOSED job, all 13 exported files, and physical name-only equality.
    No receipt boolean alone grants reuse and no new job PASS is generated.
    """
    reuse = group['view_reuse']
    text = repo.read(reuse['proof'])
    if text is None or hashlib.sha256(text.encode()).hexdigest() != reuse['proof_sha256']:
        raise ValueError('reuse proof missing/changed')
    proof = json.loads(text)
    names = [m['element'] for m in group['members']]
    if proof.get('status') != 'EXACT_IMPLEMENTATION_REUSE' or names != [proof.get('old_master'), proof.get('master')]:
        raise ValueError('reuse master identity mismatch')
    old, new = names
    prior = candidates[0]; best = prior.get('best') or {}
    if (not prior['category'].startswith('closed') or best.get('job') != proof.get('from_job')
            or best.get('tt') != proof.get('TT_setup_ps') or best.get('ff') != proof.get('FF_hold_ps')
            or best.get('drc') != 0 or proof.get('DRC') != 0):
        raise ValueError('reuse lacks the exact original CLOSED job')
    if proof.get('params') != {'LAT': 8} or proof.get('cycles') != 8 or proof.get('clock_roots') != 1:
        raise ValueError('unsupported resolved reuse parameters')
    for path, digest in proof.get('transitive_dependencies_byte_equal', {}).items():
        data = repo.read(path)
        if data is None or hashlib.sha256(data.encode()).hexdigest() != digest:
            raise ValueError('transitive reuse source changed: ' + path)
    renamed = json.loads(repo.read(reuse['new_view'] + '/renamed_from.json'))
    if renamed.get('from_master') != old or renamed.get('master') != new or len(renamed.get('files', {})) != 13:
        raise ValueError('incomplete view rename provenance')
    for name, record in renamed['files'].items():
        a = repo.read(reuse['old_view'] + '/' + record['from'])
        b = repo.read(reuse['new_view'] + '/' + name)
        if (a is None or b is None or hashlib.sha256(a.encode()).hexdigest() != record['from_sha256']
                or hashlib.sha256(b.encode()).hexdigest() != record['sha256']):
            raise ValueError('view bytes changed: ' + name)
        if name.endswith(('.lef', '.lib')) and a.replace(old, '__MASTER__') != b.replace(new, '__MASTER__'):
            raise ValueError('physical geometry/timing differs: ' + name)
    netlist = repo.read(reuse['new_view'] + '/' + new + '.v')
    if netlist is None or hashlib.sha256(netlist.encode()).hexdigest() != proof['routed_netlist_new_sha256']:
        raise ValueError('reused routed netlist changed')


def covered_internal_identity(repo, entry, row, by_name):
    text = repo.read(entry['proof'])
    if text is None or hashlib.sha256(text.encode()).hexdigest() != entry['proof_sha256']:
        raise ValueError('covered-internal evidence missing/changed')
    proof = json.loads(text)
    if proof.get('schema') != 'opentallas.covered_internal_module.v1' or proof.get('element') != row['element']:
        raise ValueError('covered-internal module mismatch')
    sources = proof.get('current_source_sha256') or {}
    if not sources:
        raise ValueError('missing source bindings')
    for path, digest in sources.items():
        data = repo.read(path)
        if data is None or hashlib.sha256(data.encode()).hexdigest() != digest:
            raise ValueError('covered-internal source changed: ' + path)
    runs = proof.get('parent_runs') or []
    parents = {p['master'] for p in runs}
    uses = {p for d in (row.get('dies') or []) for p in d.get('parents', [])}
    if not uses or uses != parents:
        raise ValueError('uncovered current-use parent')
    if {run.get('params', {}).get('W') for run in runs} != {147, 187, 202} or any(run.get('params', {}).get('MUT') != 0 for run in runs):
        raise ValueError('unproven resolved calendar parameters')
    for run in runs:
        parent = by_name.get(run['master'], {})
        if (not parent.get('category', '').startswith('closed')
                or (parent.get('best') or {}).get('job') != run['parent_job']
                or run.get('actual_netlist_modules') != [run['master']]
                or run.get('generic_calendar_cell_instances') != 0
                or run.get('flattened_u_programme_references', 0) < 1
                or run.get('actual_1024x256_SRAM_instances') != 1
                or not re.fullmatch('[0-9a-f]{64}', run.get('netlist_sha256', ''))):
            raise ValueError('missing exact CLOSED flattened-parent evidence')
    return proof


def classify(rows, repo, config=None):
    """Return display masters, integration backlog and an auditable grouping receipt.

    Unknown/stale proofs leave the original row in the independent queue. This
    changes display scope only; it never changes a route or integration verdict.
    """
    if config is None:
        text = repo.read(CONFIG)
        config = json.loads(text) if text else {}
    errors, integration, removed, aliases = [], [], set(), {}
    by_name = {r['element']: r for r in rows}
    for proof in config.get('compositions', []):
        name = proof['element']
        if name not in by_name or by_name[name].get('superseded'):
            continue
        try:
            body = module_body(repo.read(proof['path']), proof['module'])
            digest = hashlib.sha256(normalized(body).encode()).hexdigest()
            if digest != proof['body_sha256']:
                raise ValueError('source body changed')
            if re.search(r'\b(?:always\w*|initial|reg)\b', body):
                raise ValueError('parent has own state/process; not a wires-only composition')
            row = copy.deepcopy(by_name[name])
            row['qualification_scope'] = 'integration composition'
            row['component_category'] = row['category']
            if row['category'].startswith('closed'):
                row['category'] = 'not started (open)'  # component timing is not parent integration
            row['identity_evidence'] = proof
            row['integration_status'] = 'OPEN: child closures do not prove parent pins, routing, clocks or token calendar'
            integration.append(row); removed.add(name)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(dict(element=name, error=str(exc)))
    covered = 0
    for entry in config.get('covered_internal_modules', []):
        name = entry['element']
        if name not in by_name or by_name[name].get('superseded'):
            continue
        try:
            proof = covered_internal_identity(repo, entry, by_name[name], by_name)
            row = copy.deepcopy(by_name[name])
            row['qualification_scope'] = 'covered internal module'
            row['identity_evidence'] = dict(entry, coverage=proof)
            row['integration_status'] = 'Current resolved instances covered inside parent routes; parent/die integration remains OPEN. Other params and new sources unqualified.'
            integration.append(row); removed.add(name); covered += 1
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(dict(element=name, error=str(exc)))
    for proof in config.get('replica_groups', []):
        members = proof['members']
        names = [m['element'] for m in members]
        if not all(n in by_name for n in names):
            continue
        try:
            bodies = []
            for member in members:
                body = module_body(repo.read(member['path']), member['module'])
                for old, new in member.get('local_renames', {}).items():
                    body = re.sub(r'\b' + re.escape(old) + r'\b', new, body)
                bodies.append(normalized(body))
            if proof.get('view_reuse'):
                view_reuse_identity(repo, proof, [by_name[n] for n in names])
                physical = [True for _ in members]
            else:
                physical = [physical_identity(repo, m) for m in members]
            if len(set(bodies)) != 1 or any(p != physical[0] for p in physical[1:]):
                raise ValueError('RTL/parameters/interface/physical contract differs')
            canonical = proof['canonical']
            # Reuse the best existing component verdict, never manufacture PASS.
            candidates = [by_name[n] for n in names]
            chosen = min(candidates, key=lambda r: (not r['category'].startswith('closed'), r['element'] != canonical))
            row = copy.deepcopy(chosen); row['element'] = canonical
            row['replica_records'] = copy.deepcopy(candidates)
            row['identity_evidence'] = proof; row['qualification_scope'] = 'independent master'
            row['replica_aliases'] = [n for n in names if n != canonical]
            row['variants'] = sorted(set(row.get('variants', [])) | set(names) - {canonical})
            for count in ('jobs', 'live', 'failed', 'closed_jobs'):
                row[count] = sum(r.get(count, 0) for r in candidates)
            row['dies'] = [d for r in candidates for d in (r.get('dies') or [])]
            aliases[canonical] = row; removed.update(names)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(dict(elements=names, error=str(exc)))
    independent = [r for r in rows if r['element'] not in removed] + list(aliases.values())
    mismatches = []
    for proof in config.get('contract_mismatches', []):
        for index, original in enumerate(independent):
            if original['element'] != proof['element'] or (original.get('best') or {}).get('job') != proof['candidate_job']:
                continue
            try:
                body = module_body(repo.read(proof['path']), proof['module'])
                if hashlib.sha256(normalized(body).encode()).hexdigest() != proof['body_sha256']:
                    continue  # current source changed; narrowly pinned warning no longer applies
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(dict(element=proof.get('element'), error=str(exc)))
                continue
            row = copy.deepcopy(original)
            row['candidate_component_record'] = copy.deepcopy(original)
            row['component_category'] = original['category']
            row['category'] = 'not started (open)'
            row['current_contract_warning'] = proof['warning']
            row['identity_evidence'] = proof
            row['purpose'] = proof['warning'] + ' ' + row.get('purpose', '')
            row['gate'] = 'CURRENT-CONTRACT-UNQUALIFIED (candidate component evidence retained)'
            row['best'] = {key: None for key in original['best']}
            independent[index] = row; mismatches.append(proof['element'])
    return independent, integration, dict(config=CONFIG, scope='Only explicit verified groups; unlisted identities remain unchanged for further audit', compositions=len(integration) - covered, covered_internal_modules=covered, contract_mismatches=mismatches,
        alias_rows_removed=sum(len(r['replica_aliases']) for r in aliases.values()),
        groups=[r['identity_evidence'] for r in aliases.values()], errors=errors)
