"""P-RESET-RECEIPT (HEAD-INT-R2, FABLE-INDEP 08:46 W10 packet, FABLE-FLOW-0847 B18): the reset form of a type.

A type's signed / counted release receipt (bind, LAT, G0, route sign-off) was produced on ONE form of its reset: the raw START exports
and their seats, the relay names and sites of its published reset tree, the START stages of its landing contract and the die reset
IN site.  W10 renamed / re-seated those on counted types that were not rebuilt (hd_st_n4: 8 raw exports, start capture 498.8,750.6 ->
479.5,720.0, in_site 918.6 -> 718.8) and the old receipt was inherited.  This module hashes that form per type, so a receipt can be
bound to it:

  form_hash(raw, type)      sha256 of the canonical reset form (floats rounded to 1e-3 um, keys sorted)
  forms(raw, types=None)    {type: {"sha256": ..., "sections": {name: sha256}}}
  compare(cur, receipts)    per type: SAME | RE-SIGN-REQUIRED (+ the sections that differ) | NO-RECEIPT

A RE-SIGN-REQUIRED type is a per-type verdict (its signed record no longer describes the plan's reset): it is never a die-gate FAIL and
never blocks the other types.  CLI (read-only, seconds, no solve):

  python3 -I reset_form.py emit  PLAN [--types a,b] [--out forms.json]
  python3 -I reset_form.py check PLAN (--receipts forms.json | --signed-plan SIGNED_PLAN) [--types a,b] [--json OUT] [--strict]

--receipts: a file written by `emit` on the plan the types were signed on (or a hand-built {"types": {type: {"form_sha256": ...}}}).
--signed-plan: the plan the type(s) were signed on (its forms are the receipts); `type=PLAN` (repeatable) names one plan per type.
--strict makes the exit status 3 when any type is RE-SIGN-REQUIRED (default 0: a flag, not a failure).
"""
import argparse
import fnmatch
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "opentallas.reset_forms.v1"
RESIGN = "RE-SIGN-REQUIRED"
DIE_RESET_SCALARS = ("sync_stages", "release", "start", "data_reset", "epoch_bit", "root_part", "reach_cap_um", "relay_site_rule")
CLOCK_START_KEYS = ("start_capture_um", "landing_reader_start", "landing_writer_start", "landing_local_resets", "landing_export_form")
RELAY_KEYS = ("q", "xy", "depth", "kind", "tap", "name", "site")


def _canon(o):
    if isinstance(o, float):
        return round(o, 3)
    if isinstance(o, dict):
        return {str(k): _canon(v) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))}
    if isinstance(o, (list, tuple)):
        return [_canon(v) for v in o]
    return o


