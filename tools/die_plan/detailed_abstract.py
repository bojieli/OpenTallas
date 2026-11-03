#!/usr/bin/env python3
"""Detailed (non-blanket) abstract re-export of a SIGNED hard-core view from its OWN routed 6_final.odb.

Class C (DIE-KV-62/types 11-02, DIE-HEAD-55 11-03 CLASS; PDN-0006 "VSS on M5 is blocked by obstructions on M6, M7"):
a signed core routed to M7 with PG pins on M5 only, exported with ORFS generate_abstract
(write_abstract_lef -bloat_occupied_layers), carries a BLANKET OBS over the whole outline on every layer up to M7.  The
parent tile's M6 straps cannot reach the M5 PG pins anywhere over the core, so the parent PDN stops at floorplan.

This tool is a VIEW EXPORT, not a rebuild: it reads the same signed routed DB (no re-route, no re-place, no ECO) and
writes write_abstract_lef WITHOUT -bloat_occupied_layers, i.e. OBS = the real routed / placed shapes per layer, the
industry-standard detailed abstract.  The timing libs, the netlist and the sign-off record are untouched, so the signed
view stays valid; only its LEF obstruction model is refined.  Fail-closed invariants against the signed LEF:
MACRO name, CLASS, ORIGIN, SIZE, the pin set, every pin's DIRECTION / USE and its PORT rectangles (multiset equal;
a PG pin may lose only the boxes listed by the PG access trim below).

PG access trim (--pg-trim, default 0.9): OpenROAD pdngen (InstanceGrid::checkSetup) sums the raw overlaps of every
OBS box above a PG pin box without merging them (stacked M6 + M7 wires count twice) and stops with PDN-0006 if ONE
box reaches its area, although the net's other boxes are free (KV e1/e5: 1 of 49 M5 VSS strips at 151-170% summed,
91-93% real union).  Such a box is moved from the PIN PORT to OBS on its own layer: no physical change, the pin keeps
every other box, and the record lists each trimmed box.
Die-agnostic: any die, any core (KV head_eighth e0/e1/e2/e5/e6, HEAD ot_s81hd_lep_pair, ...).

    detailed_abstract.py export --odb ODB --signed-lef LEF --out DIR [--odb-sha256 SHA] [--image IMG] [--mem 8g]
        -> DIR/<macro>.lef (detailed) + DIR/<macro>.detailed_abstract.json (provenance + invariants + OBS census)
    detailed_abstract.py check --signed-lef LEF --new-lef LEF      (invariants only; exit 1 on a violation)

Runs OpenROAD in docker (default image openroad/orfs:latest, --memory cap); run it on a fleet host, never localhost.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

IMAGE = "openroad/orfs:latest"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"


class AbstractError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def _num(v):
    return round(float(v), 4)


def parse_lef(text):
    """{name, cls, origin, size, pins{name: {direction, use, rects Counter}}, obs{layer: n_shapes}} of ONE macro."""
    names = re.findall(r"(?m)^\s*MACRO\s+(\S+)\s*$", text)
    if len(names) != 1:
        raise AbstractError(f"expected exactly one MACRO, found {len(names)}")
    m = {"name": names[0], "cls": None, "origin": None, "size": None, "pins": {}, "obs": Counter()}
    sect, pin, layer = None, None, None
    for raw in text.splitlines():
        st = raw.strip()
        if not st or st.startswith("#"):
            continue
        tok = st.rstrip(";").split()
        kw = tok[0]
        if sect is None:
            if kw == "CLASS" and m["cls"] is None:
                m["cls"] = " ".join(tok[1:])
            elif kw == "ORIGIN":
                m["origin"] = tuple(_num(v) for v in tok[1:3])
            elif kw == "SIZE":
                m["size"] = (_num(tok[1]), _num(tok[3]))
            elif kw == "PIN":
                sect, pin = "pin", tok[1]
                m["pins"][pin] = {"direction": None, "use": None, "rects": Counter()}
            elif kw == "OBS":
                sect, layer = "obs", None
        elif sect == "pin":
            if kw == "END" and len(tok) > 1 and tok[1] == pin:
                sect, pin, layer = None, None, None
            elif kw == "DIRECTION":
                m["pins"][pin]["direction"] = " ".join(tok[1:])
            elif kw == "USE":
                m["pins"][pin]["use"] = tok[1]
            elif kw == "LAYER":
                layer = tok[1]
            elif kw in ("RECT", "POLYGON"):
                vals = [v for v in tok[1:] if v not in ("MASK",)]
                m["pins"][pin]["rects"][(layer, kw) + tuple(_num(v) for v in vals)] += 1
        elif sect == "obs":
            if kw == "END":
                sect, layer = None, None
            elif kw == "LAYER":
                layer = tok[1]
            elif kw in ("RECT", "POLYGON", "PATH"):
                m["obs"][layer] += 1
    return m


def obs_boxes(text, above=None):
    """[(layer, x0, y0, x1, y1)] of the OBS section (routing layers Mn, n > above when given)"""
    i = re.search(r"(?m)^\s*OBS\s*$", text)
    out, layer = [], None
    if not i:
        return out
    for raw in text[i.end():].splitlines():
        st = raw.strip()
        if st.startswith("END"):
            break
        if st.startswith("LAYER"):
            layer = st.split()[1]
        elif st.startswith("RECT") and layer:
            mm = re.fullmatch(r"M(\d+)", layer)
            if above is None or (mm and int(mm.group(1)) > above):
                out.append((layer,) + tuple(float(v) for v in st.rstrip(";").split()[1:5]))
    return out


def pdn_summed_overlap(pin_box, obs):
    """OpenROAD pdn InstanceGrid::checkSetup measure (PDN-0006/0007): the SUM of raw (un-merged, un-bloated) overlaps
    of every master OBS box on a routing layer above the pin's top layer, per pin box; >= pin area = PDN-0006 fatal."""
    x0, y0, x1, y1 = pin_box
    s = 0.0
    for _, a, b, c, d in obs:
        w, h = min(x1, c) - max(x0, a), min(y1, d) - max(y0, b)
        if w > 0 and h > 0:
            s += w * h
    return s / max((x1 - x0) * (y1 - y0), 1e-12)


