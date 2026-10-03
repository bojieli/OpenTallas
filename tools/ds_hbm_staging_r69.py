"""Read-only R68 staging inventory. Never transfers files or grants admission."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

FROZEN = '915558caaa3742e32ab46343fef9c437807a1f28'
MODEL_SHA = 'ae5e031ebbf51413095a5ae6aeee02958ea653ecedcd26ffe38860f12dafcfda'
ORIGINAL_SHA = '19c27a2387310b88249b043ec2319a7a21e2ce2532b55450d7f424870fa82dd8'
R68 = 'results/uarch/ds_hbm_pc01_r68_20261003/'
SEEDS = [
    'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz',
    'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz',
    'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/actual_DeepSeek_homes.json.gz',
    'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/prefix_input_manifest.json.gz',
    'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json',
    'results/uarch/ds_hbm_connected_source_r37_20261002/peer_source_pins.json',
    'results/uarch/ds_hbm_connected_source_r37_20261002/metadata_source_catalog.json',
    'results/uarch/ds_hbm_history_provider_r36_20261002/source_sha256.json',
]

def stamp(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def digest(path):
    path = Path(path)
    with path.open('rb') as f:
        fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
        before = stamp(os.fstat(f.fileno()))
        h = hashlib.sha256()
        while block := f.read(1024 * 1024):
            h.update(block)
        if before != stamp(os.fstat(f.fileno())) or before != stamp(path.stat()):
            raise ValueError('file changed during locked read: ' + str(path))
        return {'bytes': before[2], 'sha256': h.hexdigest()}

def rooted(root, name):
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('metadata escapes pinned root')
    return path

def require(record, expected, name):
    if record['sha256'] != expected or record['bytes'] < 0:
        raise ValueError('source or payload digest mismatch: ' + name)

def union_record(records, key, value, role):
    if key in records and any(records[key][k] != value[k] for k in ('bytes', 'sha256')):
        raise ValueError('conflicting identity: ' + key)
    records.setdefault(key, {**value, 'roles': []})
    if role not in records[key]['roles']:
        records[key]['roles'].append(role)

def catalog_entries(name, catalog):
    active, archival = {}, {}
    for key, value in catalog.items():
        if isinstance(value, str):
            target, expected = key, value
        else:
            target, expected = value.get('path', key), value['sha256']
        # Exact composed_class source checks only tools/ in this R36 ledger.
        if name == SEEDS[-1] and not key.startswith('tools/'):
            archival[target] = expected
        else:
            active[target] = expected
    return active, archival

def inventory(root, original):
    root = Path(root).resolve()
    plan = json.loads((root / (R68 + 'ot-pve1_plan.template.json')).read_text())
    require(digest(root / (R68 + 'model.json')), MODEL_SHA, 'frozen915 model')
    model = json.loads((root / (R68 + 'model.json')).read_text())
    if plan['component_model_sha256'] != MODEL_SHA or plan['source_sha256'] != model['source_sha256']:
        raise ValueError('frozen915 source/model enrollment differs')
    require(digest(root / (R68 + 'immutable_input_index.json')),
            plan['immutable_input_index_sha256'], 'frozen915 input index')
    index = json.loads((root / (R68 + 'immutable_input_index.json')).read_text())
    records = {}
    for name, expected in sorted(plan['source_sha256'].items()):
        record = digest(rooted(root, name)); require(record, expected, name)
        union_record(records, str(root / name), record, 'frozen_source_pin')
    for name, expected in sorted(index['paths'].items()):
        record = digest(name); require(record, expected['sha256'], name)
        if record['bytes'] != expected['bytes']:
            raise ValueError('input size mismatch')
        union_record(records, name, record, 'immutable_array_input')
    metadata = {name: None for name in SEEDS}
    # These three exact source-owned catalogs enroll retained peers/metadata.
    archival = {}
    for name in SEEDS[-3:]:
        catalog = json.loads(rooted(root, name).read_text())
        active, excluded = catalog_entries(name, catalog)
        archival.update(excluded)
        for target, expected in active.items():
            rooted(root, target)
            if target in metadata and metadata[target] not in (None, expected):
                raise ValueError('conflicting catalog identity')
            metadata[target] = expected
    for name in sorted(metadata):
        record = digest(rooted(root, name))
        if metadata[name] is not None:
            require(record, metadata[name], name)
        union_record(records, str(root / name), record, 'constructor_metadata')
    for path in sorted((root / R68).iterdir()):
        if path.is_file():
            union_record(records, str(path), digest(path), 'frozen_r68_record')
    shards = []
    for old in original['selected_shards']:
        item = digest(old['path']); require(item, old['sha256'], old['path'])
        if item['bytes'] != old['bytes']:
            raise ValueError('shard size mismatch')
        union_record(records, old['path'], item, 'released_checkpoint_shard')
        shards.append({'path': old['path'], **item})
    cp = original['checkpoint_index']
    item = digest(cp['path']); require(item, cp['sha256'], cp['path'])
    union_record(records, cp['path'], item, 'released_checkpoint_index')
    manifest_path = root / SEEDS[3]
    import gzip
    manifest = json.loads(gzip.decompress(manifest_path.read_bytes()))
    require(item, manifest['checkpoint_index_sha256'], cp['path'])
    required_disk = model['required_disk_bytes']
    staging = sum(v['bytes'] for v in records.values())
    metadata_extra = sum(v['bytes'] for v in records.values()
                         if v['roles'] == ['constructor_metadata'])
    return dict(schema='DS_R68_STAGING_INVENTORY_R69', frozen_source=FROZEN,
        model_sha256=plan['component_model_sha256'], files=dict(sorted(records.items())),
        constructor_metadata_count=len(metadata), metadata_only_additional_bytes=metadata_extra,
        unique_staging_file_bytes=staging, frozen_run_output_envelope_bytes=required_disk,
        known_staging_plus_run_bytes=staging + required_disk,
        selected_shards=shards, complete_dynamic_dependency_closure=False,
        historical_r36_nonruntime_entries=archival,
        catalog_classification_source='tools/h3_ds_connected_provider_r37.py:composed_class checks only tools/ in R36 ledger; peer and metadata catalogs remain enrolled',
        unpriced=['receiver filesystem block/inode allocation', 'archive plus unpack overlap',
                  'atomic transfer temporary coexistence', 'additional dynamic metadata dependencies',
                  'physical filecache/page-table/kernel exposure', 'protected peer disk/RAM growth'],
        physical_admission=False, remote_transfer=False, constructors=False, numerical=False,
        scope='Known source/catalog/payload staging union only; no runtime guard or reservation change.')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--original-integrity', type=Path, required=True)
    p.add_argument('--out', type=Path)
    p.add_argument('--verify', type=Path)
    a = p.parse_args()
    require(digest(a.original_integrity), ORIGINAL_SHA, 'original local integrity receipt')
    result = inventory(a.source_root, json.loads(a.original_integrity.read_text()))
    if a.verify and result != json.loads(a.verify.read_text()):
        raise ValueError('fresh inventory differs from frozen record')
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('metadata_only_additional_bytes',
        'unique_staging_file_bytes', 'known_staging_plus_run_bytes', 'physical_admission')}))

if __name__ == '__main__':
    main()
