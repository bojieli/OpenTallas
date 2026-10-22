"""Opt-in QKH successor identities; native receipts are required before selection.

No stand-in, diagnostic autoprofile or arithmetic alias is accepted here.
The existing frame containment/overlap checks still qualify the larger leaves.
"""
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

import kv_expand_parameters as EP

FLAG = 'OT_KV_QKH_SAFE32'
TARGETS = {
    'ot_qkh_lane8_nc32c': {
        'rtl': 'rtl/hdc/nearhbm/ot_qkh_lane8_nc32c.sv',
        'view': 'physical/ref_tile/ot_qkh_lane8_nc32c/views/ot_qkh_lane8_nc32c',
        'parameters': {'ADD_LAT': 7, 'LTW': 12}},
    'ot_qkh_ktree_lk_nc32c': {
        'rtl': 'rtl/hdc/nearhbm/ot_qkh_ktree_nc32c.sv',
        'view': 'physical/ref_tile/ot_qkh_ktree_lk_nc32c/views/ot_qkh_ktree_lk_nc32c',
        'parameters': {'ADD_LAT': 7, 'MUL_LAT': 6, 'SCALE': 0x3DB504F3, 'MUT': 0}},
}


def enabled():
    return os.environ.get(FLAG, '0') == '1'


def data_edges():
    """Measured complete16-lane LK delta; input/output wrapper stages stay ON."""
    return 2 if enabled() else 0


def capture_hxk():
    # Real ECTL current-GEN9 component: HXK15 retires all256 tags at age82;
    # HXK14/13 causally fail at175/174 versus expected176.
    return 13 + data_edges()


def calendar_d_qk(issue_age, base_consume=34):
    # Fetch/issue age is unchanged. Only the post-issue score path moves.
    return issue_age - base_consume + data_edges()


def configure(views, rtl):
    if enabled():
        views.update({m: t['view'] for m, t in TARGETS.items()})
        rtl.update({m: t['rtl'] for m, t in TARGETS.items()})


DIAG_FLAG = 'OT_KV_QKH_SAFE32_DIAG'


def diagnostic_missing_allowed():
    """KV-BIND10 10-20: explicit DIAGNOSTIC-only opt-in (needs OT_KV_PARAM_DIAG=1 too; the chain stamps
    NOT_A_DIE_RESULT): a target whose standard-LEC receipt has not landed yet is left to kv_expand's diagnostic
    autoprofile.  A SUPPLIED profile is still checked exactly; strict runs never take this path."""
    return os.environ.get(DIAG_FLAG, '0') == '1' and os.environ.get('OT_KV_PARAM_DIAG', '0') == '1'


def require_profiles(root, profiles, allow_missing=False):
    """Check both exact selected views and frozen receipts even in diagnostic mode."""
    root = Path(root)
    missing = []
    for module, target in TARGETS.items():
        profile = profiles.get(module)
        if profile is None and allow_missing and diagnostic_missing_allowed():
            missing.append(module)
            continue
        if not isinstance(profile, dict) or profile.get('parameters') != target['parameters']:
            raise ValueError(f'{module}: missing exact safe32 parameter profile')
        defaults = EP.integer_defaults((root / target['rtl']).read_text(), module)
        if defaults != target['parameters']:
            raise ValueError(f'{module}: safe32 RTL defaults changed')
        _, checked = EP.preserve(root, module, {}, target['rtl'], target['view'], profiles, diagnostic=False)
        if not checked['native_qualified']:
            raise ValueError(f'{module}: safe32 native qualification missing')
    return missing


def produce_profiles(root, audits, out, base=None):
    """Use the canonical PROVEN-audit receipt producer, then merge exact targets."""
    import kv_param_native_audit as A
    root, out = Path(root).resolve(), Path(out).resolve()
    if not out.is_relative_to(root):
        raise ValueError('profile output must be within the pinned source root')
    if (out / 'profiles.json').exists():
        raise ValueError('profile output already exists; use a fresh immutable evidence directory')
    A.receipts(SimpleNamespace(root=str(root), audits=str(audits), out=str(out / 'qualified')))
    selected = json.loads((out / 'qualified/profiles.json').read_text())
    require_profiles(root, selected)
    profiles = json.loads(Path(base).read_text()) if base else {}
    for module in TARGETS:
        if module in profiles and profiles[module] != selected[module]:
            raise ValueError(f'{module}: conflicting base profile; explicit replacement required')
        profiles[module] = selected[module]
    (out / 'profiles.json').write_text(json.dumps(profiles, indent=2, sort_keys=True) + '\n')
    return profiles


if __name__ == '__main__':
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--audits', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--base', help='existing native profiles to retain without replacement')
    a = ap.parse_args()
    produce_profiles(a.root, a.audits, a.out, a.base)
