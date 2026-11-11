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
  splice ... --pin-window-um 1.0 --window-detail exact_b0.lef [--top-layer M7]: PIN ACCESS WINDOW (DIE-QC-97 11-10,
      DRT-0073 class: QC NK/NL centre ck on M5 under blanket M5-M7).  After the splice, every signal pin of the new
      view that a parent cannot reach (access_report: not an edge pin, and no OBS-free via landing on the layer above
      it plus a free spot on each further layer up to --top-layer within pin +- margin) gets a window = its shape
      +- margin on each OBS layer above it up to --top-layer: the OBS there is cut and replaced by the EXACT core
      metal from the bloat-0 export of the same ODB, so a window removes only abstraction (blanket / bloat), never
      real metal.  The pin's own layer is not touched.  The receipt's 'pin_window' records every window.
  python3 -I abstract_detail.py check --base signed.lef --new new.lef [--receipt splice_receipt.json]
      -> with --receipt also: windows sit on base signal pins, kept layers = base minus windows plus metal inside
         the windows only, and every signal pin of new.lef has access
  python3 -I abstract_detail.py access --lef view.lef [--top-layer M7]
      -> JSON per-pin access report (edge / stack / top); exit 0 iff every signal pin has access
Die-agnostic: any single-MACRO abstract (HEAD lep_pair, KV head_eighth, ...).
"""
import argparse
import hashlib
import json
import math
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
    plan = dict(needed=False, layers=[], bloat_factor=None, pg_layer=False, enclosed=sorted(enclosed), pin_window=None)
    acc = access_report(base_lines)
    no_col = sorted(p for p, e in acc["pins"].items() if not e["ok"])
    if no_col:   # DIE-QC-97 11-10: no access on the base: the splice adds a window where the detail still has none
        plan["pin_window"] = dict(margin_um=WINDOW_MARGIN_UM, top_layer=acc["top_layer"], clear_um=ACCESS_CLEAR_UM,
                                  pins=no_col)
    # HBM-CORES-B 11-10 (DRT-0073, ot_hbm_idx_score_hcol_h0_ra clk): a pin with no access on the base that is NOT
    # enclosed (its own layer is free around it; only the bloated OBS of the layer above blocks every via landing)
    # takes the same detail form, else the exporter logged PIN-WINDOW-NO-DETAIL-FORM and shipped the blocked view.
    blocked = dict(enclosed)
    for p in no_col:
        blocked.setdefault(p, acc["pins"][p]["layer"])
    if not blocked:
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
    if layers and any(l in LAYER_ORDER[:-1] and LAYER_ORDER[LAYER_ORDER.index(l) + 1] in layers
                      for l in blocked.values()):
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


WINDOW_MARGIN_UM = 1.0   # QC-FAIL-22 11-10 hand form: ck pin +- 1 um (2 x 2.5 um window) passed pin access
ACCESS_CLEAR_UM = 0.05   # half-side of the probe box that must be OBS-free (via landing / free spot)
SCAN_UM = 0.016          # probe step inside a window


def _size_wh(lines):
    for ln in lines:
        m = re.search(r"^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", ln)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


def _obs_rects(lines):
    """{layer: [rect]} of the view's OBS."""
    _, body, _ = _split(lines)
    obs = {}
    for layer, geo in _obs_by_layer(body):
        for ln in geo:
            m = _RECT.match(ln)
            if m:
                obs.setdefault(layer, []).append(tuple(float(v) for v in m.groups()[1:]))
    return obs


