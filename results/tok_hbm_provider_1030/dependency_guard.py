"""Require the reviewed canonical source snapshot before fixture compilation."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent


def require_sources(repo,provider_dir,names):
    manifest=json.loads((HERE/'source_dependencies.json').read_text())
    for name in names:
        path=provider_dir/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['provider_files'][name]:
            raise ValueError(f'Provider source mismatch: {path}; expected reviewed {manifest["canonical_RTL_tip"]}, including destination-format guard. Historical734/5fe snapshots are not the current default.')
    for relative,expected in manifest['shared_repo_files'].items():
        if 'cp_provider' not in ' '.join(names) and ('ot_hgi_dma_back_cp_collar' in relative or 'ot_static_cmd_target' in relative):
            continue
        path=repo/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Shared native source mismatch: {path}; expected reviewed {manifest["canonical_RTL_tip"]}')
    return manifest
