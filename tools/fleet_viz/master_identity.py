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
    for proof in config.get('replica_groups', []):
        members = proof['members']
        names = [m['element'] for m in members]
        if not all(n in by_name for n in names):
            continue
        try:
            bodies = [normalized(module_body(repo.read(m['path']), m['module'])) for m in members]
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
    return independent, integration, dict(config=CONFIG, scope='Only explicit verified groups; unlisted identities remain unchanged for further audit', compositions=len(integration),
        alias_rows_removed=sum(len(r['replica_aliases']) for r in aliases.values()),
        groups=[r['identity_evidence'] for r in aliases.values()], errors=errors)
