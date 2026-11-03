#!/usr/bin/env python3
"""HBM plan event: put the clock pins of every hard-core pin table at the plan clock entry (METHODOLOGY 12.8a).

DIE-HBM-60 11-03 (COORD 11-03 00:2x (4)): a plan-defined centre clock entry is the approved form. Land the clock-entry
pin event for every HBM wave kit on the e96f24182 src form in the plan of record, then drop the APPROVED_PIN_EVENTS
exception.  The kit generator (gen_core_kit_hbm.py --clock-pin-entry on) already moves each clock pin from the pin
table's face point to the module's clock_entries.json entry (plan_clock_entries) and places it with clock_entry_pin.
The plan-of-record pin table kept the face point, so every such kit reads as 'moved pin' against the POR.

This tool makes the pin TABLE carry what the kit places. For each hard-core pins file named by the plan it writes
<stem>__centry.json with every clock pin that the generator moves at the generator's entry centre. It uses the same
functions, imported from gen_core_kit_hbm.py, so the numbers are identical by construction. It repoints the
hard_cores rows and writes centry_event.json (per table: pins moved, entry, old/new pins file).  Pins files of --keep
modules (signed designs whose routed DB is the record) are not touched.  --check-kit plan_pins.json ... compares the
predicted clock pins with built kits (exact centre, layer) and fails on any difference.

Usage: clock_entry_pins.py PLAN_DIR [--plan die_plan.json] [--keep MOD ...] [--write OUT_DIR] [--check-kit F ...]
OUT_DIR gets die_plan.json (repointed) + cores/<stem>__centry.json + centry_event.json; other sidecars are not copied.
"""
import argparse
import copy
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "physical/die_plan/hbm_arch_cores"))
sys.path.insert(0, str(REPO / "tools/die_plan"))
import gen_core_kit_hbm as G  # noqa: E402  (clock_entry_pin, plan_clock_entries, CLK_RE)

SCHEMA = "opentallas.hbm_clock_entry_pin_event.v1"


def jload(p):
    p = Path(p)
    raw = p.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def pins_list(doc):
    """pin table -> (list of pin dicts, setter(list) -> doc).  Tables are a bare list or {'pins': [...]}."""
    if isinstance(doc, list):
        return doc, (lambda L: L)
    if isinstance(doc, dict) and isinstance(doc.get("pins"), list):
        return doc["pins"], (lambda L: dict(doc, pins=L))
    raise ValueError("unknown pin table form")


def resolve(plan_dir, pf):
    for q in (Path(plan_dir) / pf, Path(plan_dir) / (pf + ".gz"), Path(plan_dir) / "cores" / Path(pf).name,
              Path(plan_dir) / "cores" / (Path(pf).name + ".gz")):
        if q.is_file():
            return q
    return None


def m5_of(P):
    import schema as S   # same layer table as schema.Plan(P).layers (the generator's --clock-pin-entry m5)
    L5 = {L["name"]: L for L in P["die"].get("layers", S.ASAP7_LAYERS)}.get("M5")
    return float(L5["offset_um"]), float(L5["pitch_um"])


def pname(p):
    """pin name of a table row: name, or bus[bit] for bus/bit rows"""
    if "name" in p:
        return p["name"]
    return p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]"


def entry_pins(entries, module, pins, w, h, m5):
    """the generator's clock-entry positions for this table: {name: (x, y)} of the clock pins it moves."""
    base = lambda n: re.sub(r"\[\d+\]$", "", n)
    clks = [pname(p) for p in pins if re.match(G.CLK_RE, base(pname(p)))]
    if not clks:
        return {}, None
    moved, rec = G.plan_clock_entries(entries, module, clks, w, h, m5)
    out = {}
    for p in pins:
        n = pname(p)
        if n not in moved or p.get("layer") != "M5":
            continue
        x, y = moved[n]
        if abs(p["x"] - x) <= 1e-4 and abs(p["y"] - y) <= 1e-4:
            continue
        cx, cy, _, _ = G.clock_entry_pin(dict(p, x=x, y=y), w, h, m5)
        out[n] = (cx, cy)
    return out, rec


