"""Selected E5 source entry readiness; no physical qualification is implied."""
import hashlib
import json
from pathlib import Path

def load_profile(manifest):
    p = Path(manifest)
    d = json.loads(p.read_text())
    c = d.get('eng_profile') or {}
    if c.get('kind') != 'S81_ENG_F6_TIMED_ENTRY':
        raise ValueError('selected manifest has no E5 timed entry profile')
    q = json.loads(Path(c['component_qualification']).read_text())
    if not set(q.get('source_flags', [])) <= set(d.get('defines', [])) or not q.get('source_flags'):
        raise ValueError('selected manifest lacks qualified E5 flags')
    required = dict(entry_readiness_added_cycles=1, LKP_XQ_added_cycles=0,
                    reset_assert_edges=3, reset_release_edges=3, early_reset_edges=1,
                    additional_entry_boot_edges=1)
    if any(q.get(k) != v for k, v in required.items()):
        raise ValueError('unsupported E5 entry/reset contract')
    gates = q.get('gates', {})
    if not gates.get('core_full', '').startswith('3seeds*200000cycles allpublic+internalx/xd0mismatch') or any('CAUGHT' not in gates.get(k, '') for k in ('xq_full', 'win', 'reset')):
        raise ValueError('E5 component or negative-control gate missing')
    hashes = q.get('source_sha256', {})
    if len(hashes) != 3 or c.get('source_sha256') != hashes:
        raise ValueError('E5 source cohort is incomplete')
    for field in ('files', 'prefer'):
        for name, expected in hashes.items():
            paths = [Path(x) for x in d.get(field, []) if Path(x).name == Path(name).name]
            if not paths or any(hashlib.sha256(x.read_bytes()).hexdigest() != expected for x in paths):
                raise ValueError('selected E5 source differs from qualified ' + name)
    cohort_path = Path(c['compiled_sources'])
    raw = cohort_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != c.get('compiled_sources_sha256'):
        raise ValueError('E5 compiled cohort record changed')
    cohort = json.loads(raw)
    entries = cohort.get('compiled_source_cohort', []) + [cohort.get('wrapper') or {}]
    if not entries or not cohort.get('wrapper') or cohort.get('source_commit') != c.get('source_commit'):
        raise ValueError('E5 full compiled source cohort or wrapper missing')
    for item in entries:
        name, expected = item.get('basename'), item.get('sha256')
        if not name or not expected:
            raise ValueError('incomplete E5 compiled source entry')
        if item.get('native_matches') is True:
            if item.get('native_sha256') != expected:
                raise ValueError('native E5 source differs from compiled source')
            fields = ('files', 'prefer')
        else:
            # Explicit functional macro models are required as replay inputs.
            # A native interface blackbox cannot substitute for simulation.
            if not name.endswith('.v') or not name.startswith(('ot_rom_', 'ot_sram_')):
                raise ValueError('unqualified native E5 source mismatch: ' + name)
            fields = ('simulation_files',)
        for field in fields:
            paths = [Path(x) for x in d.get(field, []) if Path(x).name == name]
            if not paths or any(hashlib.sha256(x.read_bytes()).hexdigest() != expected for x in paths):
                raise ValueError('selected E5 full cohort differs in ' + field + ': ' + name)
    return dict(kind=c['kind'], entry_guard_cycles=1, reset_guard_cycles=4,
                return_age_added_cycles=0, manifest=str(p.resolve()),
                profile_sha256=hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest())

def boot_witness(profile, witness):
    d = json.loads(Path(witness).read_text())
    if d.get('profile_sha256') != profile['profile_sha256']:
        raise ValueError('Eng reset/START witness has a different source cohort')
    release, start = d.get('last_core_pin_release_cycle'), d.get('start_cycle')
    if not isinstance(release, int) or not isinstance(start, int) or start < release + profile['reset_guard_cycles']:
        raise ValueError('Eng START precedes pin release+3 reset edges+1 entry edge')
    cfg = d.get('cfg_en_stable_from_cycle')
    if not isinstance(cfg, int) or cfg > start:
        raise ValueError('cfg_en is not aligned before the selected entry record')
    return dict(cfg_en_stable_from_cycle=cfg, profile_sha256=profile['profile_sha256'], last_core_pin_release_cycle=release,
                start_cycle=start, core_ready_cycle=release + 4, entry_guard_cycles=1,
                qualification='STATIC_READINESS_ONLY; actual bound token still required')

def validate_landed_start(profile, witness, engine_pin_cycle):
    if witness.get('cfg_en_stable_from_cycle', engine_pin_cycle + 1) > engine_pin_cycle:
        raise ValueError('cfg_en arrives after the Eng f_ks entry record')
    release = witness.get('last_core_pin_release_cycle')
    if not isinstance(release, int) or witness.get('core_ready_cycle') != release + profile['reset_guard_cycles']:
        raise ValueError('Eng readiness receipt is inconsistent with pin release')
    if witness.get('profile_sha256') != profile['profile_sha256'] or engine_pin_cycle < release + profile['reset_guard_cycles']:
        raise ValueError('landed Eng f_ks precedes selected E5 readiness')
    return dict(engine_fks_pin_cycle=engine_pin_cycle,
                internal_entry_record_cycle=engine_pin_cycle + 1,
                return_age_added_cycles=0)
