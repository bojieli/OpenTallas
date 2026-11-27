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
HEAD_KIT_SCHEMA = "opentallas.head_wave_kit_rtl.v1"
HEAD_AUDIT_RECEIPT_FIELDS = {"tie_audit_plan_sha256", "tie_audit_sha256", "tie_audit_source"}
SHA256 = re.compile(r"[0-9a-f]{64}")


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


def bind_plan_records(audit_file):
    """Read legacy neighboring plan paths and hash the files still available."""
    for name in ("pre.json", "module_check.json"):
        try:
            plan = json.loads((Path(audit_file).parent / name).read_text()).get("plan")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(plan, str) and plan:
            try:
                digest = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
            except OSError:
                digest = None
            yield plan, digest


def bind_plan_of(audit_file):
    """Keep the legacy first-record behavior for bind exports without a direct receipt."""
    return next(bind_plan_records(audit_file), (None, None))


def native_head_bind_plan(receipt, audit_file, audit, audit_sha, kit_sha, plan_data, parts):
    """Verify the copied HEAD export against the caller's actual plan bytes.

    The exporter is the authority for the audit file hash. A standalone copy
    needs no original plan path, but any accessible original must agree.
    """
    native_type = receipt.get("plan_type")
    declared_copy = receipt.get("tie_audit")
    declared_source = receipt.get("tie_audit_source")
    if (receipt.get("schema") != HEAD_KIT_SCHEMA or not isinstance(native_type, str)
            or not parts or any(part.get("type") != native_type for _, part in parts)
            or not isinstance(declared_copy, str) or not isinstance(declared_source, str) or not declared_source
            or not Path(declared_copy).is_absolute() or Path(declared_copy).name != audit_file.name):
        raise ValueError("invalid HEAD kit tie-audit receipt")
    if not audit_sha or receipt.get("tie_audit_sha256") != audit_sha:
        raise ValueError("copied HEAD tie-audit sha256 differs from its export receipt")
    for recorded in (Path(declared_copy), Path(declared_source)):
        if recorded.is_file() and hashlib.sha256(recorded.read_bytes()).hexdigest() != audit_sha:
            raise ValueError(f"copied HEAD tie audit differs from {recorded}")

    accepted = audit.get("accepted")
    plan = audit.get("plan")
    top_sha = audit.get("top_sha256")
    if (audit.get("verdict") != "PASS" or audit.get("rejected") != []
            or type(audit.get("rows")) is not int or not isinstance(accepted, list)
            or audit["rows"] != len(accepted)
            or not isinstance(top_sha, str) or not SHA256.fullmatch(top_sha)
            or not isinstance(plan, str) or not Path(plan).is_absolute()):
        raise ValueError("copied HEAD tie audit lacks a complete native PASS receipt")
    names = set()
    for row in accepted:
        if (not isinstance(row, list) or len(row) != 2
                or not isinstance(row[0], str) or not all(row[0].rpartition(".")[::2])
                or not isinstance(row[1], str) or row[0] in names):
            raise ValueError("copied HEAD tie audit has invalid or duplicate accepted rows")
        try:
            width, value = lit_value(row[1])
            if width < 1 or value < 0 or value.bit_length() > width:
                raise ValueError
        except (IndexError, KeyError, ValueError) as exc:
            raise ValueError("copied HEAD tie audit has an invalid accepted literal") from exc
        names.add(row[0])

    bind_sha = audit.get("plan_sha256")
    if not kit_sha or bind_sha != kit_sha or bind_sha != receipt.get("tie_audit_plan_sha256"):
        raise ValueError("HEAD audit, export receipt and supplied plan sha256 do not agree")
    expected = {part["name"] for part in json.loads(plan_data).get("partitions", [])
                if part.get("type") == native_type}
    if {name for name, _ in parts} != expected:
        raise ValueError("HEAD export instance inventory differs from the supplied plan")
    if ((Path(plan).is_file() and hashlib.sha256(Path(plan).read_bytes()).hexdigest() != bind_sha)
            or any(digest and digest != bind_sha for _, digest in bind_plan_records(audit_file))):
        raise ValueError("native HEAD plan sha256 disagrees with the available bound plan")
    return plan, bind_sha


