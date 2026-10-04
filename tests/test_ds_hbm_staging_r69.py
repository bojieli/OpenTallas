import fcntl
import hashlib
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ds_hbm_staging_r69 as s

def test_bounded_digest(tmp_path):
    p = tmp_path / 'payload'; p.write_bytes(b'x' * (1024 * 1024 + 17))
    assert s.digest(p) == {'bytes': p.stat().st_size,
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def test_exclusive_writer_refuses(tmp_path):
    p = tmp_path / 'payload'; p.write_bytes(b'a')
    with p.open('rb') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError): s.digest(p)

def test_wrong_digest_refuses():
    with pytest.raises(ValueError): s.require({'bytes': 3, 'sha256': 'wrong'}, 'right', 'a')

@pytest.mark.parametrize('name', ['../outside', '/absolute'])
def test_catalog_escape_refuses(tmp_path, name):
    with pytest.raises(ValueError): s.rooted(tmp_path, name)

def test_union_counts_shared_bytes_once():
    records = {}; value = {'bytes': 13, 'sha256': 'exact'}
    s.union_record(records, 'same', value, 'source')
    s.union_record(records, 'same', value, 'metadata')
    assert sum(x['bytes'] for x in records.values()) == 13
    assert records['same']['roles'] == ['source', 'metadata']

def test_identity_conflict_refuses():
    records = {}; s.union_record(records, 'same', {'bytes': 13, 'sha256': 'one'}, 'source')
    with pytest.raises(ValueError):
        s.union_record(records, 'same', {'bytes': 13, 'sha256': 'two'}, 'metadata')

def test_missing_payload_refuses(tmp_path):
    with pytest.raises(FileNotFoundError): s.digest(tmp_path / 'missing')

def test_source_owned_catalog_roles():
    active, archival = s.catalog_entries(s.SEEDS[-1], {'tools/live.py': 'a', 'results/old.json': 'b'})
    assert active == {'tools/live.py': 'a'}
    assert archival == {'results/old.json': 'b'}
    active, archival = s.catalog_entries(s.SEEDS[-2], {'identity': {'path': 'results/actual.json', 'sha256': 'c'}})
    assert active == {'results/actual.json': 'c'} and archival == {}
