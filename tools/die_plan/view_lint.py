"""VIEW-NOOBS (C-VIEW-NO-OBS, S81-GATE-LINT 11-26, FABLE-FLOW-0847 A8): a hard-macro LEF view must carry OBS and PG pins.

ot_s81dv_norm_finish was used as a hard macro with a LEF of 576 M5 signal pins only: no OBS (the router saw the body as free
space) and no PG pins (515 floating pins, RSZ-0020 / RSZ-0095).  A LEF a plan uses as a hard core (partition_types[].hard_cores[].lef)
without an OBS block, or without a PIN USE POWER / GROUND, is a FAIL line of PRE (class VIEWOBS).
    python3 tools/die_plan/view_lint.py LEF [LEF ...]      (rc 1 on a problem)
"""
import re
import sys
from pathlib import Path

CHECK = "VIEW-NOOBS"


def lef_problems(text):
    """-> [problem] of one LEF text: 'no OBS' (no OBS block with a RECT / POLYGON), 'no PG pins' (no PIN with USE POWER|GROUND)"""
    out = []
    has_obs = False
    for m in re.finditer(r"(?m)^\s*OBS\b(.*?)^\s*END\s*$", text, re.S):
        if re.search(r"\b(RECT|POLYGON)\b", m.group(1)):
            has_obs = True
            break
    if not has_obs:
        out.append("no OBS")
    pg = False
    for m in re.finditer(r"(?m)^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", text, re.S):
        if re.search(r"(?m)^\s*USE\s+(POWER|GROUND)\b", m.group(2)):
            pg = True
            break
    if not pg:
        out.append("no PG pins")
    return out


def _resolve(lef, bases):
    p = Path(lef)
    if p.is_absolute():
        return p if p.is_file() else None
    for b in bases:
        if b and (Path(b) / lef).is_file():
            return Path(b) / lef
    return None


def findings(raw, plan_path=None, repo=None, **_kw):
    """FAIL VIEW-NOOBS lines: every hard core whose plan LEF (found on disk) lacks OBS or PG pins.  A LEF that is not on disk is not judged
    here (MACROGHOST / TOOLROOT own that); one LEF is judged once and named with every type that uses it."""
    pp = Path(plan_path) if plan_path else None
    bases = [repo] + ([pp.parent, *pp.parents] if pp else [])
    seen, out = {}, []
    for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        for h in t.get("hard_cores") or []:
            lef = h.get("lef") if isinstance(h, dict) else None
            if not lef:
                continue
            seen.setdefault(str(lef), (h.get("module"), []))[1].append(tn)
    for lef, (mod, types) in sorted(seen.items()):
        f = _resolve(lef, bases)
        if f is None:
            continue
        try:
            probs = lef_problems(f.read_text(errors="replace"))
        except OSError:
            continue
        if probs:
            out.append(f"FAIL {CHECK} {mod}: hard-macro LEF {lef} has {' and '.join(probs)} (used by {', '.join(sorted(set(types))[:4])}"
                       f"{' ...' if len(set(types)) > 4 else ''}); the router sees the body as free space / its power pins float: "
                       f"use a LEF with OBS M1-M5 and PG pins")
    return out


def main(argv=None):
    bad = 0
    for a in (argv if argv is not None else sys.argv[1:]):
        probs = lef_problems(Path(a).read_text(errors="replace"))
        print(f"{a}: {'; '.join(probs) or 'ok'}")
        bad += bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