def pg_access_trim(text, threshold):
    """PG pin ACCESS trim (abstract form, no physical change): a POWER/GROUND pin box whose OpenROAD summed overlap
    with the obstructions above it is >= threshold is not a parent access point (pdngen would stop on it: the checker
    double-counts stacked M6+M7 / overlapping boxes and is fatal for ONE such box although the net's other boxes are
    free).  Such a box leaves the PIN PORT and becomes OBS on its own layer (the parent never routes over it); the pin
    keeps every other box, so the net stays reachable.  Returns (text, [(pin, layer, box, summed)])."""
    m = parse_lef(text)
    dropped = []
    out, pin, layer, use = [], None, None, None
    pg = {n for n, p in m["pins"].items() if p["use"] in ("POWER", "GROUND")}
    allobs = [o for o in obs_boxes(text) if re.fullmatch(r"M\d+", o[0])]
    for raw in text.splitlines(keepends=True):
        st = raw.strip()
        tok = st.rstrip(";").split()
        if tok[:1] == ["PIN"] and len(tok) > 1:
            pin, layer = tok[1], None
        elif pin and tok[:1] == ["END"] and len(tok) > 1 and tok[1] == pin:
            pin = None
        elif pin in pg and tok[:1] == ["LAYER"]:
            layer = tok[1]
        elif pin in pg and tok[:1] == ["RECT"] and layer:
            mm = re.fullmatch(r"M(\d+)", layer)
            box = tuple(float(v) for v in tok[1:5])
            if mm:
                f = pdn_summed_overlap(box, [o for o in allobs if int(o[0][1:]) > int(mm.group(1))])
                if f >= threshold:
                    dropped.append((pin, layer, box, round(f, 4)))
                    continue
        out.append(raw)
    text = "".join(out)
    if dropped:
        for n in pg:
            left = sum(1 for (L, *_r) in parse_lef(text)["pins"][n]["rects"])
            if not left:
                raise AbstractError(f"PG pin {n}: every access box is blocked (>= {threshold}); no trim possible")
        add = "".join(f"    LAYER {L} ;\n" + "".join(f"     RECT  {b[0]:g} {b[1]:g} {b[2]:g} {b[3]:g} ;\n"
                                                  for (_p, L2, b, _f) in dropped if L2 == L)
                      for L in sorted({d[1] for d in dropped}))
        i = re.search(r"(?m)^\s*OBS\s*$", text)
        if not i:
            raise AbstractError("no OBS section to receive the trimmed PG boxes")
        j = re.compile(r"(?m)^\s*END\s*$").search(text, i.end())
        text = text[:j.start()] + add + text[j.start():]
    return text, dropped


def check_invariants(signed_text, new_text, pg_trimmed=()):
    a, b = parse_lef(signed_text), parse_lef(new_text)
    bad = []
    for k in ("name", "cls", "origin", "size"):
        if a[k] != b[k]:
            bad.append(f"{k}: signed {a[k]} != new {b[k]}")
    if set(a["pins"]) != set(b["pins"]):
        bad.append(f"pin set differs: only signed {sorted(set(a['pins']) - set(b['pins']))[:5]}, "
                   f"only new {sorted(set(b['pins']) - set(a['pins']))[:5]}")
    for n in sorted(set(a["pins"]) & set(b["pins"])):
        pa, pb = a["pins"][n], b["pins"][n]
        for k in ("direction", "use"):
            if pa[k] != pb[k]:
                bad.append(f"pin {n} {k}: {pa[k]} != {pb[k]}")
        trimmed = Counter((L, "RECT") + tuple(round(v, 4) for v in box) for (p, L, box, _f) in pg_trimmed if p == n)
        if pa["rects"] != pb["rects"] + trimmed:
            bad.append(f"pin {n} PORT shapes differ ({sum(pa['rects'].values())} vs {sum(pb['rects'].values())})")
    return bad, a, b


