#!/usr/bin/env python3
"""Class C (PDN-0006) fix: detailed upper-layer OBS for a signed hard-core abstract, no re-route.

A signed core exported with ``write_abstract_lef -bloat_occupied_layers`` carries one blanket OBS rect per
occupied layer.  When the core routed signals on layers above its PG pin layer (e.g. PG pins on M5, signals on
M6/M7), the blanket M6/M7 OBS hides every M5 PG pin from the parent grid and OpenROAD pdn stops with
``[ERROR PDN-0006] VSS on M5 is blocked by obstructions on M6, M7``.

This tool keeps the signed view byte-for-byte except the OBS of the layers ABOVE the highest PG pin layer, which
it takes from a detailed abstract of the SAME routed ODB (``write_abstract_lef -bloat_factor N``, N=0 = exact
shapes).  Lower layers stay blanket (the parent never routes there over the core), so pins, SIZE, FOREIGN, PG
pins and lower OBS are unchanged by construction; ``check`` proves it and that the detailed export saw the same
pins (same ODB).

  python3 -I abstract_detail.py tcl --odb /src/6_final.odb --out /out/detail.lef [--bloat-factor 0]
      -> OpenROAD Tcl for the detailed export (run it in the ORFS image, memory-capped)
  python3 -I abstract_detail.py splice --base signed.lef --detail detail.lef --out new.lef [--layers M6,M7]
      -> new.lef + JSON report on stdout (layers default: OBS layers above the highest PG pin layer)
  python3 -I abstract_detail.py check --base signed.lef --new new.lef
      -> exit 0 iff everything except OBS of the replaced layers is identical
Die-agnostic: any single-MACRO abstract (HEAD lep_pair, KV head_eighth, ...).
"""
import argparse
import hashlib
import json
import re
import sys

LAYER_ORDER = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "Pad"]


def _split(lines):
    """-> (head, obs_body, tail): head = lines before '  OBS', obs_body = lines inside OBS (excl OBS/END),
    tail = lines from the OBS 'END' on.  A view without OBS has obs_body None."""
    for i, ln in enumerate(lines):
        if ln.strip() == "OBS":
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "END":
                    return lines[:i + 1], lines[i + 1:j], lines[j:]
            raise ValueError("OBS without END")
    return lines, None, []


def _obs_by_layer(body):
    """OBS body -> ordered list of (layer, [lines]) (a layer may repeat; kept in order)."""
    out, cur = [], None
    for ln in body or []:
        m = re.match(r"\s*LAYER\s+(\S+)\s*;", ln)
        if m:
            cur = (m.group(1), [])
            out.append(cur)
        elif cur is not None:
            cur[1].append(ln)
        elif ln.strip():
            raise ValueError("OBS geometry before LAYER: %r" % ln)
    return out


def _iter_obs_layers(path, wanted):
    """Stream a (possibly huge) detailed LEF; yield only OBS lines of the wanted layers -> {layer: [lines]}."""
    got, in_obs, cur = {}, False, None
    with open(path) as fh:
        for ln in fh:
            s = ln.strip()
            if not in_obs:
                if s == "OBS":
                    in_obs = True
                continue
            if s == "END":
                break
            m = re.match(r"LAYER\s+(\S+)\s*;", s)
            if m:
                cur = m.group(1)
                continue
            if cur in wanted:
                got.setdefault(cur, []).append(ln if ln.endswith("\n") else ln + "\n")
    return got


def _pin_section(lines):
    """Text of all lines before OBS (MACRO header, SIZE, FOREIGN, every PIN) normalised for whitespace."""
    head, _, _ = _split(lines)
    return [re.sub(r"\s+", " ", ln.strip()) for ln in head if ln.strip() and ln.strip() != "OBS"]


def _head_stream(path):
    out = []
    with open(path) as fh:
        for ln in fh:
            if ln.strip() == "OBS":
                break
            if ln.strip():
                out.append(re.sub(r"\s+", " ", ln.strip()))
    return out


def pg_pin_layers(lines):
    """{pin: set(layers)} for USE POWER / GROUND pins."""
    res, pin, use, layers = {}, None, None, set()
    for ln in lines:
        s = ln.strip()
        m = re.match(r"PIN\s+(\S+)", s)
        if m:
            pin, use, layers = m.group(1), None, set()
            continue
        if pin is None:
            continue
        m = re.match(r"USE\s+(\S+)\s*;", s)
        if m:
            use = m.group(1)
        m = re.match(r"LAYER\s+(\S+)\s*;", s)
        if m:
            layers.add(m.group(1))
        if s == "END %s" % pin:
            if use in ("POWER", "GROUND"):
                res[pin] = layers
            pin = None
    return res


