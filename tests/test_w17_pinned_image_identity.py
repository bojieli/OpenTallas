"""Offline image binding checks and independent identity corruptions."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_w17_pinned_image_identity as identity


def test_exact_mapping_does_not_admit_execution():
    result = identity.check(ROOT / identity.EVIDENCE)
    assert result['raw_config_bytes'] == 2341
    assert not result['relink_admitted'] and not result['runtime_admitted']
    assert not result['local_layer_bytes_freshly_hashed']


@pytest.mark.parametrize('mutation', ['history', 'layer_order', 'manifest', 'default', 'blob_hash'])
def test_corrupt_identity_rejected(tmp_path, mutation):
    d = tmp_path / 'evidence'
    shutil.copytree(ROOT / identity.EVIDENCE, d)
    names = dict(history='local_config.raw.json', layer_order='local_inspect.json',
                 manifest='remote_manifest.raw.json', default='local_inspect.json',
                 blob_hash='remote_blob_hashes.json')
    p = d / names[mutation]
    data = json.loads(p.read_bytes())
    if mutation == 'history':
        data['history'][0]['created_by'] += ' changed'
    elif mutation == 'layer_order':
        data[0]['RootFS']['Layers'].reverse()
    elif mutation == 'manifest':
        data['config']['digest'] = 'sha256:' + '0' * 64
    elif mutation == 'default':
        data[0]['Config']['Entrypoint'] = ['/different-entrypoint']
    else:
        data['checked'][2]['actual_sha256'] = '0' * 64
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        identity.check(d)
