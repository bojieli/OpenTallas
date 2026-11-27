"""ADV-PHASE-BIND (DIECLOCK-PHASE-BIND-CHECK, C-DIECLOCK-PHASE-BIND, COORD 11-26; report only, never a gate).

The plan's per-instance clock-phase choices (partitions[].reset_entry_phase + id_straps strap_rst_ph of pin_entry_phase
types, the START tree edge_fall, count-align J / K) must be the ones the ROUTED die clock wants.  On HEAD W10 / W11 they were
derived on a cell-delay die tree: phase_bind.py on the routed W10 die clock finds 33 of 358 entry phases below the 60 ps guard
(tE3b3 h=2 -213 ps; the routed clock wants h=1, +203 ps).

Reads the phase_bind.json of the plan: $OT_PHASE_BIND, else <plan dir>/phase_bind.json.  With none, a plan that uses
pin_entry_phase or a count-aligned sidecar gets one NO-BIND line (its phases were never checked against a routed clock).
The sidecar is <plan dir>/source_sidecar.json or $OT_PHASE_BIND_SIDECAR when present.

    findings(raw, plan_path, tree=None) -> ["WARN ADV-PHASE-BIND ..."]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase_bind as PB  # noqa: E402


def _uses_phases(raw):
    return any(PB.enabled(t) for t in (raw.get("partition_types") or {}).values())


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def findings(raw, plan_path, tree=None, **_kw):
    pdir = Path(plan_path).resolve().parent if plan_path else Path(".")
    bp = os.environ.get("OT_PHASE_BIND") or str(pdir / "phase_bind.json")
    sp = os.environ.get("OT_PHASE_BIND_SIDECAR") or str(pdir / "source_sidecar.json")
    bind = _load(bp) if Path(bp).is_file() else None
    sidecar = _load(sp) if Path(sp).is_file() else None
    if bind is None:
        if _uses_phases(raw) or ((sidecar or {}).get("count_aligned")):
            n = sum(1 for p in raw.get("partitions", [])
                    if PB.enabled((raw.get("partition_types") or {}).get(p.get("type"))))
            return [f"WARN ADV-PHASE-BIND NO-BIND {n} pin_entry_phase instance(s) and the START / count-align phases were "
                    f"never checked against a routed die clock (no {bp}; phase_bind.py derive on the die clock event)"]
        return []
    return [f"WARN ADV-PHASE-BIND {x}" for x in PB.check_lines(raw, bind, sidecar)]
