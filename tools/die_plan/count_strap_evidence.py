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


def plan_facts(type_plan, parts):
    """KIT-STRAP-EVIDENCE 11-23: the kit_rtl facts from the die plan, for a kit_rtl.json that carries none (HEAD wave
    head_wave_kit_rtl.v1: no instances / bound_only_pins / bound_type).  gen.py rtl ties every count strap on the die top from
    partitions[].id_straps (gen_rtl.die_top), so the plan holds the same literals the bind tie audit records.
    parts = [(instance name, partition dict)] of this type -> (kit_rtl-like dict, tie_audit-like dict)"""
    straps = type_plan.get("count_straps") or []
    names = {r["name"] for r in straps}
    rows = []
    for inst, part in parts:
        for name, value in sorted((part.get("id_straps") or {}).items()):
            if name in names:
                width = next(int(r["width"]) for r in straps if r["name"] == name)
                rows.append([sv_id(inst), name, f"{width}'d{int(value)}"])
    kit_rtl = dict(instances=sorted(sv_id(i) for i, _ in parts),
                   bound_only_pins=[dict(port=r["name"], dir="input", width=int(r["width"])) for r in straps])
    return kit_rtl, dict(verdict="PASS", rows=rows)


def missing_bits(type_plan, evidence):
    """declared count-strap bits without a pin site that the evidence does not accept (pin_audit would call them extra)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pin_audit import accepted_count_strap_bits
    ok = accepted_count_strap_bits(evidence or {})
    out = []
    for r in type_plan.get("count_straps") or []:
        if r.get("sites_um"):
            continue                       # a planned pin site: the kit pin table has it, no evidence needed
        w = int(r["width"])
        out += [f"{r['name']}[{b}]" for b in range(w) if f"{r['name']}[{b}]" not in ok]
    return out


def write_for_kit(kit, type_plan, kit_rtl_json, parts=None, strict=False):
    """write kit/FILE when the type declares count straps; -> the evidence, or None (no file: pin_audit stays strict).
    kit_rtl without instances/bound_only_pins (HEAD wave) takes them from the plan (parts).  strict: an evidence that leaves
    a declared strap unaccepted raises here (GENDRY), not at PIN_AUDIT after the route."""
    if not type_plan.get("count_straps"):
        return None
    if not Path(kit_rtl_json).is_file():
        if not (strict and parts):
            return None
        kit_rtl = {}
    else:
        kit_rtl = json.loads(Path(kit_rtl_json).read_text())
    if parts and not (kit_rtl.get("instances") and kit_rtl.get("bound_only_pins")):
        plan_kr, plan_ties = plan_facts(type_plan, parts)
        evidence = build(type_plan, dict(plan_kr, bound_type=kit_rtl.get("bound_type") or kit_rtl.get("plan_type")), plan_ties)
        evidence["source"] = "plan partitions[].id_straps (kit_rtl.json has no instances/bound_only_pins)"
        bad = missing_bits(type_plan, evidence) if strict else []
        if bad:
            raise ValueError(f"count_strap_evidence empty/short: {len(bad)} declared count-strap bit(s) not tied on every instance "
                             f"(plan partitions id_straps): {bad[:6]}")
        (Path(kit) / FILE).parent.mkdir(parents=True, exist_ok=True)
        (Path(kit) / FILE).write_text(json.dumps(evidence, indent=1) + "\n")
        return evidence
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bound_r8_straps as _BRS              # FLOW-PROC-A 11-21: kit copy first, then bind_out
    tie_file = _BRS.bind_file(kit_rtl_json, kit_rtl, "bind_tie_audit.json")
    tie_audit = json.loads(tie_file.read_text()) if tie_file else {}
    evidence = build(type_plan, kit_rtl, tie_audit)
    bad = missing_bits(type_plan, evidence) if strict else []
    if bad:
        raise ValueError(f"count_strap_evidence empty/short: {len(bad)} declared count-strap bit(s) not accepted "
                         f"(kit_rtl instances {len(evidence['instances'])}, ties {len(evidence['parent_ties'])}): {bad[:6]}")
    (Path(kit) / FILE).parent.mkdir(parents=True, exist_ok=True)
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