def _sha(o):
    return hashlib.sha256(json.dumps(_canon(o), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree(ck):
    """published reset tree of the landing contract: relay names / sites only (a timing-only edit of the tree does not change the form)"""
    ct = ((ck or {}).get("landing_contract") or {}).get("collector_tree") or {}
    rel = []
    for r in ct.get("relays") or []:
        if isinstance(r, dict):
            rel.append({k: r.get(k) for k in RELAY_KEYS if k in r})
    rel.sort(key=lambda r: json.dumps(_canon(r), sort_keys=True))
    return {"root": ct.get("root"), "relays": rel}


def sections(raw, tn):
    """{section name: canonical content} of the type's reset form; {} when the type is unknown"""
    t = ((raw or {}).get("partition_types") or {}).get(tn)
    if not isinstance(t, dict):
        return {}
    ck = t.get("clock") or {}
    dr = (raw or {}).get("reset") or {}
    rst = t.get("reset") or {}
    return {
        "type_reset": {k: v for k, v in rst.items() if k != "export_seats_um"},
        "export_seats_um": rst.get("export_seats_um") or {},
        "raw_exports": t.get("reset_start_raw_exports") or [],
        "private_exports": t.get("private_reset_start_exports"),
        "start_stages": {k: ck.get(k) for k in CLOCK_START_KEYS if k in ck},
        "reset_tree": _tree(ck),
        "die_reset": {**{k: dr.get(k) for k in DIE_RESET_SCALARS if k in dr}, "in_site": (dr.get("in_sites") or {}).get(tn)},
    }


def form_hash(raw, tn):
    s = sections(raw, tn)
    return _sha(s) if s else None


def forms(raw, types=None):
    out = {}
    for tn in sorted((raw or {}).get("partition_types") or {}):
        if types and not any(fnmatch.fnmatchcase(tn, g) for g in types):
            continue
        s = sections(raw, tn)
        if s:
            out[tn] = {"sha256": _sha(s), "sections": {k: _sha(v) for k, v in s.items()}}
    return out


def compare(cur, receipts):
    """cur: forms() of the plan; receipts: {type: form dict | {"form_sha256"|"sha256": ...} | sha string}
    -> {type: {"verdict": SAME | RE-SIGN-REQUIRED | NO-RECEIPT, "changed": [sections]}}"""
    res = {}
    for tn, f in sorted(cur.items()):
        r = (receipts or {}).get(tn)
        if r is None:
            res[tn] = {"verdict": "NO-RECEIPT", "changed": []}
            continue
        rsha = r if isinstance(r, str) else (r.get("form_sha256") or r.get("sha256"))
        rsec = (r.get("sections") or {}) if isinstance(r, dict) else {}
        if rsha == f["sha256"]:
            res[tn] = {"verdict": "SAME", "changed": []}
        else:
            ch = sorted(k for k in f["sections"] if rsec and rsec.get(k) != f["sections"][k]) if rsec else ["(receipt has no section hashes)"]
            res[tn] = {"verdict": RESIGN, "changed": ch}
    return res


def line(tn, v):
    return f"RESET-RECEIPT {tn}: {v['verdict']}" + (f" (changed: {', '.join(v['changed'])})" if v["changed"] else "")


def _load(p):
    return json.loads(Path(p).read_text())


def _types(s):
    return [x for x in (s or "").split(",") if x] or None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reset_form", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emit")
    e.add_argument("plan")
    e.add_argument("--types")
    e.add_argument("--out")
    c = sub.add_parser("check")
    c.add_argument("plan")
    c.add_argument("--receipts")
    c.add_argument("--signed-plan", action="append", default=[], help="PLAN (all types) or TYPE=PLAN")
    c.add_argument("--types")
    c.add_argument("--json")
    c.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    raw = _load(a.plan)
    doc = {"schema": SCHEMA, "plan": str(Path(a.plan).resolve()), "plan_sha256": hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
           "types": forms(raw, _types(a.types))}
    if a.cmd == "emit":
        txt = json.dumps(doc, indent=1) + "\n"
        if a.out:
            Path(a.out).write_text(txt)
        print(f"reset_form: {len(doc['types'])} type form(s) of plan {doc['plan_sha256'][:12]}" + (f"; wrote {a.out}" if a.out else ""))
        if not a.out:
            print(txt, end="")
        return 0
    receipts = {}
    if a.receipts:
        receipts.update(_load(a.receipts).get("types") or {})
    for sp in a.signed_plan:
        tn, _, path = sp.partition("=") if "=" in sp else ("", "", sp)
        f = forms(_load(path), [tn] if tn else None)
        for k, v in f.items():
            receipts[k] = dict(v, plan_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    if not receipts:
        ap.error("check needs --receipts or --signed-plan")
    res = compare(doc["types"], receipts)
    doc["result"] = res
    doc["resign_required"] = sorted(k for k, v in res.items() if v["verdict"] == RESIGN)
    for tn, v in res.items():
        if v["verdict"] != "SAME":
            print(line(tn, v))
    n = {k: sum(1 for v in res.values() if v["verdict"] == k) for k in ("SAME", RESIGN, "NO-RECEIPT")}
    print(f"RESET-RECEIPT-SUMMARY plan {doc['plan_sha256'][:12]}: {n['SAME']} same, {n[RESIGN]} {RESIGN}, {n['NO-RECEIPT']} no receipt")
    if a.json:
        Path(a.json).write_text(json.dumps(doc, indent=1) + "\n")
    return 3 if a.strict and n[RESIGN] else 0


if __name__ == "__main__":
    sys.exit(main())
