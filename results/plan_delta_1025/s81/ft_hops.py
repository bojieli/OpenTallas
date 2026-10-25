#!/usr/bin/env python3
"""PLAN-DELTA/S81: per-bit FT hop audit of types (pin_in -> internal bit_sites_um stages -> pin_out, Manhattan um),
from the type-frame pin table of gen_phys.type_pins (bit order included).  A bit-order repair flips which pin feeds
which explicit site, so the internal hops can grow; this prints max hop per slot and the worst per type.
usage: ft_hops.py PLAN.json [TYPE ...]  (default: every type with bit_sites_um) -> JSON on stdout"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S  # noqa: E402
from gen_phys import type_pins  # noqa: E402


def audit(raw, types=None):
    model = S.Plan(raw)
    out = {}
    for tn, ty in model.types.items():
        if types and tn not in types:
            continue
        slots = [s for s in ty.get("ft_slots", []) if s.get("bit_sites_um")]
        if not slots:
            continue
        pins = {(b, i): (x, y) for b, i, _, x, y, _ in type_pins(model, tn)}
        rec = {}
        for s in slots:
            worst = 0.0
            for bit in range(s["width"] + 1):
                a = pins.get((s["name"] + "_i", bit))
                z = pins.get((s["name"] + "_o", bit))
                if a is None or z is None:
                    continue
                chain = [a] + [tuple(st[bit]) for st in s["bit_sites_um"]] + [z]
                for p, q in zip(chain, chain[1:]):
                    worst = max(worst, abs(p[0] - q[0]) + abs(p[1] - q[1]))
            rec[s["name"]] = round(worst, 2)
        out[tn] = dict(max=max(rec.values()) if rec else 0.0, slots=rec)
    return out


if __name__ == "__main__":
    raw = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(audit(raw, set(sys.argv[2:]) or None), indent=1))