def run(plan_dir, plan_file=None, keep=(), write=None):
    plan_dir = Path(plan_dir)
    pp = Path(plan_file) if plan_file else next(q for q in (plan_dir / "die_plan.json", plan_dir / "die_plan.json.gz")
                                                 if q.is_file())
    P = jload(pp)
    entries = plan_dir / "clock_entries.json"
    m5 = m5_of(P)
    keep = set(keep)
    seen, ledger, new_files = {}, {}, {}
    for tk, v in (P.get("partition_types") or {}).items():
        for hc in v.get("hard_cores") or []:
            m, pf = hc.get("module"), hc.get("pins_file")
            if not m or not pf or (m, pf) in seen:
                continue
            w, h = (float(x) for x in hc["outline_um"])
            seen[(m, pf)] = None
            key = f"{m}|{pf}"
            if m in keep:
                ledger[key] = dict(module=m, pins_file=pf, status="KEPT (signed record)")
                continue
            q = resolve(plan_dir, pf)
            if q is None:
                ledger[key] = dict(module=m, pins_file=pf, status="NO PINS FILE")
                continue
            doc = jload(q)
            try:
                pins, setp = pins_list(doc)
            except ValueError:
                ledger[key] = dict(module=m, pins_file=pf, status="UNKNOWN TABLE FORM")
                continue
            try:
                mv, rec = entry_pins(entries, m, pins, w, h, m5)
            except SystemExit as e:
                ledger[key] = dict(module=m, pins_file=pf, status=f"GEN REFUSES: {e}")
                continue
            if not mv:
                ledger[key] = dict(module=m, pins_file=pf, status="UNCHANGED (table at entry or no entry)")
                continue
            newp = [dict(p, x=mv[pname(p)][0], y=mv[pname(p)][1]) if pname(p) in mv else p for p in pins]
            stem = Path(pf).name
            for sfx in (".gz", ".json"):
                stem = stem[: -len(sfx)] if stem.endswith(sfx) else stem
            npf = str(Path(pf).parent / f"{stem}__centry.json")
            seen[(m, pf)] = npf
            new_files[npf] = setp(newp)
            ledger[key] = dict(module=m, pins_file=pf, new_pins_file=npf, status="MOVED",
                               moved={n: list(xy) for n, xy in sorted(mv.items())},
                               old={pname(p): [p["x"], p["y"]] for p in pins if pname(p) in mv},
                               entry=(rec or {}).get("xy_um"))
    Q = copy.deepcopy(P)
    for tk, v in (Q.get("partition_types") or {}).items():
        for hc in v.get("hard_cores") or []:
            k = (hc.get("module"), hc.get("pins_file"))
            if seen.get(k):
                hc["pins_file"] = seen[k]
    st = [r["status"] for r in ledger.values()]
    ev = dict(schema=SCHEMA, plan=str(pp), plan_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),
              clock_entries_sha256=hashlib.sha256(entries.read_bytes()).hexdigest() if entries.is_file() else None,
              keep=sorted(keep), rule="METHODOLOGY 12.8a plan clock entry; gen_core_kit_hbm plan_clock_entries + "
              "clock_entry_pin (DIE-HBM-60, COORD 11-03 00:2x (4))",
              summary=dict(tables=len(st), moved=st.count("MOVED"), kept=sum(s.startswith("KEPT") for s in st),
                           refused=sum(s.startswith("GEN REFUSES") for s in st),
                           missing=st.count("NO PINS FILE"), unknown=st.count("UNKNOWN TABLE FORM")),
              tables=ledger)
    if write:
        out = Path(write)
        (out / "cores").mkdir(parents=True, exist_ok=True)
        for npf, d in new_files.items():
            (out / npf).parent.mkdir(parents=True, exist_ok=True)
            (out / npf).write_text(json.dumps(d) + "\n")
        (out / "die_plan.json").write_text(json.dumps(Q, indent=1) + "\n")
        (out / "centry_event.json").write_text(json.dumps(ev, indent=1) + "\n")
    return ev, Q, new_files


def check_kits(ev, kit_pins):
    """kit plan_pins.json files -> (pins matched, mismatches) between kit clock pins and the event's positions.
    Only kits whose pins source is the same table (file name) are compared."""
    bysrc = {}
    for r in ev["tables"].values():
        if r["status"] == "MOVED":
            bysrc[(r["module"], Path(r["pins_file"]).name.replace(".gz", ""))] = r
    bad, ok, used = [], 0, 0
    for f in kit_pins:
        d = jload(f)
        m = str(d.get("view", "")).split("@")[0] or d.get("module")
        r = bysrc.get((d.get("module") or m, Path(str(d.get("source", ""))).name.replace(".gz", "")))
        if r is None:
            continue
        used += 1
        kp = d["pins"] if isinstance(d["pins"], dict) else {p["name"]: p for p in d["pins"]}
        for n, (x, y) in r["moved"].items():
            k = kp.get(n)
            if not k or k.get("layer") != "M5" or abs(k["x"] - x) > 1e-3 or abs(k["y"] - y) > 1e-3:
                bad.append(dict(kit=str(f), pin=n, event=[x, y], kit_xy=[k and k.get("x"), k and k.get("y")]))
            else:
                ok += 1
    return used, ok, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_dir")
    ap.add_argument("--plan")
    ap.add_argument("--keep", nargs="*", default=[])
    ap.add_argument("--write")
    ap.add_argument("--check-kit", nargs="*", default=[])
    a = ap.parse_args(argv)
    ev, _, _ = run(a.plan_dir, a.plan, a.keep, a.write)
    print(json.dumps(ev["summary"]))
    if a.check_kit:
        used, ok, bad = check_kits(ev, a.check_kit)
        print(json.dumps(dict(kits_compared=used, kit_pins_match=ok, kit_pins_mismatch=len(bad), examples=bad[:8])))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
