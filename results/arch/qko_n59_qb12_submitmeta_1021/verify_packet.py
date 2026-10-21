#!/usr/bin/env python3
"""Verify preserved consumed bytes and excluded submission metadata offline."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def normalized_job(j):
    j = json.loads(json.dumps(j))
    for key in ('owner', 'purpose', 'structural_change'):
        j.pop(key)
    j['source'].pop('branch')
    return j


for tag in ('a', 'b'):
    receipt = json.loads((HERE/(tag+'_receipt.json')).read_text())
    with gzip.open(HERE/(tag+'_source_snapshot.json.gz'), 'rb') as f:
        raw = f.read()
    assert hashlib.sha256(raw).hexdigest() == receipt['snapshot_file_sha256']
    snapshot = json.loads(raw)
    archive = HERE/receipt['consumed_bundle']['path']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['consumed_bundle']['sha256']
    with tarfile.open(archive) as tf:
        assert set(tf.getnames()) == set(snapshot['consumed']['paths'])
        for path, digest in snapshot['consumed']['sha256'].items():
            assert hashlib.sha256(tf.extractfile(path).read()).hexdigest() == digest, path
            # Fresh submission WT's actual kit remains byte-for-byte frozen.
            if path.startswith('physical/ref_tile/qfd_n59_qbank12'+tag+'/'):
                assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    job_path = ROOT/'physical/ref_tile'/('qfd_n59_qbank12'+tag)/'job.json'
    assert str(job_path.relative_to(ROOT)) not in snapshot['consumed']['paths']
    old = json.loads((HERE/(tag+'_original_job.json')).read_text())
    new = json.loads(job_path.read_text())
    assert normalized_job(old) == normalized_job(new)
    assert old['name'] == new['name']
    print(f'QB12{tag.upper()} METADATA_PACKET PASS consumed320 intact; excluded job metadata only; no gate verdict inferred')
