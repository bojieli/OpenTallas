#!/usr/bin/env python3
"""view_pg_port.py (C-VIEW-PG-PORT-STALE, S81-INT-R3-VIEWS 11-27): hard-macro LEF VDD/VSS PORT geometry must equal the signed routed DEF.

ot_s81_sstn_base566 was published with M5 VDD/VSS PORTs at 2.70 um pitch while the signed routed body (DEF e68dd0ecbc8d) has them at
4.32 um: the parent's PDN connects to ports that do not exist in the body (hand-built abstract, never regenerated from the signed DB).

  view_pg_port.py contract --signed-def DEF [--signed-def DEF ...] --out CONTRACT.json     contract of the signed bodies (PG PORT rects, DBU)
  view_pg_port.py check PLAN.json [--contract C.json] [--repo DIR] [--json OUT]            REPORT-ONLY: every hard_cores LEF vs contract
  view_pg_port.py check-lef --contract C.json LEF [LEF ...]                                the same for single LEFs
  view_pg_port.py regen --contract C.json --lef LEF --out LEF2                             PORT-only rewrite (signal pins, OBS, size byte-identical)

Per master the check compares, for VDD and VSS: rect count, set of x0 (x position) and set of widths, then the full rect set.
rc is 0 on report unless --strict (blocking use is OWNER-decided after calibration).
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

PG = ("VDD", "VSS")
SCHEMA = "s81.signed_core_pg.v1"
CONTRACT_REL = "physical/die_plan/s81/inputs/core_pg_signed.json"
LEF_SHAPE = re.compile(r"\b(LAYER|RECT)\s+([^;]+);")
DEF_RECT = re.compile(r"\+ LAYER (M\d+)\s+\( (-?\d+) (-?\d+) \)\s+\( (-?\d+) (-?\d+) \)")
PORT_ORIGIN = re.compile(r"\+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \) N")
LEF_RECT_LINE = re.compile(r"(?m)^([ \t]*)RECT\s+[^;]+;[ \t]*\n?")


def lef_pin(text, pin):
    found = re.search(rf"(?ms)^\s*PIN {pin}[ \t]*\n(.*?)^[ \t]*END {pin}[ \t]*$", text)
    if not found:
        raise ValueError(f"Missing LEF pin {pin}")
    return found


def lef_macro(text):
    m = re.search(r"(?m)^\s*MACRO\s+(\S+)", text)
    return m[1] if m else None


def lef_ports(text, units):
    """-> {net: set((layer, x0, y0, x1, y1))} in DBU of the contract (units per um)"""
    result = {}
    for pin in PG:
        content = lef_pin(text, pin)[1]
        layer = None
        shapes = []
        if re.search(r"(?m)^\s*(POLYGON|PATH|VIA)\b", content):
            raise ValueError(f"Unsupported LEF shape in {pin} supply port")
        for kind, definition in LEF_SHAPE.findall(content):
            if kind == "LAYER":
                layer = definition.split()[0]
                continue
            values = [Decimal(v) * units for v in definition.split()]
            if not layer or len(values) != 4:
                raise ValueError(f"Invalid {pin} LEF rectangle {definition}")
            shapes.append((layer, *(int(v) if v == v.to_integral_value() else v for v in values)))
        if not shapes:
            raise ValueError(f"No LEF rectangles for {pin}")
        result[pin] = set(shapes)
    return result


def signed_ports(path):
    raw = Path(path).read_bytes()
    text = raw.decode()
    master = re.search(r"(?m)^DESIGN (\S+) ;$", text)[1]
    units = int(re.search(r"(?m)^UNITS DISTANCE MICRONS (\d+) ;$", text)[1])
    pins = re.search(r"(?ms)^PINS \d+ ;\n(.*?)^END PINS$", text)[1]
    result = {}
    for pin in PG:
        body = re.search(rf"(?ms)^[ \t]*- {pin} \+ NET {pin}\b(.*?);", pins)[1]
        parts = body.split("+ PORT")[1:]
        if not parts:
            raise ValueError(f"No routed DEF {pin} port")
        shapes = []
        for part in parts:
            origin = PORT_ORIGIN.findall(part)
            rects = DEF_RECT.findall(part)
            if len(origin) != 1 or not rects or len(rects) != part.count("+ LAYER "):
                raise ValueError(f"Unsupported exact routed DEF port geometry for {pin}")
            x, y = map(int, origin[0])
            for layer, *r in rects:
                x0, y0, x1, y1 = map(int, r)
                shapes.append((layer, x + x0, y + y0, x + x1, y + y1))
        result[pin] = sorted(set(shapes))
    return master, dict(units_per_um=units, source_def_sha256=hashlib.sha256(raw).hexdigest(), ports=result)


def load_contract(path):
    data = json.loads(Path(path).read_text())
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported signed PG contract in {path}")
    return data["masters"]


def compare(lef_text, contract):
    """-> (ok, {net: {...count, x, width, rects}}) ; contract = one master's entry"""
    actual = lef_ports(lef_text, contract["units_per_um"])
    rep, ok = {}, True
    for net in PG:
        exp = {tuple(s) for s in contract["ports"][net]}
        act = actual[net]
        r = {
            "count": [len(exp), len(act)],
            "x0": [sorted({s[1] for s in exp}) == sorted({s[1] for s in act})],
            "width": [sorted(Counter(s[3] - s[1] for s in exp).items()) == sorted(Counter(s[3] - s[1] for s in act).items())],
            "missing": len(exp - act),
            "extra": len(act - exp),
        }
        r["equal"] = not (exp ^ act)
        ok = ok and r["equal"]
        rep[net] = r
    return ok, rep


