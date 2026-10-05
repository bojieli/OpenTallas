"""Explicit continuation scope contract; no restore, constructor or GO bypass.

Only output stop and host evidence-journal policy move out of data identity.
Physical backing/credits, native bytes, homes, source inputs and retention stay
exact. Peirce's restore must consume this contract explicitly before adoption.
"""
import hashlib
import json
from copy import deepcopy

POLICY_FIELDS = frozenset(('prefix_stop', 'journal_root', 'journal_capacity_bytes'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def architectural_manifest(manifest):
    return {k: deepcopy(v) for k, v in manifest.items() if k not in POLICY_FIELDS}


def transition(old_manifest, new_manifest, old_identity, new_identity, *,
               boundary_pc, storage_projection, source_review):
    """Validate, describe and hash a transition without mutating either producer.

    A positive source-sized storage projection is prerequisite metadata, never
    an OS reservation or a numerical launch grant. Architectural identity cannot
    be substituted by a caller-supplied physical-resource equivalence assertion.
    """
    if type(boundary_pc) is not int or boundary_pc < 0:
        raise ValueError('exact retired boundary required')
    for manifest in (old_manifest, new_manifest):
        if type(manifest.get('prefix_stop')) is not int:
            raise ValueError('explicit output stop required')
        if type(manifest.get('journal_capacity_bytes')) is not int or manifest['journal_capacity_bytes'] <= 0:
            raise ValueError('positive source-sized journal policy required')
        if not isinstance(manifest.get('journal_root'), str) or not manifest['journal_root'].startswith('/'):
            raise ValueError('absolute evidence journal root required')
    if old_manifest['prefix_stop'] < boundary_pc or new_manifest['prefix_stop'] <= boundary_pc:
        raise ValueError('continuation stop must follow certified boundary')
    if new_manifest['prefix_stop'] < old_manifest['prefix_stop']:
        raise ValueError('continuation scope must not shrink')
    if architectural_manifest(old_manifest) != architectural_manifest(new_manifest):
        raise ValueError('exact data/backing/credit/manifest identity required')
    for manifest, identity in ((old_manifest, old_identity), (new_manifest, new_identity)):
        pinned = dict(manifest); pinned.pop('journal_root', None)
        if identity.get('manifest_sha256') != digest(pinned):
            raise ValueError('identity must bind actual declared manifest')
    before = {k: v for k, v in old_identity.items() if k != 'manifest_sha256'}
    after = {k: v for k, v in new_identity.items() if k != 'manifest_sha256'}
    if not before or before != after:
        raise ValueError('exact program/homes/source/retention/generation identity required')
    if not source_review or not source_review.get('source_sha256') or not source_review.get('review_record_sha256'):
        raise ValueError('explicit source-reviewed transition required')
    required = storage_projection.get('required_new_bytes')
    available = storage_projection.get('available_bytes')
    if type(required) is not int or required <= 0 or type(available) is not int or available < required:
        raise ValueError('complete source-sized disk admission required')
    if storage_projection.get('continuation_new_bytes', 0) < new_manifest['journal_capacity_bytes']:
        raise ValueError('projection must include complete new journal policy')
    record = dict(schema='DS_EXPLICIT_CONTINUATION_SCOPE_R51', boundary_pc=boundary_pc,
                  old_identity=deepcopy(old_identity), new_identity=deepcopy(new_identity),
                  architectural_manifest_sha256=digest(architectural_manifest(old_manifest)),
                  old_policy={k: old_manifest[k] for k in sorted(POLICY_FIELDS)},
                  new_policy={k: new_manifest[k] for k in sorted(POLICY_FIELDS)},
                  source_review=deepcopy(source_review), storage_projection=deepcopy(storage_projection),
                  physical_backing_and_credits_changed=False, actual_state_restored=False,
                  constructor_admitted=False, numerical_GO=False, hardware_qualified=False)
    record['transition_sha256'] = digest(record)
    return record
