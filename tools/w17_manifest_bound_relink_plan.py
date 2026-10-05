"""Additive classic-Docker relink binding; preserves original manifest-only plan."""
import hashlib
import json
from pathlib import Path

import check_w17_pinned_image_identity as identity
import w17_existing_port_relink_plan as original

EVIDENCE = 'results/rtl/w17_manifest_bound_native_relink_20261002'
GO_SCHEMA = 'w17.existing_public_ports.manifest_config_relink_GO.v1'


def build(root):
    verified = identity.check(root / identity.EVIDENCE)
    p = original.build(root)
    old_image = p['image']
    p['image'] = identity.CONFIG
    p['future_container_argv'] = [
        identity.CONFIG if arg == old_image else arg for arg in p['future_container_argv']]
    p['image_binding'] = dict(
        expected_OCI_manifest=identity.MANIFEST,
        expected_config=identity.CONFIG,
        loaded_local_ID=identity.CONFIG,
        raw_config_bytes=verified['raw_config_bytes'],
        ordered_uncompressed_diffIDs=verified['diff_ids'],
        expected_local_store='overlay2',
        immutable_original_plan_sha256='04f0cb920d4e77ee0d6caae09253ed981c302ff6b2bdee70a80b6c3ac8e1013f',
        identity_review_commit='249a15df4e9e2cb25b48c66b402a77968990924f',
        retagging_allowed=False)
    p['prerequisites'] = [
        'fresh independent manifest/config GO; original manifest-only GO is invalid here',
        'live local inspect + raw config SHA + ordered RootFS identity checks before Docker run',
        'all unchanged enrolled native inputs verified before/after compile',
        'fresh local coordinated4GiB/twoCPU admission;60s wall,2MiB log,2GiB output caps',
        'runtime separately admitted only after actual binary/tool/input compile receipt']
    return p


def validate_local_identity(p, image, raw_config, driver):
    """Pure preflight; runtime callers supply freshly read metadata, never aliases."""
    b = p['image_binding']
    if driver != b['expected_local_store'] or image['Id'] != b['loaded_local_ID']:
        raise ValueError('local image ID/store')
    actual = 'sha256:' + hashlib.sha256(raw_config).hexdigest()
    if actual != b['expected_config'] or len(raw_config) != b['raw_config_bytes']:
        raise ValueError('live raw config SHA/size')
    config = json.loads(raw_config)
    if image['RootFS'] != dict(Type='layers', Layers=b['ordered_uncompressed_diffIDs']):
        raise ValueError('live ordered diffIDs')
    if config['rootfs'] != dict(type='layers', diff_ids=b['ordered_uncompressed_diffIDs']):
        raise ValueError('raw config rootfs')
    defaults = dict(Entrypoint=None, OnBuild=None, User='', Volumes=None, WorkingDir='')
    if image['Config'] != {**config['config'], **defaults}:
        raise ValueError('live Config presentation')
    if image['Architecture'] != config['architecture'] or image['Os'] != config['os'] or image['Created'] != config['created']:
        raise ValueError('live platform/history')
    return dict(OCI_manifest=b['expected_OCI_manifest'], config_SHA=actual,
                loaded_local_ID=image['Id'], ordered_diffIDs=image['RootFS']['Layers'],
                config_bytes=len(raw_config), store=driver, retagged=False)
