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

  python3 -I abstract_detail.py tcl --odb /src/6_final.odb --out /out/detail.lef [--bloat-factor 1]
      -> OpenROAD Tcl for the detailed export (run it in the ORFS image, memory-capped); default 1 = one pitch
         merge (fewer parent slivers; same PG access as 0 on HEAD lep_pair)
  python3 -I abstract_detail.py splice --base signed.lef --detail detail.lef --out new.lef [--layers M6,M7]
      -> new.lef + JSON report on stdout (layers default: OBS layers above the highest PG pin layer)
      [--pin-clear-um 0.048 --pin-clear-layers M4]: DRT-0073 form. Always with this flag: metal under a signal pin
      leaves the OBS (it is that pin's own conductor, so nothing is lost); and detail OBS on --pin-clear-layers within
      the distance of a signal pin is cut, because the neighbouring wire there stops pin access.  Geometry under that
      cut is NOT modeled for the parent: the report counts it, and --pin-clear-layers should stay the pin's own layer.
  python3 -I abstract_detail.py check --base signed.lef --new new.lef
      -> exit 0 iff everything except OBS of the replaced layers is identical
  python3 -I abstract_detail.py plan --base signed.lef
      -> JSON: does this view enclose a signal pin (DRT-0073 class), and which splice form an export should add
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


_RECT = re.compile(r"(\s*)RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)")


def signal_pin_rects(base_lines):
    """{layer: [rect]} of every non-PG pin shape in the base view."""
    out, name, skip, layer = {}, None, False, None
    for line in base_lines:
        m = re.match(r"\s*PIN (\S+)", line)
        if m:
            name, skip, layer = m.group(1), False, None
            continue
        if name is None:
            continue
        if re.match(r"\s*END %s\s*$" % re.escape(name), line):
            name = None
        elif re.search(r"USE (POWER|GROUND)", line):
            skip = True
        elif re.match(r"\s*LAYER (\S+)", line):
            layer = re.match(r"\s*LAYER (\S+)", line).group(1)
        elif not skip:
            m = _RECT.match(line)
            if m and layer:
                out.setdefault(layer, []).append(tuple(float(x) for x in m.groups()[1:]))
    return out


def enclosed_signal_pins(base_lines, edge_um=0.5):
    """{pin: layer} of signal pins the view leaves with no way in (DRT-0073 class, DIE-HBM-97 11-09): an interior pin
    whose every shape is covered by OBS on its own layer AND on the layer above, so no via up and no planar entry."""
    size = next((re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", ln) for ln in base_lines if "SIZE" in ln), None)
    if not size:
        return {}
    w, h = float(size.group(1)), float(size.group(2))
    _, body, _ = _split(base_lines)
    obs = {}
    for layer, geo in _obs_by_layer(body):
        for ln in geo:
            m = _RECT.match(ln)
            if m:
                obs.setdefault(layer, []).append(tuple(float(v) for v in m.groups()[1:]))

    def covered(layer, r):
        e = 0.001
        pts = [(r[0] + e, r[1] + e), (r[2] - e, r[1] + e), (r[0] + e, r[3] - e), (r[2] - e, r[3] - e),
               ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)]
        return all(any(a <= x <= c and b <= y <= d for a, b, c, d in obs.get(layer, ())) for x, y in pts)

    pins, name, skip, layer = {}, None, False, None
    for line in base_lines:
        m = re.match(r"\s*PIN (\S+)", line)
        if m:
            name, skip, layer = m.group(1), False, None
            pins[name] = []
            continue
        if name is None:
            continue
        if re.match(r"\s*END %s\s*$" % re.escape(name), line):
            name = None
        elif re.search(r"USE (POWER|GROUND)", line):
            skip = True
            pins.pop(name, None)
        elif re.match(r"\s*LAYER (\S+)", line):
            layer = re.match(r"\s*LAYER (\S+)", line).group(1)
        elif not skip and layer:
            m = _RECT.match(line)
            if m:
                pins[name].append((layer, tuple(float(x) for x in m.groups()[1:])))
    out = {}
    for pin, shapes in pins.items():
        if not shapes or any(l not in LAYER_ORDER[:-1] or min(r[0], r[1], w - r[2], h - r[3]) < edge_um
                             for l, r in shapes):
            continue
        if all(covered(l, r) and covered(LAYER_ORDER[LAYER_ORDER.index(l) + 1], r) for l, r in shapes):
            out[pin] = shapes[0][0]
    return out


def export_plan(base_lines):
    """Which detailed splice a counted-view export should add -> {needed, layers, bloat_factor, pg_layer, enclosed}.
    Needed only when a signal pin is enclosed and the layer above it is one this form replaces.  Normal form: layers
    above the PG pins, exact shapes (bloat 0; bloat 1 still left DRT-0073 on wbq_root_g0, gqi_issue, opsa_rest and ahub).  PG pins on the top OBS
    layer: that one layer at bloat 1, the only form prov_view.pg_layer_detail_layers accepts."""
    enclosed = enclosed_signal_pins(base_lines)
    plan = dict(needed=False, layers=[], bloat_factor=None, pg_layer=False, enclosed=sorted(enclosed))
    if not enclosed:
        return plan
    pg = pg_pin_layers(base_lines)
    tops = [l for ls in pg.values() for l in ls if l in LAYER_ORDER]
    if not tops:
        return plan
    layers, bloat, pg_layer = default_layers(base_lines), 0, False
    if not layers:
        top = max(tops, key=LAYER_ORDER.index)
        _, body, _ = _split(base_lines)
        have = [l for l, _ in _obs_by_layer(body) if l in LAYER_ORDER]
        if have and max(have, key=LAYER_ORDER.index) == top:
            layers, bloat, pg_layer = [top], 1, True
    if layers and any(LAYER_ORDER[LAYER_ORDER.index(l) + 1] in layers for l in enclosed.values()):
        plan.update(needed=True, layers=layers, bloat_factor=bloat, pg_layer=pg_layer)
    return plan


def _subtract(r, p):
    a, b, c, d = r
    e, f, g, h = p
    res = []
    if f > b:
        res.append((a, b, c, f))
    if h < d:
        res.append((a, h, c, d))
    if e > a:
        res.append((a, max(b, f), e, min(d, h)))
    if g < c:
        res.append((g, max(b, f), c, min(d, h)))
    return [q for q in res if q[2] > q[0] and q[3] > q[1]]


def clear_pins(detail_obs, base_lines, clear_um=0.0, clear_layers=()):
    """Cut pin shapes (all layers) and, on clear_layers, pin shapes grown by clear_um out of detail OBS lines.
    -> (new detail_obs, {layer: {own_rects, cleared_rects, cleared_um2}})"""
    pins, grid, new, rep = signal_pin_rects(base_lines), 1.0, {}, {}
    for layer, lines in detail_obs.items():
        grow = clear_um if layer in clear_layers else 0.0
        boxes = [(r, (r[0] - grow, r[1] - grow, r[2] + grow, r[3] + grow)) for r in pins.get(layer, [])]
        idx = {}
        for _, b in boxes:
            for x in range(int(b[0] // grid), int(b[2] // grid) + 1):
                for y in range(int(b[1] // grid), int(b[3] // grid) + 1):
                    idx.setdefault((x, y), []).append(b)
        out, own, cut, area = [], 0, 0, 0.0
        for line in lines:
            m = _RECT.match(line)
            if not m:
                out.append(line)
                continue
            r = tuple(float(x) for x in m.groups()[1:])
            cand = set()
            for x in range(int(r[0] // grid), int(r[2] // grid) + 1):
                for y in range(int(r[1] // grid), int(r[3] // grid) + 1):
                    cand.update(idx.get((x, y), ()))
            rs = [r]
            for b in cand:
                nr = []
                for q in rs:
                    nr += _subtract(q, b) if (q[0] < b[2] and q[2] > b[0] and q[1] < b[3] and q[3] > b[1]) else [q]
                rs = nr
            if rs == [r]:
                out.append(line)
                continue
            own += any(r[0] < p[2] and r[2] > p[0] and r[1] < p[3] and r[3] > p[1] for p in pins.get(layer, []))
            cut += 1
            area += (r[2] - r[0]) * (r[3] - r[1]) - sum((q[2] - q[0]) * (q[3] - q[1]) for q in rs)
            out += ["%sRECT %.3f %.3f %.3f %.3f ;\n" % (m.group(1), q[0], q[1], q[2], q[3]) for q in rs]
        new[layer] = out
        rep[layer] = {"rects_cut": cut, "overlap_own_pin": own, "um2_cut": round(area, 4)}
    return new, rep


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
    t.add_argument("--bloat-factor", type=int, default=1)
    s = sub.add_parser("splice")
    s.add_argument("--base", required=True)
    s.add_argument("--detail", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--layers", default="")
    s.add_argument("--pin-clear-um", type=float, default=None)
    s.add_argument("--pin-clear-layers", default="")
    s.add_argument("--bloat-factor", type=int, default=None, help="recorded in the report (the wave receipt contract)")
    p = sub.add_parser("plan")
    p.add_argument("--base", required=True)
    c = sub.add_parser("check")
    c.add_argument("--base", required=True)
    c.add_argument("--new", required=True)
    c.add_argument("--layers", default="")
    a = ap.parse_args(argv)
    if a.cmd == "tcl":
        print("read_db %s\nwrite_abstract_lef -bloat_factor %d %s" % (a.odb, a.bloat_factor, a.out))
        return 0
    base = open(a.base).read().splitlines(keepends=True)
    if a.cmd == "plan":
        print(json.dumps(export_plan(base)))
        return 0
    layers = [l for l in a.layers.split(",") if l] or default_layers(base)
    if a.cmd == "splice":
        same_pins = _head_stream(a.detail) == _pin_section(base)
        det = _iter_obs_layers(a.detail, set(layers))
        cleared = None
        if a.pin_clear_um is not None:
            det, cleared = clear_pins(det, base, a.pin_clear_um, [l for l in a.pin_clear_layers.split(",") if l])
        new = splice(base, det, layers)
        with open(a.out, "w") as fh:
            fh.writelines(new)
        ok, probs = check(base, new, layers)
        rep = {"base": a.base, "base_sha256": _sha(a.base), "detail": a.detail, "out": a.out,
               "out_sha256": _sha(a.out), "layers_detailed": layers,
               "rects": {l: len(det.get(l, [])) for l in layers},
               "pin_clear_um": a.pin_clear_um, "pin_clear": cleared,
               "pg_pin_layers": {k: sorted(v) for k, v in pg_pin_layers(base).items()},
               "detail_pins_equal_base": same_pins, "check_ok": ok and same_pins, "problems": probs
               + ([] if same_pins else ["detailed export PIN section != base (different ODB?)"])}
        if a.bloat_factor is not None:
            rep["bloat_factor"] = a.bloat_factor
        print(json.dumps(rep, indent=1))
        return 0 if rep["check_ok"] else 1
    new = open(a.new).read().splitlines(keepends=True)
    ok, probs = check(base, new, layers)
    print(json.dumps({"check_ok": ok, "layers_detailed": layers, "problems": probs}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
