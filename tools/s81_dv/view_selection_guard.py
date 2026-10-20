"""Prospective S81 release admission, independent of LEF discovery and CLOSED labels.

No real master is qualified by this module's existence. ROOT must author the typed,
source-bound approval and native evidence manifest; tests use synthetic fixtures.
"""
import hashlib
import json
import math
import re


class SelectionRefused(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise SelectionRefused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def content_sha(obj):
    return sha(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def finite_tree(obj):
    if isinstance(obj, float):
        require(math.isfinite(obj), 'nonfinite evidence')
    elif isinstance(obj, dict):
        for v in obj.values():
            finite_tree(v)
    elif isinstance(obj, list):
        for v in obj:
            finite_tree(v)


def artifact(a, read):
    require(isinstance(a, dict) and set(a) == {'commit', 'path', 'sha256'}, 'artifact identity fields')
    require(re.fullmatch(r'[0-9a-f]{40}', a['commit']) is not None, 'artifact commit must be immutable')
    require(isinstance(a['path'], str) and a['path'] and not a['path'].startswith('/') and '..' not in a['path'].split('/'), 'artifact path')
    require(re.fullmatch(r'[0-9a-f]{64}', a['sha256']) is not None, 'artifact SHA256')
    raw = read(a['commit'], a['path'])
    require(isinstance(raw, bytes) and sha(raw) == a['sha256'], 'artifact bytes mismatch: ' + a['path'])
    return raw


def same_sources(evidence, entry):
    require(evidence.get('artifacts') == entry['artifacts'], 'native evidence artifact bindings mismatch')
    require(evidence.get('contracts') == entry['contracts'], 'native evidence contract bindings mismatch')


def native_evidence(entry, read):
    kind = entry.get('proof_kind')
    mandatory = {'lef', 'lib_tt', 'lib_ff', 'lib_ss', 'source_inventory', 'params', 'ports', 'clock_age_contract'}
    if kind == 'routed_hardmacro':
        mandatory |= {'route_odb', 'route_v', 'route_spef', 'route_sdc', 'abstract', 'insertion'}
    elif kind in ('sram_model', 'primitive_model'):
        mandatory |= {'model', 'pg_pin_calibration'}
    else:
        raise SelectionRefused('unknown proof kind')
    require(mandatory <= set(entry.get('artifacts', {})), 'incomplete typed artifact inventory')
    require(set(entry.get('contracts', {})) == {'source', 'params', 'ports', 'clock_age'}, 'contract inventory')
    for a in entry['artifacts'].values():
        artifact(a, read)
    for a in entry['contracts'].values():
        artifact(a, read)
    ev = json.loads(artifact(entry['native_receipt'], read))
    finite_tree(ev)
    require(ev.get('schema') == 'opentallas.s81_native_qualification.v1', 'native receipt schema')
    require(ev.get('proof_kind') == kind and ev.get('master') == entry['master'], 'native receipt type/master')
    require(ev.get('status') == 'PASS' and ev.get('complete') is True, 'native receipt not complete PASS')
    same_sources(ev, entry)
    checks = ev.get('checks', {})
    required = {'pg', 'grid', 'reach', 'roles', 'clock', 'phase', 'ports', 'parameters', 'source', 'age'}
    require(set(checks) == required, 'native check coverage')
    for k, c in checks.items():
        require(c.get('complete') is True and c.get('status') == 'PASS', 'incomplete native check: ' + k)
        require(type(c.get('checked')) is int and c['checked'] > 0, 'empty native check: ' + k)
        require(type(c.get('errors')) is int and c['errors'] == 0, 'native check errors: ' + k)
    require(set(ev.get('corners', {})) == {'tt', 'ff', 'ss'}, 'all corner evidence required')
    for c, data in ev['corners'].items():
        require(data.get('complete') is True and data.get('status') == 'PASS', 'corner not PASS: ' + c)
        for key in ('clock_rise_ps', 'clock_fall_ps', 'clock_rise_spread_ps', 'clock_fall_spread_ps'):
            require(type(data.get(key)) in (int, float) and math.isfinite(data[key]), 'finite both-edge clock metric: ' + key)
    return ev


def qualify(manifest, holds, approval_identity, context, selected, read):
    """Return receipt only when exact selected macros and ROOT context are admitted.

    selected: master -> {commit, directory}, after every explicit landing override.
    context: exact SHA256 of every source GEN input; supplied from actual files.
    read: read immutable git blob bytes by exact commit and path.
    """
    finite_tree(manifest); finite_tree(holds)
    require(manifest.get('schema') == 'opentallas.s81_release_views.v1', 'manifest schema')
    require(holds.get('schema') == 'opentallas.s81_component_holds.v1', 'hold schema')
    require(manifest.get('context') == context and context, 'source GEN context mismatch')
    require(manifest.get('holds_sha256') == content_sha(holds), 'hold inventory mismatch')
    approval = json.loads(artifact(approval_identity, read)); finite_tree(approval)
    require(approval.get('schema') == 'opentallas.s81_root_selection_approval.v1', 'ROOT receipt schema')
    require(approval.get('owner') == 'ROOT' and approval.get('status') == 'APPROVED', 'ROOT approval required')
    require(approval.get('scope') == 'exact-source-view-selection', 'ROOT approval scope')
    require(approval.get('manifest_sha256') == content_sha(manifest) and approval.get('context') == context, 'ROOT approval source/manifest mismatch')
    entries = manifest.get('masters', {})
    require(set(entries) == set(selected), 'selected master manifest coverage mismatch')
    denials = holds.get('denials'); require(isinstance(denials, list), 'hold denials required')
    for master, chosen in selected.items():
        ent = entries[master]
        require(ent.get('master') == master and ent.get('selection') == chosen, 'selected master/source identity mismatch')
        require(re.fullmatch(r'[0-9a-f]{40}', chosen.get('commit', '')) is not None, 'selected source must be immutable')
        identities = list(ent.get('artifacts', {}).values()) + list(ent.get('contracts', {}).values())
        for denial in denials:
            require(denial.get('kind') in ('artifact_sha256', 'source_commit'), 'unknown hold type')
            require(isinstance(denial.get('reason'), str) and denial['reason'], 'hold reason required')
            if denial['kind'] == 'artifact_sha256':
                require(re.fullmatch(r'[0-9a-f]{64}', denial.get('sha256', '')) is not None, 'hold artifact identity')
            else:
                require(isinstance(denial.get('master'), str) and denial['master'] and re.fullmatch(r'[0-9a-f]{40}', denial.get('commit', '')) is not None, 'hold source identity')
            if denial['kind'] == 'artifact_sha256':
                require(not any(a.get('sha256') == denial.get('sha256') for a in identities), 'held artifact selected: ' + master)
            else:
                require(not (denial.get('master') == master and denial.get('commit') == chosen['commit']), 'held source selected: ' + master)
        native_evidence(ent, read)
        for role in ('lef', 'lib_tt', 'lib_ff', 'lib_ss'):
            a = ent['artifacts'][role]
            require(a['commit'] == chosen['commit'] and a['path'] == chosen['directory'] + '/' + master + ({'lef': '.lef', 'lib_tt': '_tt.lib', 'lib_ff': '_ff.lib', 'lib_ss': '_ss.lib'}[role]), 'selected view artifact identity mismatch')
    return dict(status='ROOT_APPROVED_EXACT_SELECTION_ONLY', manifest_sha256=content_sha(manifest), holds_sha256=content_sha(holds), root_approval=approval_identity, context=context, masters=sorted(selected), note='Selection admission only; no parent die timing or physical verdict implied')
