"""Explicit repository-Git replay of the measured pre-VM-audit CP fixture.

This does not select an old source for the current VM completion fixture. It
reproduces the separately recorded packet-only dd491 proof without scratch or
network dependencies and without silently disabling the current native audit.
"""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent


def export_packet_snapshot(repo,out):
    manifest=json.loads((HERE/'source_dependencies.json').read_text())
    pin=manifest['canonical_RTL_tip']
    snapshot=out/('historical_sources_'+pin)
    paths={manifest['canonical_directory']+name:h for name,h in manifest['provider_files'].items()}
    paths.update(manifest['shared_repo_files'])
    for relative,expected in paths.items():
        try:
            raw=subprocess.check_output(['git','show',pin+':'+relative],cwd=repo,stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Historical replay requires repository Git object {pin}:{relative}; no external scratch source or automatic fetch is used')from e
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError(f'pinned historical source mismatch: {relative}')
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    (snapshot/'replay_scope.json').write_text(json.dumps(dict(source_commit=pin,scope='historical packet-only legalU32 CP replay; no native VMcompletion audit or LOADdone claim',source_files=len(paths)),indent=1)+'\n')
    return snapshot,manifest
