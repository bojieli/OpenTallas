"""ADV-PHASE-BIND (DIECLOCK-PHASE-BIND-CHECK, C-DIECLOCK-PHASE-BIND, COORD 11-26; the advisory lines are report only).

BLOCKING at the cut (COORD FABLE-RC-HEAD 1127): blocking() returns FAIL ADV-PHASE-BIND lines, which plan_gate_pre runs as the
PHASE-BIND class (skip PHASE-BIND / OT_PHASE_BIND_BLOCK=0 turns it off).  Unbound or stale phase rows fail PRE:
  NO-BIND            a plan with pin_entry_phase instances and no phase_bind.json (count-align-only plans stay WARN)
  STALE-CLOCK        the bind's ctree.spef sha12 differs from $OT_PHASE_BIND_CTREE_SHA12 (the cut's live die clock), when set
  STALE-INSTANCE     a pin_entry_phase instance with no record in the bind (the plan grew after the derive)
  RESET-ENTRY MISBOUND / START-EDGE MISBOUND   a plan phase scoring below the guard where the routed clock has a choice above it
UNMEASURED instances, NO-WINDOW seams (structural rows) and COUNT-ALIGN-UNBOUND stay WARN unless OT_PHASE_BIND_STRICT=1.

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


BLOCK_PREFIXES = ("RESET-ENTRY MISBOUND", "START-EDGE MISBOUND")
STRICT_PREFIXES = ("RESET-ENTRY NO-WINDOW", "COUNT-ALIGN-UNBOUND")


def blocking(raw, plan_path, **_kw):
    """FAIL ADV-PHASE-BIND lines (always [] when OT_PHASE_BIND_BLOCK=0 or the plan has no phase users)."""
    if os.environ.get("OT_PHASE_BIND_BLOCK", "1") == "0":
        return []
    pdir = Path(plan_path).resolve().parent if plan_path else Path(".")
    bp = os.environ.get("OT_PHASE_BIND") or str(pdir / "phase_bind.json")
    sp = os.environ.get("OT_PHASE_BIND_SIDECAR") or str(pdir / "source_sidecar.json")
    bind = _load(bp) if Path(bp).is_file() else None
    sidecar = _load(sp) if Path(sp).is_file() else None
    types = raw.get("partition_types") or {}
    insts = sorted(p["name"] for p in raw.get("partitions", []) if isinstance(p, dict) and PB.enabled(types.get(p.get("type"))))
    if bind is None:
        if insts:
            return [f"FAIL ADV-PHASE-BIND NO-BIND {len(insts)} pin_entry_phase instance(s) have no phase_bind.json ({bp}): derive it "
                    f"on the die clock of this cut (phase_bind.py derive)"]
        return []
    out = []
    want = os.environ.get("OT_PHASE_BIND_CTREE_SHA12")
    have = (bind.get("key") or {}).get("ctree_spef_sha12")
    if want and have != want:
        out.append(f"FAIL ADV-PHASE-BIND STALE-CLOCK bind derived on ctree.spef {have}, the cut's die clock is {want}")
    known = bind.get("reset_entry") or {}
    miss = [n for n in insts if n not in known]
    if miss:
        out.append(f"FAIL ADV-PHASE-BIND STALE-INSTANCE {len(miss)} pin_entry_phase instance(s) not in the bind, e.g. {', '.join(miss[:4])}")
    pre = BLOCK_PREFIXES + (STRICT_PREFIXES if os.environ.get("OT_PHASE_BIND_STRICT") == "1" else ())
    for x in PB.check_lines(raw, bind, sidecar, max_list=10 ** 6):
        if x.startswith(pre):
            out.append(f"FAIL ADV-PHASE-BIND {x}")
    return out
