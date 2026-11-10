#!/usr/bin/env python3
"""Kit evidence for tied count straps that have no planned pin site (PIN-AUDIT-COUNT-STRAP, COORD 11-09).

A count strap (types[].count_straps, OWNER 12.15a) is a constant the parent ties.  Without sites_um it is absent from
the kit pin table, so place_pins places it freely and pin_audit would report it as an extra pin.  pin_audit accepts such
a pin only when this file shows all three facts for it: the plan declares it in count_straps, kit-rtl lists it as a
bound-only input of the same width, and the bind tie audit (PASS) has a literal of that width on every instance.

    count_strap_evidence.py <plan.json> <type> <kit_rtl.json> <kit dir>
"""
import json
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.count_strap_evidence.v1"
FILE = "count_strap_evidence.json"


def sv_id(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def build(type_plan, kit_rtl, tie_audit):
    """raw facts only; the acceptance rule lives in pin_audit.accepted_count_strap_bits"""
    straps = [dict(name=r["name"], width=int(r["width"])) for r in type_plan.get("count_straps") or []]
    names = {r["name"] for r in straps}
    instances = sorted(sv_id(i) for i in kit_rtl.get("instances") or [])
    ties = {}
    if tie_audit.get("verdict") == "PASS":
        for inst, port, literal in tie_audit.get("rows") or []:
            if port in names and inst in instances:
                ties.setdefault(port, {})[inst] = literal
    return dict(schema=SCHEMA, type=kit_rtl.get("bound_type"), plan_count_straps=straps, instances=instances,
                bound_only_pins=[r for r in kit_rtl.get("bound_only_pins") or [] if r.get("port") in names],
                parent_ties=ties)


def write_for_kit(kit, type_plan, kit_rtl_json):
    """write kit/FILE when the type declares count straps; -> the evidence, or None (no file: pin_audit stays strict)"""
    if not type_plan.get("count_straps"):
        return None
    if not Path(kit_rtl_json).is_file():
        return None
    kit_rtl = json.loads(Path(kit_rtl_json).read_text())
    tie_file = Path(kit_rtl.get("bind_out") or "") / "bind_tie_audit.json"
    tie_audit = json.loads(tie_file.read_text()) if tie_file.is_file() else {}
    evidence = build(type_plan, kit_rtl, tie_audit)
    (Path(kit) / FILE).write_text(json.dumps(evidence, indent=1) + "\n")
    return evidence


def main(argv):
    plan, tn, kit_rtl_json, kit = argv
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pin_audit import accepted_count_strap_bits
    types = json.loads(Path(plan).read_text())["partition_types"]
    evidence = write_for_kit(kit, types[tn], kit_rtl_json)
    bits = sorted(accepted_count_strap_bits(evidence or {}))
    print(f"COUNT_STRAP_EVIDENCE {tn} straps {len((evidence or {}).get('plan_count_straps', []))} accepted_bits {len(bits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