def regenerate(lef_text, contract, master):
    """Rewrite only the rectangular PG PORT data (same layer); everything else is left byte-identical."""
    units = contract["units_per_um"]
    result = lef_text
    for net in PG:
        pin = lef_pin(result, net)
        expected = contract["ports"][net]
        prior_layers = set(re.findall(r"\bLAYER\s+(M\d+)\s*;", pin[1]))
        if len(prior_layers) != 1 or prior_layers != {r[0] for r in expected}:
            raise ValueError(f"{master} {net} layer changed; preserve the specific LEF port contract")
        capture = list(LEF_RECT_LINE.finditer(pin[1]))
        if (not capture or len(re.findall(r"(?m)^\s*PORT\s*$", pin[1])) != 1
                or pin[1][capture[0].start():capture[-1].end()] != "".join(m[0] for m in capture)):
            raise ValueError(f"{master} {net} LEF supply rectangles are not one contiguous PORT")
        lines = []
        for _, *rect in sorted(expected, key=lambda rec: (rec[1], rec[2]), reverse=True):
            coords = " ".join(format(Decimal(v) / units, ".3f") for v in rect)
            lines.append(f"{capture[0][1]}RECT  {coords} ;\n")
        begin = pin.start(1) + capture[0].start()
        end = pin.start(1) + capture[-1].end()
        result = result[:begin] + "".join(lines) + result[end:]
    ok, rep = compare(result, contract)
    if not ok:
        raise ValueError(f"{master} regenerated LEF still differs from the signed DEF: {rep}")
    return result


def _resolve(lef, bases):
    p = Path(lef)
    if p.is_absolute():
        return p if p.is_file() else None
    for b in bases:
        if b and (Path(b) / lef).is_file():
            return Path(b) / lef
    return None


