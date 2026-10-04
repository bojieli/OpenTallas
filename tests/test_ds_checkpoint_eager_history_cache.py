import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('cache', Path(__file__).resolve().parents[1] / 'tools/ds_checkpoint_eager_history_cache.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


def fixture():
    records = [dict(path='/source/history.npy', dtype='F32', kind=1,
                    shape=[524287, 512], file_sha256='f' * 64)]
    inventory = {'/source/history.npy': dict(bytes=524287 * 512 * 4 + 128,
                   dev=1, ino=2, mtime_ns=3, ctime_ns=4, sha256='f' * 64)}
    return dict(history_images=records), inventory


def test_whole_file_read_is_positive_before_history_consumer():
    manifest, inventory = fixture()
    result = cache.eager_history_cache(manifest, inventory, page_bytes=4096)
    assert result['full_eager_filecache_page_upper_bytes'] == 1073741824
    assert result['source_payload_bytes'] == 1073739776
    assert not result['physical_admission']
    assert result['existing_cache_credit_bytes'] == 0


@pytest.mark.parametrize('mutation', ['missing', 'hash', 'short', 'stamp', 'shape', 'dtype'])
def test_incomplete_or_changed_source_refused(mutation):
    manifest, inventory = fixture()
    row = inventory['/source/history.npy']
    if mutation == 'missing': inventory.clear()
    if mutation == 'hash': row['sha256'] = 'a' * 64
    if mutation == 'short': row['bytes'] -= 128
    if mutation == 'stamp': del row['ctime_ns']
    if mutation == 'shape': manifest['history_images'][0]['shape'][1] = 128
    if mutation == 'dtype': manifest['history_images'][0]['dtype'] = 'BF16'
    with pytest.raises(ValueError): cache.eager_history_cache(manifest, inventory, page_bytes=4096)


def test_alias_requires_same_inode_and_complete_stamp():
    manifest, inventory = fixture()
    other = copy.deepcopy(manifest['history_images'][0]); other['path'] = '/source/alias.npy'
    manifest['history_images'].append(other)
    inventory[other['path']] = copy.deepcopy(inventory['/source/history.npy'])
    one = cache.eager_history_cache(manifest, inventory, page_bytes=4096)
    assert one['unique_file_inodes'] == 1
    inventory[other['path']]['ino'] = 5
    two = cache.eager_history_cache(manifest, inventory, page_bytes=4096)
    assert two['full_eager_filecache_page_upper_bytes'] == 2 * one['full_eager_filecache_page_upper_bytes']
    inventory[other['path']]['ino'] = 2
    inventory[other['path']]['mtime_ns'] += 1
    with pytest.raises(ValueError): cache.eager_history_cache(manifest, inventory, page_bytes=4096)


@pytest.mark.parametrize('page', [0, -1, 3, None])
def test_page_size_must_be_enrolled(page):
    manifest, inventory = fixture()
    with pytest.raises(ValueError): cache.eager_history_cache(manifest, inventory, page_bytes=page)