class _Grid:
    """bucketed rects of one layer; blocked(box) = some rect overlaps the box interior"""

    def __init__(self, rects, cell=5.0):
        self.cell, self.idx = cell, {}
        for r in rects:
            for k in self._keys(r):
                self.idx.setdefault(k, []).append(r)

    def _keys(self, r):
        c = self.cell
        return ((x, y) for x in range(int(r[0] // c), int(r[2] // c) + 1) for y in range(int(r[1] // c), int(r[3] // c) + 1))

    def blocked(self, b):
        for k in self._keys(b):
            for r in self.idx.get(k, ()):
                if r[0] < b[2] - 1e-9 and r[2] > b[0] + 1e-9 and r[1] < b[3] - 1e-9 and r[3] > b[1] + 1e-9:
                    return True
        return False


def _signal_pin_shapes(lines):
    """{pin: [(layer, rect)]} of every non-PG pin (file order)."""
    pins, name, skip, layer = {}, None, False, None
    for line in lines:
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
            if m and name in pins:
                pins[name].append((layer, tuple(float(x) for x in m.groups()[1:])))
    return pins


def top_obs_layer(lines):
    have = [l for l in _obs_rects(lines) if l in LAYER_ORDER[:-1]]
    return max(have, key=LAYER_ORDER.index) if have else None


def _upper(layer, top):
    """routing layers strictly above `layer` up to and including `top`"""
    if layer not in LAYER_ORDER or top not in LAYER_ORDER:
        return []
    return LAYER_ORDER[LAYER_ORDER.index(layer) + 1:LAYER_ORDER.index(top) + 1]


def _snap(v, up):
    """to the 1 nm grid, outward"""
    return (math.ceil(v * 1000 - 1e-6) if up else math.floor(v * 1000 + 1e-6)) / 1000.0


def _grow(r, m, wh):
    w, h = wh or (float("inf"), float("inf"))
    return (max(0.0, _snap(r[0] - m, False)), max(0.0, _snap(r[1] - m, False)),
            min(w, _snap(r[2] + m, True)), min(h, _snap(r[3] + m, True)))


def _scan(r, step):
    """probe centres covering rect r (inclusive ends)"""
    nx, ny = max(1, int(round((r[2] - r[0]) / step))), max(1, int(round((r[3] - r[1]) / step)))
    return [(r[0] + (r[2] - r[0]) * i / nx, r[1] + (r[3] - r[1]) * j / ny) for i in range(nx + 1) for j in range(ny + 1)]


def _free_spot(grid, region, c, step=SCAN_UM):
    """a probe centre in region whose (2c) box lies in region and is OBS-free on this grid, or None"""
    x0, x1, y0, y1 = region[0] + c, region[2] - c, region[1] + c, region[3] - c
    if x1 < x0:                                   # region narrower than the probe: its centre line on that axis
        x0 = x1 = (region[0] + region[2]) / 2
    if y1 < y0:
        y0 = y1 = (region[1] + region[3]) / 2
    inner = (x0, y0, x1, y1)
    for x, y in _scan(inner, step):
        if grid is None or not grid.blocked((x - c, y - c, x + c, y + c)):
            return (round(x, 4), round(y, 4))
    return None


def access_report(lines, top_layer=None, clear_um=ACCESS_CLEAR_UM, margin_um=WINDOW_MARGIN_UM, edge_um=0.001):
    """Per signal pin: can a parent router reach it, judged on this view's OBS only?
      edge:  one of its shapes touches the macro boundary (within edge_um): planar entry from outside the cell;
      stack: over one of its shapes the layer directly above has an OBS-free via landing (a (2*clear_um) box, centre
             on the pin), AND every further layer up to top_layer (the parent's top routing layer; default the
             view's top OBS layer) has an OBS-free spot within the pin's window (shape +- margin_um): the access the
             router needs to leave the pin upward (DRT-0073 is the missing landing; a landing in a closed pocket
             passes pin access and then cannot route out);
      top:   the pin is on top_layer or above (nothing above to clear).
    The pin's own layer is not probed: OBS there over the pin is its own conductor (QC-FAIL-22 11-10: an M6 window
    over the M5 ck under blanket M5 passed pin access).
    -> {top_layer, clear_um, margin_um, pins: {pin: {layer, shape, ok, mode, landing, missing}}}"""
    top = top_layer or top_obs_layer(lines)
    wh = _size_wh(lines)
    grids = {l: _Grid(rs) for l, rs in _obs_rects(lines).items()}
    out = {}
    for pin, shapes in _signal_pin_shapes(lines).items():
        best = None
        for layer, r in shapes:
            if wh and min(r[0], r[1], wh[0] - r[2], wh[1] - r[3]) <= edge_um:
                best = dict(layer=layer, shape=list(r), ok=True, mode="edge", landing=None, missing=[])
                break
            ups = _upper(layer, top) if top else []
            if not ups:
                best = dict(layer=layer, shape=list(r), ok=True, mode="top", landing=None, missing=[])
                break
            land = _free_spot(grids.get(ups[0]), r, clear_um, min(SCAN_UM, clear_um))
            win = _grow(r, margin_um, wh)
            missing = ([] if land else [ups[0]]) + [l for l in ups[1:] if _free_spot(grids.get(l), win, clear_um) is None]
            cand = dict(layer=layer, shape=list(r), ok=not missing, mode="stack" if not missing else None,
                        landing=land, missing=missing)
            if best is None or len(missing) < len(best["missing"]):
                best = cand
            if not missing:
                break
        if best is not None:
            out[pin] = best
    return dict(top_layer=top, clear_um=clear_um, margin_um=margin_um, pins=out)


def pin_windows(lines, margin_um=WINDOW_MARGIN_UM, top_layer=None, clear_um=ACCESS_CLEAR_UM):
    """{pin: {layer, rect, layers}} for every signal pin of `lines` without access (access_report): window = the pin
    shape access_report judged best, grown by margin_um (snapped out to 1 nm, clipped to SIZE); layers = the OBS
    layers above the pin layer up to top_layer.  The pin's own layer is never in a window."""
    rep = access_report(lines, top_layer, clear_um, margin_um)
    wh = _size_wh(lines)
    obs_layers = set(_obs_rects(lines))
    return {pin: dict(layer=e["layer"], rect=list(_grow(e["shape"], margin_um, wh)),
                      layers=[l for l in _upper(e["layer"], rep["top_layer"]) if l in obs_layers])
            for pin, e in rep["pins"].items() if not e["ok"]}


def exact_in_windows(path, wins):
    """Stream an EXACT detailed export (write_abstract_lef -bloat_factor 0 of the same signed ODB) -> {layer: [rect
    clipped to each window of that layer]}: the true core metal inside the windows."""
    by_layer = {}
    for w in wins.values():
        for l in w["layers"]:
            by_layer.setdefault(l, []).append(tuple(w["rect"]))
    got = {}
    for layer, lines in _iter_obs_layers(path, set(by_layer)).items():
        for ln in lines:
            m = _RECT.match(ln)
            if not m:
                continue
            r = tuple(float(v) for v in m.groups()[1:])
            for h in by_layer[layer]:
                c = (max(r[0], h[0]), max(r[1], h[1]), min(r[2], h[2]), min(r[3], h[3]))
                if c[2] > c[0] + 1e-9 and c[3] > c[1] + 1e-9:
                    got.setdefault(layer, []).append(c)
    return got


def _fmt(x):
    s = "%.4f" % x
    return s.rstrip("0").rstrip(".") if "." in s else s


def _in_any(r, holes, e=1e-6):
    return any(r[0] >= h[0] - e and r[1] >= h[1] - e and r[2] <= h[2] + e and r[3] <= h[3] + e for h in holes)


def apply_windows(lines, wins, exact=None):
    """Cut every window out of the OBS of its layers (exact cover of rect minus windows; untouched lines byte-equal),
    then put the EXACT core metal inside each window back (exact = exact_in_windows(...)): the window removes only
    the abstraction (blanket / bloat), never real metal.  -> (new lines, {layer: {rects_cut, um2_cut, exact_added,
    exact_um2}})"""
    by_layer = {}
    for w in wins.values():
        for l in w["layers"]:
            by_layer.setdefault(l, []).append(tuple(w["rect"]))
    head, body, tail = _split(lines)
    if body is None or not by_layer:
        return list(lines), {}
    exact = exact or {}
    out_body, rep, layer, indent = [], {}, None, "     "

    def flush(l):
        add = exact.get(l) if l in by_layer else None
        if add:
            st = rep.setdefault(l, {"rects_cut": 0, "um2_cut": 0.0})
            st["exact_added"] = len(add)
            st["exact_um2"] = round(sum((q[2] - q[0]) * (q[3] - q[1]) for q in add), 6)
            out_body.extend("%sRECT  %s %s %s %s ;\n" % ((indent,) + tuple(_fmt(v) for v in q)) for q in add)
    for ln in body:
        lm = re.match(r"\s*LAYER\s+(\S+)\s*;", ln)
        if lm:
            flush(layer)
            layer = lm.group(1)
            out_body.append(ln)
            continue
        holes = by_layer.get(layer)
        m = _RECT.match(ln) if holes else None
        r = tuple(float(v) for v in m.groups()[1:]) if m else None
        hit = [h for h in holes if r[0] < h[2] and r[2] > h[0] and r[1] < h[3] and r[3] > h[1]] if m else []
        if m:
            indent = m.group(1)
        if not hit:
            out_body.append(ln)
            continue
        rs = [r]
        for h in hit:
            rs = [q for p in rs for q in (_subtract(p, h) if p[0] < h[2] and p[2] > h[0] and p[1] < h[3]
                                          and p[3] > h[1] else [p])]
        st = rep.setdefault(layer, {"rects_cut": 0, "um2_cut": 0.0})
        st["rects_cut"] += 1
        st["um2_cut"] = round(st["um2_cut"] + (r[2] - r[0]) * (r[3] - r[1])
                              - sum((q[2] - q[0]) * (q[3] - q[1]) for q in rs), 6)
        out_body += ["%sRECT  %s %s %s %s ;\n" % ((m.group(1),) + tuple(_fmt(v) for v in q)) for q in rs]
    flush(layer)
    return head + out_body + tail, rep


def _check_windows(base_lines, window):
    """the receipt's windows must each sit on a signal pin of the base: rect = that pin's shape grown by the margin,
    layers above its layer up to the recorded top layer -> problems"""
    probs, wh = [], _size_wh(base_lines)
    shapes = _signal_pin_shapes(base_lines)
    m, top = float(window.get("margin_um", WINDOW_MARGIN_UM)), window.get("top_layer")
    for pin, w in sorted((window.get("windows") or {}).items()):
        want = [list(_grow(r, m, wh)) for l, r in shapes.get(pin, []) if l == w.get("layer")]
        if not want or [round(v, 4) for v in w.get("rect") or []] not in [[round(v, 4) for v in q] for q in want]:
            probs.append("pin window %s is not its signal pin shape +- %s um" % (pin, m))
        if not set(w.get("layers") or []) <= set(_upper(w.get("layer"), top)):
            probs.append("pin window %s cuts layers outside (%s, %s]" % (pin, w.get("layer"), top))
    return probs


def check(base_lines, new_lines, layers, window=None):
    """Everything but OBS of `layers` identical.  With a pin window record (splice receipt 'pin_window': margin_um,
    top_layer, clear_um, windows) the windows must sit on base signal pins (_check_windows), the kept layers must
    equal the base with those windows cut plus only metal inside the windows (the exact refinement), and every signal
    pin of the new view must have access (access_report).  -> (ok, problems)."""
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
    if window:
        wins = window.get("windows") or {}
        probs += _check_windows(base_lines, window)
        cut, _ = apply_windows(base_lines, wins)
        keep_b = [(l, g) for l, g in _obs_by_layer(_split(cut)[1]) if l not in layers]
        holes = {}
        for w in wins.values():
            for l in w["layers"]:
                holes.setdefault(l, []).append(tuple(w["rect"]))

        def outside(l, g):
            return [ln for ln in g if not (_RECT.match(ln) and _in_any(
                tuple(float(v) for v in _RECT.match(ln).groups()[1:]), holes.get(l, ())))]
        keep_n = [(l, outside(l, g)) for l, g in keep_n]
        keep_b = [(l, outside(l, g)) for l, g in keep_b]
    if keep_b != keep_n:
        probs.append("OBS of kept layers differ")
    if window:
        rep = access_report(new_lines, window.get("top_layer"), float(window.get("clear_um", ACCESS_CLEAR_UM)),
                            float(window.get("margin_um", WINDOW_MARGIN_UM)))
        bad = sorted(p for p, e in rep["pins"].items() if not e["ok"])
        if bad:
            probs.append("signal pins without access up to %s: %s" % (rep["top_layer"], bad[:8]))
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
    c.add_argument("--receipt", default=None, help="splice receipt JSON: recheck its pin windows ('pin_window')")
    x = sub.add_parser("access")
    x.add_argument("--lef", required=True)
    s.add_argument("--pin-window-um", type=float, default=None,
                   help="window margin for every signal pin without access (needs --window-detail)")
    s.add_argument("--window-detail", default=None,
                   help="EXACT detailed export (-bloat_factor 0, same ODB): the true metal put back inside windows")
    for q in (s, x):
        q.add_argument("--top-layer", default=None, help="parent top routing layer (default: the view's top OBS layer)")
        q.add_argument("--access-clear-um", type=float, default=ACCESS_CLEAR_UM)
    x.add_argument("--margin-um", type=float, default=WINDOW_MARGIN_UM)
    a = ap.parse_args(argv)
    if a.cmd == "tcl":
        print("read_db %s\nwrite_abstract_lef -bloat_factor %d %s" % (a.odb, a.bloat_factor, a.out))
        return 0
    if a.cmd == "access":
        lines = open(a.lef).read().splitlines(keepends=True)
        rep = access_report(lines, a.top_layer, a.access_clear_um, a.margin_um)
        bad = sorted(p for p, e in rep["pins"].items() if not e["ok"])
        modes = {}
        for e in rep["pins"].values():
            modes[str(e["mode"])] = modes.get(str(e["mode"]), 0) + 1
        print(json.dumps(dict(lef=a.lef, lef_sha256=_sha(a.lef), top_layer=rep["top_layer"], clear_um=rep["clear_um"],
                              margin_um=rep["margin_um"], signal_pins=len(rep["pins"]), modes=modes,
                              interior={p: e for p, e in rep["pins"].items() if e["mode"] != "edge"},
                              without_access=bad, ok=not bad), indent=1))
        return 0 if not bad else 1
    base = open(a.base).read().splitlines(keepends=True)
    if a.cmd == "plan":
        print(json.dumps(export_plan(base)))
        return 0
    layers = [l for l in a.layers.split(",") if l] or default_layers(base)
    if a.cmd == "splice":
        if a.pin_window_um is not None and not a.window_detail:
            ap.error("--pin-window-um needs --window-detail (exact export): a window never removes real metal")
        same_pins = _head_stream(a.detail) == _pin_section(base)
        det = _iter_obs_layers(a.detail, set(layers))
        cleared = None
        if a.pin_clear_um is not None:
            det, cleared = clear_pins(det, base, a.pin_clear_um, [l for l in a.pin_clear_layers.split(",") if l])
        new = splice(base, det, layers)
        window = None
        if a.pin_window_um is not None:
            top = a.top_layer or top_obs_layer(base)
            wins = pin_windows(new, a.pin_window_um, top, a.access_clear_um)   # decided on the spliced view
            exact = exact_in_windows(a.window_detail, wins) if wins else {}
            new, cut = apply_windows(new, wins, exact)
            window = dict(margin_um=a.pin_window_um, top_layer=top, clear_um=a.access_clear_um, windows=wins, cut=cut,
                          window_detail=a.window_detail, window_detail_sha256=_sha(a.window_detail),
                          window_detail_pins_equal_base=_head_stream(a.window_detail) == _pin_section(base))
        with open(a.out, "w") as fh:
            fh.writelines(new)
        ok, probs = check(base, new, layers, window)
        if window and not window["window_detail_pins_equal_base"]:
            ok, probs = False, probs + ["window detail PIN section != base (different ODB?)"]
        rep = {"base": a.base, "base_sha256": _sha(a.base), "detail": a.detail, "out": a.out,
               "out_sha256": _sha(a.out), "layers_detailed": layers,
               "rects": {l: len(det.get(l, [])) for l in layers},
               "pin_clear_um": a.pin_clear_um, "pin_clear": cleared,
               "pg_pin_layers": {k: sorted(v) for k, v in pg_pin_layers(base).items()},
               "detail_pins_equal_base": same_pins, "check_ok": ok and same_pins, "problems": probs
               + ([] if same_pins else ["detailed export PIN section != base (different ODB?)"])}
        if window is not None:
            rep["pin_window"] = window
        if a.bloat_factor is not None:
            rep["bloat_factor"] = a.bloat_factor
        print(json.dumps(rep, indent=1))
        return 0 if rep["check_ok"] else 1
    new = open(a.new).read().splitlines(keepends=True)
    window = json.load(open(a.receipt)).get("pin_window") if a.receipt else None
    ok, probs = check(base, new, layers, window)
    print(json.dumps({"check_ok": ok, "layers_detailed": layers, "pin_windows": sorted((window or {}).get("windows")
                                                                                       or {}), "problems": probs}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
