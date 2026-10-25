"""Qualified native hcore cohort admission and conservative static readiness guards."""
import hashlib
import json
from pathlib import Path


def load_profile(manifest):
    p = Path(manifest)
    d = json.loads(p.read_text())
    c = d.get('core_profile') or {}
    if c.get('kind') != 'S81_CTLA_RSTE_NATIVE_LOAD_STAGE':
        raise ValueError('not a qualified native hcore load-stage profile')
    if not {'OT_ATTN_HCORE', 'OT_S81C_HCORE_CTLA', 'OT_S81C_HCORE_RSTE'} <= set(d.get('defines', [])):
        raise ValueError('selected manifest lacks native CTLA/RSTE defines')
    if c.get('stationary_load_transport_added_cycles') != 1 or c.get('reset_release_cycles_after_core_pin') != 2:
        raise ValueError('unsupported hcore load/reset readiness contract')
    q = json.loads(Path(c['component_qualification']).read_text())
    if q.get('miter') != 'PASS' or q.get('mutant') != 'CAUGHT':
        raise ValueError('hcore qualification is not PASS with mutant caught')
    if c.get('reset_input_timed') is not True or q.get('reset_input_timed') is not True:
        raise ValueError('native hcore cohort does not qualify the required timed reset input')
    for field in ('files', 'prefer'):
        files = d.get(field, [])
        for name, expected in c.get('source_sha256', {}).items():
            selected = [Path(f) for f in files if Path(f).name == name]
            if not selected:
                raise ValueError('profile source absent from selected ' + field + ': ' + name)
            for source in selected:
                got = hashlib.sha256(source.read_bytes()).hexdigest()
                qualified = [v for k, v in q.get('source_sha256', {}).items() if Path(k).name == name]
                if got != expected or qualified != [got]:
                    raise ValueError('profile source is not the qualified cohort: ' + name)
    if set(c.get('source_sha256', {})) != {'ot_s81c_attn_hcore.sv', 'ot_hdc_v41x_attn_tile_s.sv'}:
        raise ValueError('profile must qualify both the core and actual sender')
    return dict(kind=c['kind'], load_guard_cycles=1, reset_guard_cycles=2,
                manifest=str(p.resolve()), profile_sha256=hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest())


def boot_witness(profile, witness):
    d = json.loads(Path(witness).read_text())
    if d.get('profile_sha256') != profile['profile_sha256']:
        raise ValueError('reset/start witness belongs to a different hcore cohort')
    release, start = d.get('last_core_pin_release_cycle'), d.get('start_cycle')
    if not isinstance(release, int) or not isinstance(start, int) or start < release + profile['reset_guard_cycles']:
        raise ValueError('START precedes hcore pin release plus two readiness edges')
    return dict(last_core_pin_release_cycle=release, start_cycle=start, core_ready_cycle=release + 2,
                profile_sha256=profile['profile_sha256'], qualification='STATIC_READINESS_ONLY; bound RTL token still required')


def validate_schedule(schedule, profile):
    r = schedule.get('hcore_readiness') or {}
    g = profile['load_guard_cycles']
    if schedule['go'] < r.get('go_without_guard', schedule['go']) + g:
        raise ValueError('GO misses the native hcore query-load readiness guard')
    if schedule['po'] < r.get('po_without_guard', schedule['po']) + g:
        raise ValueError('PO misses the native hcore P-load readiness guard')
    if schedule['pvo'] < schedule['po']:
        raise ValueError('P.V drain precedes its guarded P input')
    return True
