"""Rejudge counting records from their measured sign-off evidence."""

import inspect
import re
from pathlib import Path

here = Path(__file__).resolve().parent
profile_file = here.parent / 'die_plan' / 'signoff_profile.py'
if not profile_file.is_file():
    profile_file = here / 'signoff_profile.py'
_PROFILE_PY = profile_file.read_text()
_profile = {}
exec(compile(_PROFILE_PY, str(profile_file), 'exec'), _profile)
judge_minimal = _profile['judge']
probe_signoff = _profile['probe_signoff']


def measured_minimal(d):
    try:
        return judge_minimal(d)['verdict'] == 'SIGNED'
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


def _fin(x):
    try: x = float(x)
    except (TypeError, ValueError): return None
    return x if abs(x) < 1e6 else None
def record_clock_period(d):
    # largest create_clock period the record's STA ran at (corners.<c>.periods; generated clocks print 0); None when not recorded
    best = None
    for c in (d.get('corners') or {}).values():
        if not isinstance(c, dict) or not isinstance(c.get('periods'), dict): continue
        for v in c['periods'].values():
            v = _fin(v)
            if v is not None and v > 0 and (best is None or v > best): best = v
    return best
def legacy_period_problem(d):
    # OWNER 11-20 (superseding the 1000 ps part of (1)): nothing signs above 833 ps (tools/die_plan/signoff_profile.period_problem):
    # a record timed at a relaxed clock never counts, with or without signed_period_ps
    sp, cp = _fin(d.get('signed_period_ps')), record_clock_period(d)
    if sp is None: return cp is not None and cp > 833.5
    return sp < 832.5 or sp > 833.5 or cp is None or abs(cp - sp) > 0.5
def legacy_rminimal(d):
    # Compatibility for unprofiled historical records only.
    # COUNT-FRICTION-1 11-14 (R-MINIMAL, OWNER 11-13 17:5x; same metrics as tools/die_plan/signoff_profile.py): a record counts when detailed-route
    # DRC is 0, TT setup WNS >= -42 ps (833 ps) and the INTERNAL FF hold >= 0 (a hold miss only at input ports is allowed); every other
    # check is advisory.  This lets a record whose legacy verdict is NOT SIGNED for an advisory reason count.
    try:
        ch = d.get('checks') or {}
        drc = (ch.get('drc') or {}).get('count') if isinstance(ch.get('drc'), dict) else None
        if drc is None: drc = (d.get('route') or {}).get('drc')
        st = ch.get('setup_tt') if isinstance(ch.get('setup_tt'), dict) else {}
        tt = _fin(st.get('wns_ps'))
        if tt is None: tt = _fin(st.get('sdc_wns_ps'))
        hf = ch.get('hold_ff') if isinstance(ch.get('hold_ff'), dict) else {}
        ff = _fin(hf.get('wns_ps'))
        if ff is None: ff = _fin(hf.get('sdc_wns_ps'))
        if drc is None or int(drc) != 0 or tt is None or tt < -42.0 or ff is None: return False
        if legacy_period_problem(d): return False
        return ff >= 0.0 or (bool(hf.get('port_only_needs_parent')) and hf.get('verdict') == 'PASS')
    except Exception:
        return False
def counts_signed(d):
    if probe_signoff(d):
        return False
    # Minimal verdict stamps can be written by older callers. Always replay
    # their evidence, including the complete internal FF census.
    if d.get('profile') == 'minimal':
        return measured_minimal(d)
    v = d.get('verdict')
    if v == 'SIGNED':
        return True
    # OWNER 11-03: the parent receipt can be deferred for port-only hold.
    if v == 'LOCAL_PASS_NEEDS_PARENT' and d.get('local_verdict') == 'SIGNED':
        return all(str(r).startswith('io_hold_parent') for r in (d.get('reasons') or []))
    if v == 'HARD-IP':
        ch = d.get('checks') or {}
        return (d.get('schema') == 'opentallas.hard_ip_view.v1' and (ch.get('bind') or {}).get('errors') == 0
                and ch.get('port_bind') == 'PASS' and not ch.get('face_guard_fails'))
    return legacy_rminimal(d)


def archive_record_counts(record, declared_minimal):
    """An index row declaring R-MINIMAL needs its exact measured record."""
    if not isinstance(record, dict):
        return not declared_minimal
    return measured_minimal(record) if declared_minimal else counts_signed(record)


# Remote scans run in an isolated interpreter and have no checkout dependency.
REMOTE_PY = (_PROFILE_PY + '\njudge_minimal = judge\n'
             + '\n'.join(inspect.getsource(fn) for fn in
                          (measured_minimal, _fin, record_clock_period, legacy_period_problem, legacy_rminimal, counts_signed))
             + '\n')


def index_record_counts(listing, row, store=None):
    """Resolve a measured record by its immutable index ID or exact meta path."""
    import signed_store

    meta = row.get('meta')
    record = (listing.get('agidock_count_signoffs') or {}).get(meta)
    if record is None:
        record = (listing.get('agidock_signoffs') or {}).get(meta)
    eid = row.get('record') or ''
    if record is None and len(eid) == 64 and all(c in '0123456789abcdef' for c in eid):
        try:
            entry = signed_store.read_entry(signed_store.entry_path(eid, str(store) if store else None))
            record = signed_store.unblob(entry.get('signoff_json'))
        except (OSError, EOFError, ValueError):
            pass
    declared_minimal = re.search(r'\bR-MINIMAL\b', row.get('src') or '') is not None
    return archive_record_counts(record, declared_minimal)