def write_for_kit(kit, type_plan, kit_rtl_json, parts=None, strict=None, plan_path=None):
    """write kit/FILE when the type declares count straps; -> the evidence, or None (no file: pin_audit stays strict).
    Ties come from the bound plan's PASS tie audit (sha256 + the bind plan's sha recorded; WARN when that plan differs from the
    kit's plan_path on the legacy path). A copied HEAD export must match the supplied plan.
    A declared strap bit without an audit literal makes the evidence UNVERIFIED: bits with a plan literal use
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
    parts = list(parts or [])
    native = bool(HEAD_AUDIT_RECEIPT_FIELDS & kit_rtl.keys())
    audit_file = Path(kit_rtl_json).with_name("tie_audit.json") if native else find_audit(kit_rtl_json, kit_rtl)
    plan_data = Path(plan_path).read_bytes() if plan_path and Path(plan_path).is_file() else None
    kit_sha = hashlib.sha256(plan_data).hexdigest() if plan_data is not None else None
    audit, audit_sha, native_error = {}, None, None
    bplan = bsha = None
    try:
        if audit_file:
            data = audit_file.read_bytes()
            audit_sha = hashlib.sha256(data).hexdigest()
            audit = json.loads(data)
        if native:
            if not isinstance(audit, dict):
                raise ValueError("copied HEAD tie audit must be a JSON object")
            bplan, bsha = native_head_bind_plan(kit_rtl, audit_file, audit, audit_sha, kit_sha, plan_data, parts)
        elif audit_file:
            bplan, bsha = bind_plan_of(audit_file)
    except (OSError, ValueError) as exc:
        if not native:
            raise
        native_error = str(exc)
    lits = audit_literals(audit) if not native_error else {}
    plan_lits = plan_literals(type_plan, parts)
    compared, mism = cross_check(plan_lits, lits)
    if native and mism:
        native_error = f"{mism} of {compared} plan literals differ from the copied HEAD tie audit"
        bplan = bsha = None
        lits = {}
    audit_rows = [[i, p, l] for (i, p), l in lits.items()]
    if not native and kit_rtl.get("instances") and kit_rtl.get("bound_only_pins"):
        evidence = build(type_plan, kit_rtl, dict(verdict="PASS" if lits else "FAIL", rows=audit_rows))
    else:
        shell = dict(instances=sorted(sv_id(i) for i, _ in parts or []), bound_type=kit_rtl.get("bound_type") or kit_rtl.get("plan_type"),
                     bound_only_pins=[dict(port=r["name"], dir="input", width=int(r["width"])) for r in type_plan["count_straps"]])
        evidence = build(type_plan, shell, dict(verdict="PASS" if lits else "FAIL", rows=audit_rows))
    evidence["tie_audit"] = dict(path=str(audit_file) if audit_file else None,
                                 verdict=audit.get("verdict") if isinstance(audit, dict) else None,
                                 sha256=audit_sha, bind_plan=bplan, bind_plan_sha256=bsha, kit_plan_sha256=kit_sha)
    warns = []
    if native_error:
        warns.append("copied HEAD tie audit refused: " + native_error)
    if bsha and kit_sha and bsha != kit_sha:
        warns.append(f"bind plan sha {bsha[:12]} differs from the kit plan sha {kit_sha[:12]} (audit {audit_file})")
    gaps = missing_bits(type_plan, evidence)
    evidence["verification"] = "UNVERIFIED" if gaps or native_error else "VERIFIED"
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
    if mism and not native_error:
        warns.append(f"{mism} of {compared} plan literals differ from the bind tie audit")
    print(f"COUNT_STRAP_EVIDENCE_CHECK {evidence['verification']} audit={evidence['tie_audit']['verdict']} audit_rows={len(lits)} "
          f"plan_literals={len(plan_lits)} compared={compared} mismatch={mism} unverified_bits={len(gaps)}")
    for w in warns:
        print("COUNT_STRAP_EVIDENCE_WARN " + w)
    if strict and (gaps or mism or native_error):
        raise ValueError("count_strap_evidence: " + "; ".join(warns))
    (Path(kit) / FILE).parent.mkdir(parents=True, exist_ok=True)
    (Path(kit) / FILE).write_text(json.dumps(evidence, indent=1) + "\n")
    return evidence


def main(argv):
    plan, tn, kit_rtl_json, kit = argv
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pin_audit import accepted_count_strap_bits
    raw = json.loads(Path(plan).read_text())
    parts = [(part["name"], part) for part in raw.get("partitions", []) if part["type"] == tn]
    evidence = write_for_kit(kit, raw["partition_types"][tn], kit_rtl_json, parts=parts, plan_path=plan)
    bits = sorted(accepted_count_strap_bits(evidence or {}))
    print(f"COUNT_STRAP_EVIDENCE {tn} straps {len((evidence or {}).get('plan_count_straps', []))} accepted_bits {len(bits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
