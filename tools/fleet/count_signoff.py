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


def measured_minimal(d):
    try:
        return judge_minimal(d)['verdict'] == 'SIGNED'
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


def counts_signed(d):
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
    return measured_minimal(d)


def archive_record_counts(record, declared_minimal):
    """An index row declaring R-MINIMAL needs its exact measured record."""
    if not isinstance(record, dict):
        return not declared_minimal
    return measured_minimal(record) if declared_minimal else counts_signed(record)


# Remote scans run in an isolated interpreter and have no checkout dependency.
REMOTE_PY = (_PROFILE_PY + '\njudge_minimal = judge\n' + inspect.getsource(measured_minimal)
             + '\n' + inspect.getsource(counts_signed) + '\n')


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
