#!/usr/bin/env python3
"""retired_hosts.py -- drop retired fleet hosts from a job spec's hosts / host_require (HOSTFIX, 2026-10-17).

Old kit templates still pin hosts that left the fleet (EPYC2/3 retired 10-12, EPYC1 10-16).  validate() marked such a
job INVALID ("unknown host ot-epyc1tb", qkd_static_ectla_k3-r3-c71c412db) although the pin is only a preference.  A
retired name is now removed with a warning; an emptied list is removed, so the job falls back to normal admission.
Unknown names that are NOT retired (typos) stay a validate() error.
"""
import copy

# names the fleet used for retired hosts; hosts.json may add more under "retired_hosts"
RETIRED_HOSTS = frozenset({"ot-epyc1", "ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-epyc4", "ot-epyc5", "ot-epyc6"})   # ot-epyc4 terminated 2026-10-19 (EPYC4-RETIRE); ot-epyc6 2026-10-21 (EPYC6-RETIRE); ot-epyc5 retiring 2026-10-23 (EPYC5-RETIRE)


def retired_names(table_doc=None):
    extra = (table_doc or {}).get("retired_hosts") or []
    return RETIRED_HOSTS | {str(x) for x in extra}


def drop_retired_hosts(spec, known=(), retired=RETIRED_HOSTS):
    """(spec', warnings).  spec' is a deep copy with retired names removed from hosts / host_require (an emptied list
    is deleted); spec itself is returned unchanged (same object) when nothing was dropped.  A name in `known` (the live
    hosts.json table) is never dropped, so re-enabling a host in hosts.json wins over this list."""
    if not isinstance(spec, dict):
        return spec, []
    known = set(known)
    warns, out = [], None
    for key in ("hosts", "host_require"):
        val = spec.get(key)
        if not isinstance(val, list):
            continue
        gone = [h for h in val if isinstance(h, str) and h in retired and h not in known]
        if not gone:
            continue
        if out is None:
            out = copy.deepcopy(spec)
        keep = [h for h in val if h not in gone]
        if keep:
            out[key] = keep
            warns.append(f"RETIRED-HOST WARN: dropped {', '.join(gone)} from {key} (kept {', '.join(map(str, keep))})")
        else:
            del out[key]
            warns.append(f"RETIRED-HOST WARN: dropped {', '.join(gone)} from {key}; list now empty and removed: "
                         f"normal admission places the job")
    return (spec if out is None else out), warns