def export(args):
    odb, slef = Path(args.odb).resolve(), Path(args.signed_lef).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    odb_sha = sha256(odb)
    if args.odb_sha256 and odb_sha != args.odb_sha256:
        raise AbstractError(f"{odb}: sha256 {odb_sha} != expected {args.odb_sha256} (not the signed routed DB)")
    signed_text = slef.read_text()
    macro = parse_lef(signed_text)["name"]
    with tempfile.TemporaryDirectory(dir=out) as td:
        tcl = Path(td) / "abstract.tcl"
        tcl.write_text(f"read_db /in/{odb.name}\n"
                       f"if {{[[ord::get_db_block] getName] ne \"{macro}\"}} {{\n"
                       f"  puts \"OT_DA_BLOCK [[ord::get_db_block] getName]\"\n}}\n"
                       f"write_abstract_lef /tmp_out/{macro}.lef\nexit\n")
        cmd = ["docker", "run", "--rm", "--memory", args.mem, "--name", args.name or f"da-{macro[:40]}-{odb_sha[:8]}",
               "-v", f"{odb.parent}:/in:ro", "-v", f"{td}:/tmp_out", args.image,
               "bash", "-c", f"{OPENROAD} -no_init -exit /tmp_out/abstract.tcl"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"{macro}.detailed_abstract.log").write_text(r.stdout + r.stderr)
        new_lef = Path(td) / f"{macro}.lef"
        if r.returncode != 0 or not new_lef.is_file():
            raise AbstractError(f"openroad export failed rc {r.returncode}: {(r.stdout + r.stderr)[-800:]}")
        new_text = new_lef.read_text()
    raw_sha = hashlib.sha256(new_text.encode()).hexdigest()
    dropped = []
    if args.pg_trim is not None and args.pg_trim > 0:
        new_text, dropped = pg_access_trim(new_text, args.pg_trim)
    bad, a, b = check_invariants(signed_text, new_text, dropped)
    rec = {"schema": "opentallas.detailed_abstract.v1", "macro": macro, "routed_db": str(odb), "routed_db_sha256": odb_sha,
           "signed_lef": str(slef), "signed_lef_sha256": hashlib.sha256(signed_text.encode()).hexdigest(),
           "new_lef_sha256": hashlib.sha256(new_text.encode()).hexdigest(), "image": args.image,
           "command": "read_db + write_abstract_lef (no -bloat_occupied_layers); no re-route / re-place / ECO",
           "raw_abstract_sha256": raw_sha, "pg_trim_threshold": args.pg_trim,
           "pg_access_trimmed": [{"pin": p, "layer": L, "rect": list(bx), "pdn_summed_overlap": f}
                                 for (p, L, bx, f) in dropped],
           "invariants": "PASS" if not bad else "FAIL", "violations": bad[:50],
           "obs_shapes_signed": dict(sorted(a["obs"].items())), "obs_shapes_new": dict(sorted(b["obs"].items())),
           "pg_pin_layers": sorted({r[0] for n, p in b["pins"].items() if p["use"] in ("POWER", "GROUND")
                                    for r in p["rects"]}),
           "note": "view export of the SAME signed routed DB; timing libs / netlist / sign-off record unchanged"}
    (out / f"{macro}.detailed_abstract.json").write_text(json.dumps(rec, indent=1) + "\n")
    if bad:
        print(f"FAIL {macro}: {len(bad)} invariant violation(s): {bad[:3]}", file=sys.stderr)
        return 1
    (out / f"{macro}.lef").write_text(new_text)
    print(f"PASS {macro}: {out / (macro + '.lef')} obs signed {rec['obs_shapes_signed']} -> new {rec['obs_shapes_new']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--odb", required=True)
    e.add_argument("--signed-lef", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--odb-sha256")
    e.add_argument("--image", default=IMAGE)
    e.add_argument("--mem", default="8g")
    e.add_argument("--name")
    e.add_argument("--pg-trim", type=float, default=0.9,
                   help="PG access trim threshold on the OpenROAD summed overlap (default 0.9; pass -1 to disable)")
    c = sub.add_parser("check")
    c.add_argument("--signed-lef", required=True)
    c.add_argument("--new-lef", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "export":
            return export(a)
        bad, _, _ = check_invariants(Path(a.signed_lef).read_text(), Path(a.new_lef).read_text())
        print("PASS" if not bad else "FAIL\n" + "\n".join(bad[:20]))
        return 1 if bad else 0
    except AbstractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