def default_layers(base_lines):
    pg = pg_pin_layers(base_lines)
    if not pg:
        raise ValueError("no PG pins in base view")
    top = max(LAYER_ORDER.index(l) for ls in pg.values() for l in ls if l in LAYER_ORDER)
    _, body, _ = _split(base_lines)
    obs_layers = [l for l, _ in _obs_by_layer(body)]
    return [l for l in obs_layers if l in LAYER_ORDER and LAYER_ORDER.index(l) > top]


def splice(base_lines, detail_obs, layers):
    """Replace OBS geometry of `layers` in base with detail_obs[layer] (list of lines; empty = no OBS there)."""
    head, body, tail = _split(base_lines)
    if body is None:
        raise ValueError("base view has no OBS")
    groups = _obs_by_layer(body)
    out_body, done = [], set()
    for layer, geo in groups:
        if layer in layers:
            if layer in done:
                continue
            done.add(layer)
            rects = detail_obs.get(layer, [])
            if rects:
                out_body.append("    LAYER %s ;\n" % layer)
                out_body.extend(rects)
        else:
            out_body.append("    LAYER %s ;\n" % layer)
            out_body.extend(geo)
    for layer in layers:  # detail layers the blanket view did not list (should not happen; kept for safety)
        if layer not in done and detail_obs.get(layer):
            out_body.append("    LAYER %s ;\n" % layer)
            out_body.extend(detail_obs[layer])
    return head + out_body + tail


def check(base_lines, new_lines, layers):
    """Everything but OBS of `layers` identical.  -> (ok, problems)."""
    probs = []
    if _pin_section(base_lines) != _pin_section(new_lines):
        probs.append("header/PIN sections differ")
    if pg_pin_layers(base_lines) != pg_pin_layers(new_lines):
        probs.append("PG pin layers differ")
    _, bb, bt = _split(base_lines)
    _, nb, nt = _split(new_lines)
    if bt != nt:
        probs.append("text after OBS differs")
    keep_b = [(l, g) for l, g in _obs_by_layer(bb) if l not in layers]
    keep_n = [(l, g) for l, g in _obs_by_layer(nb) if l not in layers]
    if keep_b != keep_n:
        probs.append("OBS of kept layers differ")
    return not probs, probs


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tcl")
    t.add_argument("--odb", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--bloat-factor", type=int, default=0)
    s = sub.add_parser("splice")
    s.add_argument("--base", required=True)
    s.add_argument("--detail", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--layers", default="")
    c = sub.add_parser("check")
    c.add_argument("--base", required=True)
    c.add_argument("--new", required=True)
    c.add_argument("--layers", default="")
    a = ap.parse_args(argv)
    if a.cmd == "tcl":
        print("read_db %s\nwrite_abstract_lef -bloat_factor %d %s" % (a.odb, a.bloat_factor, a.out))
        return 0
    base = open(a.base).read().splitlines(keepends=True)
    layers = [l for l in a.layers.split(",") if l] or default_layers(base)
    if a.cmd == "splice":
        same_pins = _head_stream(a.detail) == _pin_section(base)
        det = _iter_obs_layers(a.detail, set(layers))
        new = splice(base, det, layers)
        with open(a.out, "w") as fh:
            fh.writelines(new)
        ok, probs = check(base, new, layers)
        rep = {"base": a.base, "base_sha256": _sha(a.base), "detail": a.detail, "out": a.out,
               "out_sha256": _sha(a.out), "layers_detailed": layers,
               "rects": {l: len(det.get(l, [])) for l in layers},
               "pg_pin_layers": {k: sorted(v) for k, v in pg_pin_layers(base).items()},
               "detail_pins_equal_base": same_pins, "check_ok": ok and same_pins, "problems": probs
               + ([] if same_pins else ["detailed export PIN section != base (different ODB?)"])}
        print(json.dumps(rep, indent=1))
        return 0 if rep["check_ok"] else 1
    new = open(a.new).read().splitlines(keepends=True)
    ok, probs = check(base, new, layers)
    print(json.dumps({"check_ok": ok, "layers_detailed": layers, "problems": probs}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
