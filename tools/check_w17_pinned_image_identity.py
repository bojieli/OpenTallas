"""Offline OCI manifest/config identity review. Never admits image execution."""
import hashlib
import json
from pathlib import Path

MANIFEST = 'sha256:760104a7f8f31f970fb3c1ff5bf91cfa0cb79ace21ada4454b157421df715555'
CONFIG = 'sha256:d7d4a8ff33fe73c006535591233e4af478ce5ea2b55ebea30c3dbbf133f6bae2'
EVIDENCE = 'results/rtl/w17_pinned_image_identity_review_20261002'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(directory):
    d = Path(directory)
    def read(name):
        return json.loads((d / name).read_bytes())
    def digest(data):
        return 'sha256:' + hashlib.sha256(data).hexdigest()

    raw = (d / 'remote_manifest.raw.json').read_bytes()
    require(digest(raw) == MANIFEST, 'immutable manifest hash')
    manifest = json.loads(raw)
    require(manifest['schemaVersion'] == 2 and
            manifest['mediaType'] == 'application/vnd.oci.image.manifest.v1+json',
            'OCI manifest type')
    remote = (d / 'remote_config.raw.json').read_bytes()
    local = (d / 'local_config.raw.json').read_bytes()
    require(remote == local and digest(remote) == CONFIG, 'raw config/history bytes')
    require(manifest['config'] == dict(
        mediaType='application/vnd.oci.image.config.v1+json',
        digest=CONFIG, size=len(remote)), 'manifest config binding')
    config = json.loads(remote)
    ids = config['rootfs']['diff_ids']
    require(config['rootfs']['type'] == 'layers' and len(ids) == 3, 'rootfs shape')
    require([x['digest'] for x in manifest['layers']] == ids and
            all(x['mediaType'] == 'application/vnd.oci.image.layer.v1.tar'
                for x in manifest['layers']), 'ordered uncompressed layer identities')
    ri, li = read('remote_inspect.json')[0], read('local_inspect.json')[0]
    require(ri['Id'] == MANIFEST and li['Id'] == CONFIG, 'store-specific image IDs')
    require(ri['Descriptor']['digest'] == MANIFEST and
            ri['Descriptor']['size'] == len(raw), 'remote descriptor')
    for image in (ri, li):
        require(image['RootFS'] == dict(Type='layers', Layers=ids), 'inspect RootFS')
        require(image['Architecture'] == config['architecture'] == 'amd64' and
                image['Os'] == config['os'] == 'linux' and
                image['Created'] == config['created'], 'platform/creation')
    require(ri['Config'] == config['config'], 'remote config presentation')
    defaults = dict(Entrypoint=None, OnBuild=None, User='', Volumes=None, WorkingDir='')
    require(li['Config'] == {**config['config'], **defaults}, 'local default presentation')
    blobs = read('remote_blob_hashes.json')['checked']
    expected = [(MANIFEST, len(raw)), (CONFIG, len(remote))] + [
        (x['digest'], x['size']) for x in manifest['layers']]
    require(len(blobs) == len(expected), 'blob receipt count')
    for actual, (identity, size) in zip(blobs, expected):
        require(actual == dict(digest=identity, bytes=size,
                               actual_sha256=identity[7:], stable=True), 'blob hash receipt')
    layerdb = read('local_layerdb.json')
    require(len(layerdb['layers']) == len(ids), 'layerdb count')
    chain = None
    for diff, layer in zip(ids, layerdb['layers']):
        parent = chain
        chain = diff if chain is None else digest((chain + ' ' + diff).encode())
        require(layer['diff_id'] == diff and layer['chain_id'] == chain and
                layer['parent'] == parent, 'local layerdb chain')
    require(ri['Size'] == sum(size for _, size in expected), 'containerd size accounting')
    require(li['Size'] == layerdb['sum_size'] == sum(
        x['size'] for x in layerdb['layers']), 'overlay2 size accounting')
    require(read('parent_import_failure.snapshot.json')['status'] ==
            'IDENTITY_MISMATCH_NOT_ADMITTED', 'preserved failure authority')
    return dict(status='MANIFEST_CONFIG_IDENTITY_MAPPING_VERIFIED',
                manifest=MANIFEST, config=CONFIG, raw_config_bytes=len(remote),
                diff_ids=ids, relink_admitted=False, runtime_admitted=False,
                local_layer_bytes_freshly_hashed=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(check(parser.parse_args().directory), indent=2))
