"""Read exact committed metadata snapshots without Git or private worktrees."""
import functools
import hashlib
import io
import json
from pathlib import Path
import tarfile

DIRECTORY = Path(__file__).resolve().parents[1]/'results/uarch/qwen_hbm_provider_portable_r18_20261002'

@functools.lru_cache(maxsize=1)
def validated_snapshot():
    manifest = json.loads((DIRECTORY/'snapshot_manifest.json').read_bytes())
    archive = (DIRECTORY/'source_metadata.tar.gz').read_bytes()
    if hashlib.sha256(archive).hexdigest() != manifest['archive_sha256']:
        raise ValueError('snapshot archive digest mismatch')
    result = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        if {m.name for m in tar.getmembers()} != {x['member'] for x in manifest['entries']}:
            raise ValueError('snapshot member inventory mismatch')
        for entry in manifest['entries']:
            raw = tar.extractfile(entry['member']).read()
            if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('snapshot source digest mismatch')
            result[entry['commit'],entry['path']] = raw
    return result

def snapshot(commit, path):
    return validated_snapshot()[commit,path]
