#!/usr/bin/env python3
"""Kit evidence for tied count straps that have no planned pin site (PIN-AUDIT-COUNT-STRAP, COORD 11-09).

A count strap (types[].count_straps, OWNER 12.15a) is a constant the parent ties.  Without sites_um it is absent from
the kit pin table, so place_pins places it freely and pin_audit would report it as an extra pin.  pin_audit accepts such
a pin only when this file shows all three facts for it: the plan declares it in count_straps, kit-rtl lists it as a
bound-only input of the same width, and the bind tie audit (PASS) has a literal of that width on every instance.

    count_strap_evidence.py <plan.json> <type> <kit_rtl.json> <kit dir>
"""
import hashlib
import json
import os
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


def audit_literals(doc):
    """{(instance, port): literal} of a PASS tie audit; both schemas: straps.audit_top_ties rows [[inst, port, lit]] and the
    HEAD die portbind file (rows = a count, accepted = [["inst.port", lit]]).  {} for a missing or FAIL audit."""
    if not isinstance(doc, dict) or doc.get("verdict") != "PASS":
        return {}
    out = {}
    rows = doc.get("rows")
    if isinstance(rows, list):
        for inst, port, lit in rows:
            out[(inst, port)] = lit
    for key, lit in doc.get("accepted") or []:
        inst, _, port = key.rpartition(".")
        out.setdefault((inst, port), lit)
    return out


