"""Enforce explicit HBM adoption holds without changing generic route verdicts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'results/arch/hbm_die_v15/native_view_admission.json'


def require_admitted(master, view):
    """Called by HBM view binding; unknown historical masters retain their labels."""
    rec = json.loads(MANIFEST.read_text())['masters'].get(master)
    if rec is None:
        return
    if not rec['adopt']:
        raise ValueError(f"HBM native adoption refused for {master}: {rec['reason']}; receipt {rec['receipt']}")
    # An explicit admission never transfers to a different physical realization.
    for name, expected in rec['view_sha256'].items():
        if hashlib.sha256((Path(view) / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'HBM native view identity mismatch: {master}/{name}')
    if hashlib.sha256((ROOT / rec['source']).read_bytes()).hexdigest() != rec['source_sha256']:
        raise ValueError(f'HBM native source identity mismatch: {master}')