def plan_check(raw, contracts, plan_path=None, repo=None):
    """-> (lines, records): one record per distinct (LEF, master); a LEF not on disk is reported 'unresolved', a master without a contract 'nocontract'"""
    pp = Path(plan_path) if plan_path else None
    bases = [repo] + ([pp.parent, *pp.parents] if pp else [])
    seen = {}
    for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
        for h in (t or {}).get("hard_cores") or []:
            lef = h.get("lef") if isinstance(h, dict) else None
            if lef:
                seen.setdefault(str(lef), []).append(tn)
    records, lines, cache = [], [], {}
    for lef, types in sorted(seen.items()):
        f = _resolve(lef, bases)
        if f is None:
            records.append(dict(lef=lef, status="unresolved", pointers=len(types)))
            continue
        text = f.read_text(errors="replace")
        master = lef_macro(text)
        if master not in contracts:
            records.append(dict(lef=lef, master=master, status="nocontract", pointers=len(types)))
            continue
        try:
            ok, rep = compare(text, contracts[master])
        except ValueError as e:
            records.append(dict(lef=lef, master=master, status="unread", detail=str(e), pointers=len(types)))
            lines.append(f"REPORT VIEW-PG-PORT {master}: {lef} unreadable ({e}); {len(types)} pointers")
            continue
        records.append(dict(lef=lef, master=master, status="ok" if ok else "DIFF", pointers=len(types), nets=rep,
                            signed_def=contracts[master]["source_def_sha256"][:12]))
        if not ok:
            d = "; ".join(f"{n} count {r['count'][1]}/{r['count'][0]} x0{'=' if r['x0'][0] else '!='} width{'=' if r['width'][0] else '!='}"
                          for n, r in rep.items())
            lines.append(f"REPORT VIEW-PG-PORT {master}: LEF {lef} PG PORT != signed DEF {contracts[master]['source_def_sha256'][:12]} "
                         f"({d}); {len(types)} pointers")
    return lines, records


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("contract")
    c.add_argument("--signed-def", type=Path, action="append", required=True)
    c.add_argument("--out", type=Path, required=True)
    k = sub.add_parser("check")
    k.add_argument("plan", type=Path)
    k.add_argument("--contract", type=Path)
    k.add_argument("--repo", type=Path)
    k.add_argument("--json", type=Path)
    k.add_argument("--strict", action="store_true")
    kl = sub.add_parser("check-lef")
    kl.add_argument("--contract", type=Path, required=True)
    kl.add_argument("lef", type=Path, nargs="+")
    kl.add_argument("--strict", action="store_true")
    r = sub.add_parser("regen")
    r.add_argument("--contract", type=Path, required=True)
    r.add_argument("--lef", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "contract":
        masters = {}
        for d in a.signed_def:
            m, ct = signed_ports(d)
            masters[m] = ct
        a.out.write_text(json.dumps(dict(schema=SCHEMA, masters=masters), indent=2) + "\n")
        return 0
    if a.cmd == "regen":
        text = a.lef.read_text()
        m = lef_macro(text)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(regenerate(text, load_contract(a.contract)[m], m))
        return 0
    if a.cmd == "check-lef":
        contracts = load_contract(a.contract)
        bad = 0
        for p in a.lef:
            text = p.read_text()
            m = lef_macro(text)
            if m not in contracts:
                print(f"{p}: {m} no contract")
                continue
            ok, rep = compare(text, contracts[m])
            print(f"{p}: {m} {'ok' if ok else 'DIFF ' + json.dumps(rep)}")
            bad += not ok
        return 1 if (bad and a.strict) else 0
    plan = json.loads(a.plan.read_text())
    contract = a.contract
    if contract is None:
        for b in [a.repo, a.plan.parent, *a.plan.parents]:
            if b and (Path(b) / CONTRACT_REL).is_file():
                contract = Path(b) / CONTRACT_REL
                break
        if contract is None:
            print(f"view_pg_port: no contract ({CONTRACT_REL})", file=sys.stderr)
            return 2
    lines, recs = plan_check(plan, load_contract(contract), a.plan, a.repo)
    for ln in lines:
        print(ln)
    n = Counter(r["status"] for r in recs)
    ptr = Counter()
    for r in recs:
        ptr[r["status"]] += r["pointers"]
    print(f"VIEW-PG-PORT summary: LEFs {dict(n)} pointers {dict(ptr)}")
    if a.json:
        a.json.write_text(json.dumps(recs, indent=1) + "\n")
    return 1 if (a.strict and n.get("DIFF")) else 0


if __name__ == "__main__":
    sys.exit(main())