def find_audit(kit_rtl_json, kit_rtl):
    """-> first existing tie-audit file of the BOUND plan: kit copy / bind_out bind_tie_audit.json, bind_out tie_audit.json (HEAD die
    portbind), kit_rtl.tie_audit, env OT_BIND_TIE_AUDIT; None when none exists"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bound_r8_straps as _BRS
    found = _BRS.bind_file(kit_rtl_json, kit_rtl, "bind_tie_audit.json") if kit_rtl_json else None
    if found:
        return found
    cands = []
    if kit_rtl.get("bind_out"):
        cands.append(Path(kit_rtl["bind_out"]) / "tie_audit.json")
    for c in (kit_rtl.get("tie_audit"), os.environ.get("OT_BIND_TIE_AUDIT")):
        if c:
            cands.append(Path(c))
    return next((c for c in cands if c.is_file()), None)


def plan_literals(type_plan, parts):
    """{(instance, port): literal} the plan carries (partitions[].id_straps) for the type's count straps; UNVERIFIED (same source
    as the die-top RTL gen, so it cannot catch a bind that computes another value)"""
    straps = {r["name"]: int(r["width"]) for r in type_plan.get("count_straps") or []}
    return {(sv_id(i), n): f"{straps[n]}'d{int(v)}" for i, part in parts for n, v in (part.get("id_straps") or {}).items() if n in straps}


def lit_value(lit):
    w, v = lit.replace(" ", "").split("'")
    return int(w), int(v[1:].replace("_", ""), {"b": 2, "d": 10, "h": 16}[v[0].lower()])


def cross_check(plan_lits, audit_lits):
    """-> (compared, mismatched): plan literals against audit literals of the same (instance, port)"""
    both = [k for k in plan_lits if k in audit_lits]
    return len(both), sum(1 for k in both if lit_value(plan_lits[k]) != lit_value(audit_lits[k]))


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


def bind_plan_of(audit_file):
    """-> (plan path, sha256 or None) the bind dir of the audit records (pre.json / module_check.json 'plan'); (None, None) if unknown"""
    for name in ("pre.json", "module_check.json"):
        try:
            plan = json.loads((Path(audit_file).parent / name).read_text()).get("plan")
        except (OSError, ValueError, AttributeError):
            continue
        if plan:
            try:
                return plan, hashlib.sha256(Path(plan).read_bytes()).hexdigest()
            except OSError:
                return plan, None
    return None, None


def write_for_kit(kit, type_plan, kit_rtl_json, parts=None, strict=None, plan_path=None):
    """write kit/FILE when the type declares count straps; -> the evidence, or None (no file: pin_audit stays strict).
    Ties come from the bound plan's PASS tie audit (sha256 + the bind plan's sha recorded; WARN when that plan differs from the
    kit's plan_path).  A declared strap bit without an audit literal makes the evidence UNVERIFIED: bits with a plan literal use
    it, the rest are listed in unverified_bits; pin_audit warns for all of them (never accepts, never fails).  Report-only
    (COUNT_STRAP_EVIDENCE_WARN) unless strict / OT_STRAP_EVIDENCE_STRICT=1: then UNVERIFIED and any plan-vs-audit literal mismatch raise."""
    if strict is None:
        strict = os.environ.get("OT_STRAP_EVIDENCE_STRICT") == "1"
    if not type_plan.get("count_straps"):
        return None
    have = Path(kit_rtl_json).is_file()
    if not have and not parts:
        return None
    kit_rtl = json.loads(Path(kit_rtl_json).read_text()) if have else {}
    strict = strict or bool(kit_rtl.get("strap_evidence_strict"))   # STRAP-EVIDENCE-PRIV-1124: the kit declared its bind tie audit
    audit_file = find_audit(kit_rtl_json, kit_rtl)
    audit = json.loads(audit_file.read_text()) if audit_file else {}
    lits = audit_literals(audit)
    audit_rows = [[i, p, l] for (i, p), l in lits.items()]
    if kit_rtl.get("instances") and kit_rtl.get("bound_only_pins"):
        evidence = build(type_plan, kit_rtl, dict(verdict="PASS" if lits else "FAIL", rows=audit_rows))
    else:
        shell = dict(instances=sorted(sv_id(i) for i, _ in parts or []), bound_type=kit_rtl.get("bound_type") or kit_rtl.get("plan_type"),
                     bound_only_pins=[dict(port=r["name"], dir="input", width=int(r["width"])) for r in type_plan["count_straps"]])
        evidence = build(type_plan, shell, dict(verdict="PASS" if lits else "FAIL", rows=audit_rows))
    bplan, bsha = bind_plan_of(audit_file) if audit_file else (None, None)
    kit_sha = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest() if plan_path and Path(plan_path).is_file() else None
    evidence["tie_audit"] = dict(path=str(audit_file) if audit_file else None, verdict=audit.get("verdict"),
                                 sha256=hashlib.sha256(audit_file.read_bytes()).hexdigest() if audit_file else None,
                                 bind_plan=bplan, bind_plan_sha256=bsha, kit_plan_sha256=kit_sha)
    warns = []
    if bsha and kit_sha and bsha != kit_sha:
        warns.append(f"bind plan sha {bsha[:12]} differs from the kit plan sha {kit_sha[:12]} (audit {audit_file})")
    plan_lits = plan_literals(type_plan, parts or [])
    gaps = missing_bits(type_plan, evidence)
    evidence["verification"] = "UNVERIFIED" if gaps else "VERIFIED"
    if gaps:
        unv = {}
        for (inst, port), lit in plan_lits.items():
            unv.setdefault(port, {})[inst] = lit
        evidence["unverified_parent_ties"] = unv
        evidence["parent_ties"] = unv
        evidence["parent_ties_source"] = "plan partitions[].id_straps (no PASS bind tie audit literal)"
        evidence["unverified_bits"] = gaps
        why = "NO PASS bind tie audit found (set OT_BIND_TIE_AUDIT=<abs path of the bound plan tie_audit.json>)" if not lits else \
            "the bind tie audit has no literal for them"
        warns.append(f"{len(gaps)} declared count-strap bit(s) UNVERIFIED, {why}: {gaps[:6]}")
    compared, mism = cross_check(plan_lits, lits)
    if mism:
        warns.append(f"{mism} of {compared} plan literals differ from the bind tie audit")
    print(f"COUNT_STRAP_EVIDENCE_CHECK {evidence['verification']} audit={evidence['tie_audit']['verdict']} audit_rows={len(lits)} "
          f"plan_literals={len(plan_lits)} compared={compared} mismatch={mism} unverified_bits={len(gaps)}")
    for w in warns:
        print("COUNT_STRAP_EVIDENCE_WARN " + w)
    if strict and (gaps or mism):
        raise ValueError("count_strap_evidence: " + "; ".join(warns))
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
