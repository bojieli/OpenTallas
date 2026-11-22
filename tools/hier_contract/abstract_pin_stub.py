#!/usr/bin/env python3
"""Abstract-LEF post-processing, run after every view export: abstract_pin_stub.py IN.lef OUT.lef (in place allowed).

1. PIN STUBS: move OBS rects that overlap a signal pin's rect on the same layer into that pin's PORT (they are the pin
   net's own stub: in a DRC-clean routed child, any metal touching a pin on its layer is that pin's net).
2. POCKET CLOSING (2026-10-13, hc_tile_xl-c4-550082537-hs: 11 DRC in one open M6 pocket of ot_hdc_v41x_hcp_lanes at
   x 12.947..13.139, y 23.84..25.616): on the child's OWN TOP SIGNAL LAYER (the highest metal layer with OBS rects) the
   exporter leaves free pockets between the child's own wires; a parent router that enters one shorts / violates
   spacing against metal the abstract only partly describes.  Obstacles = OBS rects + PG pin rects on that layer.
   Every free gap that lies BETWEEN two obstacles (never between an obstacle and the macro boundary) and is narrower
   than D in x or in y becomes OBS, x-pass / y-pass iterated to a fixed point on the exact compressed coordinate grid.
   Nothing is added within keep_um(layer) of a signal pin rect on that layer or the one below (pin access stays): whole
   pitches >= the wide-metal spacing (M6 0.128, M5 0.096), since a fill rect is wide metal (KV-ECTL5 DRT-0073).
   D = 32 routing pitches of the layer (2.048 um on M6); OT_OBS_CLOSE_UM=<um> overrides it, OT_OBS_CLOSE=0 disables the step.
   A closed LEF carries the comment line `# OT_OBS_CLOSED layer=M6 d_um=2.048 added=<n>` before OBS; child_lint (h)
   imports find_pockets() from this file and FAILs a marked LEF that still has a pocket.
3. VIA SHADOW (OPUS-FIX-QC-SLE-R4-SC 2026-11-21, S81 col_h9_r0_p2 pv11b73b67: 17 M5 shorts, each the M5 pad of a
   V4+V5 stack in the middle of a solid dsfd_cfifo_crs4 M5 OBS rect over FREE M4): a free spot on a layer below the
   top OBS layer that has OBS directly above it is reachable only through that OBS, yet the parent GRT counts it as
   capacity and DRT drops a via stack through the child's metal.  Every M2..top-1 layer gets OBS wherever the layer
   above has OBS (top-down to M4: M2/M3 keep the std-cell pin access beside the macro), outside keep_um(layer) of signal pins on that layer and the one
   above, and at least SHADOW_EDGE_UM (0.30 um, OT_OBS_SHADOW_EDGE_UM) inside the macro outline so parent cells abutting
   the macro keep their pin access (FABLE-CLOSURE lever 1).  OT_OBS_SHADOW=0 disables it; marker `# OT_OBS_SHADOW layers=.. added=n`.
4. EOL STUBS (same lane, QC sle_sc_v1 cl115da35f: 44 Lef58EolKeepOut, 2 per pin, on 22 qfd_dv_s5_sc2_leaf M5 face
   pins): an OBS rect collinear with a signal pin's end, same width, abutting it and shorter than the layer's
   LEF58_EOLKEEPOUT forward extension (asap7 M4/M5 0.048 um) is the pin's own conductor up to its first via; its far
   corners sit in the CORNERONLY keep-out of the pin's line end, so every connected pin is a DRC that no route can
   clear.  The stub is lengthened (away from the pin) to EOL_FWD_UM + one grid; TritonRoute probe of the view alone:
   44 -> 0 (pin merged or stub lengthened), pin-access levers 145.  OT_OBS_EOLSTUB=0 disables it.
Pure python (no numpy): the grid is scanned row by row with the bytes regex engine.
"""
import os, re, sys, tempfile

PITCH_UM = {"M1": 0.036, "M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.080,
            "M9": 0.080}  # ASAP7 routing pitches
CLOSE_PITCHES = 32  # 2.048 um on M6: the reported hcp_lanes bay is 1.776 um high (own OBS to own PG strap); ORFS's abstract
                    # writer already merges gaps below ~1 um, so 16 pitches (1.024 um) finds nothing on that LEF
U = 10000  # integer grid: 0.1 nm
MARK_RE = re.compile(r"\n[ \t]*# OT_OBS_CLOSED layer=(\S+) d_um=([\d.]+) added=(\d+)[^\n]*")
_RUN = re.compile(rb"(?<=[\x01\x02])[\x00\x03]+(?=[\x01\x02])")  # 0 free, 1 obstacle, 2 fill, 3 free pin keep-out
_FILL = re.compile(rb"\x02+")
_RECT = r"RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"


PG_ACCESS_MARK = "# OT_OBS_PG_ACCESS M5:M6+M7"


def _ov(a, b):  # overlap with positive area
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def split_lef(t):
    """(head, obs): head = everything before the OBS block, obs = '\\n  OBS ...' to the end of the file"""
    m = re.search(r"\n[ \t]*OBS[ \t]*(?=\n)", t)
    assert m and m.start() > 0, "no OBS block in the LEF"
    return t[:m.start()], t[m.start():]


def pin_rects(head):
    """({signal pin: [(layer, x0, y0, x1, y1)]}, [PG pin rects (layer, x0, y0, x1, y1)])"""
    sig, pg = {}, []
    for m in re.finditer(r"  PIN (\S+)\n(.*?)\n  END \1", head, re.S):
        b = m.group(2)
        is_pg = bool(re.search(r"USE (POWER|GROUND)", b))
        for lay, rs in re.findall(r"LAYER (\S+) ;\s*((?:RECT[^;]*;\s*)+)", b):
            for r in re.findall(_RECT, rs):
                rec = (lay, *map(float, r))
                pg.append(rec) if is_pg else sig.setdefault(m.group(1), []).append(rec)
    return sig, pg


def obs_rects(obs):
    """{layer: [(x0, y0, x1, y1)]} of the OBS block"""
    out, cur = {}, None
    for line in obs.split("\n"):
        m = re.match(r"\s*LAYER (\S+)", line)
        if m:
            cur = m.group(1); continue
        m = re.match(r"\s*" + _RECT, line)
        if m and cur:
            out.setdefault(cur, []).append(tuple(map(float, m.groups())))
    return out


BUCKET_UM = 2.0  # pin-rect index cell


def pin_index(pins):
    """{layer: {(bx, by): {pin order index}}}: every signal pin rect binned on a BUCKET_UM grid of its layer.
    PINSTUB-INDEX (DAEMON-FIX2 2026-10-19): move_stubs tested every OBS rect against every pin rect -- 1.1 M OBS rects x
    5,288 pins on ot_hbm_accel_smh_fc_xr2 (46 MB LEF) ran > 600 s, so the daemon's commit child-lint (pin_stub_fix)
    timed out 10 times and smn_fcxr2_ref_fa-r4-637a35abf stopped NEEDS_HUMAN after it CLOSED.  Same hits, same order."""
    idx = {}
    for k, rs in enumerate(pins.values()):
        for lay, a, b, c, e in rs:
            cells = idx.setdefault(lay, {})
            for bx in range(int(min(a, c) // BUCKET_UM), int(max(a, c) // BUCKET_UM) + 1):
                for by in range(int(min(b, e) // BUCKET_UM), int(max(b, e) // BUCKET_UM) + 1):
                    cells.setdefault((bx, by), set()).add(k)
    return idx


def _candidates(idx, layer, r):
    cells = idx.get(layer)
    if not cells:
        return ()
    out = set()
    for bx in range(int(min(r[0], r[2]) // BUCKET_UM), int(max(r[0], r[2]) // BUCKET_UM) + 1):
        for by in range(int(min(r[1], r[3]) // BUCKET_UM), int(max(r[1], r[3]) // BUCKET_UM) + 1):
            out |= cells.get((bx, by), set())
    return sorted(out)


DROPPED = []  # step 1a of the last move_stubs call: [(pin, layer, rect strings)] dropped as copies of pin metal


def _inside(r, p):
    """rect r inside rect p (both (x0, y0, x1, y1), any corner order)"""
    eps = 1e-6
    return (min(r[0], r[2]) >= min(p[0], p[2]) - eps and min(r[1], r[3]) >= min(p[1], p[3]) - eps
            and max(r[0], r[2]) <= max(p[0], p[2]) + eps and max(r[1], r[3]) <= max(p[1], p[3]) + eps)


def move_stubs(head, obs, pins):
    """step 1; returns (head, obs, moved {pin: [(layer, (x0, y0, x1, y1) strings)]}).  1a: an OBS rect inside one of the
    pin's own same-layer rects only duplicates pin metal and is dropped, never moved (listed in DROPPED)"""
    moved = {}
    DROPPED.clear()
    out, cur = [], None
    names = list(pins)
    idx = pin_index(pins)
    for line in obs.split("\n"):
        m = re.match(r"\s*LAYER (\S+)", line)
        if m: cur = m.group(1); out.append(line); continue
        m = re.match(r"\s*RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", line) if cur in idx else None
        if m:
            r = tuple(map(float, m.groups()))
            hit = [p for p in (names[k] for k in _candidates(idx, cur, r))
                   if any(x[0] == cur and _ov(r, x[1:]) for x in pins[p])]
            if len(hit) == 1:
                if any(x[0] == cur and _inside(r, x[1:]) for x in pins[hit[0]]):
                    # 1a DUPLICATE (FAM-S81-COL-H10-R4 11-22): an OBS rect inside the pin's own rect is a copy of the pin
                    # metal, not a stub, so it is dropped.  Re-adding it as a second PORT gave the J6 hw ROM view
                    # 96 -> 1444 Lef58EolKeepOut (674 duplicate PORTs) in the TritonRoute view-alone probe.
                    DROPPED.append((hit[0], cur, m.groups())); continue
                moved.setdefault(hit[0], []).append((cur, m.groups())); continue
            if len(hit) > 1:
                # 1b BAND CARVE (ROOT 2026-10-15, hbm_ckgen_rel-r1): an OBS rect over SEVERAL pins is the exporter's
                # decomposition of the occupied edge band; the part of it over a pin rect is that pin's own metal, so
                # the OBS keeps only the rect minus those pin rects (child_lint (f) band: no OBS over a face pin)
                holes = [x[1:] for p in hit for x in pins[p] if x[0] == cur and _ov(r, x[1:])]
                ind = re.match(r"\s*", line).group()
                out += [f"{ind}RECT  {_um(a)} {_um(b)} {_um(c)} {_um(e)} ;"
                        for a, b, c, e in rect_minus(tuple(map(_iu, r)), [tuple(map(_iu, h)) for h in holes])]
                continue
        out.append(line)
    obs = "\n".join(out)
    for p, rs in moved.items():
        add = "".join(f"\n    PORT\n      LAYER {l} ;\n        RECT  {a} {b} {c} {d} ;\n    END" for l, (a, b, c, d) in rs)
        head = re.sub(rf"(  PIN {re.escape(p)}\n.*?)(\n  END {re.escape(p)})", lambda m: m.group(1) + add + m.group(2), head, count=1, flags=re.S)
    return head, obs, moved


def rect_minus(r, holes):
    """integer rect r minus the union of integer holes, as disjoint rects (row runs merged over equal rows)"""
    holes = [(max(h[0], r[0]), max(h[1], r[1]), min(h[2], r[2]), min(h[3], r[3])) for h in holes]
    holes = [h for h in holes if h[0] < h[2] and h[1] < h[3]]
    xs = sorted({r[0], r[2], *[v for h in holes for v in (h[0], h[2])]})
    ys = sorted({r[1], r[3], *[v for h in holes for v in (h[1], h[3])]})
    rows = []
    for y0, y1 in zip(ys, ys[1:]):
        runs, start = [], None
        for x0, x1 in zip(xs, xs[1:]):
            free = not any(h[0] <= x0 and x1 <= h[2] and h[1] <= y0 and y1 <= h[3] for h in holes)
            if free and start is None:
                start = x0
            if not free and start is not None:
                runs.append((start, x0)); start = None
        if start is not None:
            runs.append((start, xs[-1]))
        rows.append((y0, y1, runs))
    out = []
    for y0, y1, runs in rows:                      # merge vertically when the runs repeat exactly
        if out and out[-1][2] == runs and out[-1][1] == y0:
            out[-1] = (out[-1][0], y1, runs)
        else:
            out.append((y0, y1, runs))
    return [(a, y0, b, y1) for y0, y1, runs in out for a, b in runs]


# ASAP7 SPACINGTABLE wide-metal spacing (um): a shape wider than the layer's min width needs 0.072 um on M4..M7
# (WIDTH 0.025 / 0.033 -> 0.072).  The fill rects are wide, so the free band kept around a pin must be >= this, or every
# access stub on the pin violates it: KV-ECTL5 2026-10-19, qkd_ectl3_kiss_st-e4-13455b5bb DRT-0073 "No access point for
# u_a/req_t[10]" -- one M6 pitch (0.064) between the pin and a 1.25-um fill rect; 35 such pins on qkd_static_ectla_kiss.
WIDE_SPACING_UM = {"M4": 0.072, "M5": 0.072, "M6": 0.072, "M7": 0.072}


def keep_um(layer):
    """free band kept around signal pins: the smallest whole number of routing pitches >= the layer's wide-metal spacing
    (M4/M5 0.096, M6/M7 0.128), never less than one pitch"""
    pitch = PITCH_UM.get(layer, 0.064)
    n = max(1, -(-round(WIDE_SPACING_UM.get(layer, 0.0) * 1000) // round(pitch * 1000)))
    return round(n * pitch, 4)


def top_obs_layer(layers):
    ms = [(int(m.group(1)), l) for l in layers for m in [re.fullmatch(r"M(\d+)", l)] if m]
    return max(ms)[1] if ms else None


def close_d_um(layer):
    """closing distance of a new export: OT_OBS_CLOSE_UM, else CLOSE_PITCHES pitches of the layer"""
    if os.environ.get("OT_OBS_CLOSE_UM"):
        return float(os.environ["OT_OBS_CLOSE_UM"])
    return CLOSE_PITCHES * PITCH_UM.get(layer, 0.064)


def _iu(v):
    return int(round(v * U))


def _um(v):
    return f"{v / U:.4f}".rstrip("0").rstrip(".")


def fill_gaps(obst, keep, d):
    """obst / keep: integer rects (x0, y0, x1, y1); returns the fill rects (maximal row runs merged over equal rows)
    closing every free gap narrower than d between two obstacles, outside keep, at the x/y fixed point"""
    obst = [r for r in obst if r[0] < r[2] and r[1] < r[3]]
    if len(obst) < 2:
        return []
    X0, Y0 = min(r[0] for r in obst), min(r[1] for r in obst)
    X1, Y1 = max(r[2] for r in obst), max(r[3] for r in obst)
    keep = [(max(a, X0), max(b, Y0), min(c, X1), min(e, Y1)) for a, b, c, e in keep]
    keep = [r for r in keep if r[0] < r[2] and r[1] < r[3]]
    xs = sorted({v for r in obst + keep for v in (r[0], r[2])})
    ys = sorted({v for r in obst + keep for v in (r[1], r[3])})
    xi, yi = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(ys)}
    nx, ny = len(xs) - 1, len(ys) - 1
    g = bytearray(nx * ny)
    for a, b, c, e in obst:
        i0, i1 = xi[a], xi[c]
        one = b"\x01" * (i1 - i0)
        for j in range(yi[b], yi[e]):
            g[j * nx + i0:j * nx + i1] = one
    for a, b, c, e in keep:
        i0, i1 = xi[a], xi[c]
        for j in range(yi[b], yi[e]):
            g[j * nx + i0:j * nx + i1] = g[j * nx + i0:j * nx + i1].replace(b"\x00", b"\x03")

    def sweep(line, co):
        ch = False
        for m in _RUN.finditer(bytes(line)):
            s, e = m.span()
            if co[e] - co[s] < d and b"\x00" in m.group():
                line[s:e] = m.group().replace(b"\x00", b"\x02"); ch = True
        return ch

    while True:
        changed = False
        for j in range(ny):
            row = g[j * nx:(j + 1) * nx]
            if sweep(row, xs):
                g[j * nx:(j + 1) * nx] = row; changed = True
        for i in range(nx):
            col = g[i::nx]
            if sweep(col, ys):
                g[i::nx] = col; changed = True
        if not changed:
            break
    out, open_ = [], {}
    for j in range(ny + 1):
        runs = {m.span() for m in _FILL.finditer(bytes(g[j * nx:(j + 1) * nx]))} if j < ny else set()
        for sp in [k for k in open_ if k not in runs]:
            out.append((xs[sp[0]], ys[open_.pop(sp)], xs[sp[1]], ys[j]))
        for sp in runs:
            open_.setdefault(sp, j)
    return sorted(out, key=lambda r: (r[1], r[0]))


def find_pockets(text, d_um=None, use_marker=True):
    """pockets of a LEF's own top signal layer: {layer, d_um, pitch_um, marker, rects [(x0, y0, x1, y1) um], obstacles}.
    d_um None: the distance the LEF's own OT_OBS_CLOSED marker records (use_marker; what the lint checks), else
    close_d_um().  Keep-out: one pitch around signal pin rects on the layer and on the layer below (via access)."""
    if not re.search(r"\n[ \t]*OBS[ \t]*(?=\n)", text):  # a view without OBS has no own-layer metal to pocket
        return {"layer": None, "d_um": None, "pitch_um": None, "marker": None, "rects": [], "obstacles": 0}
    head, obs = split_lef(text)
    mk = MARK_RE.search(head)
    marker = {"layer": mk.group(1), "d_um": float(mk.group(2)), "added": int(mk.group(3))} if mk else None
    sig, pg = pin_rects(head)
    by = obs_rects(obs)
    layer = top_obs_layer(by)
    rec = {"layer": layer, "d_um": None, "pitch_um": None, "marker": marker, "rects": [], "obstacles": 0}
    if not layer:
        return rec
    pitch = PITCH_UM.get(layer, 0.064)
    if d_um is not None:
        d = d_um
    elif use_marker and marker and marker["layer"] == layer:
        d = marker["d_um"]
    else:
        d = close_d_um(layer)
    norm = lambda r: (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))
    obst = [norm(tuple(map(_iu, r))) for r in by[layer]] + [norm(tuple(map(_iu, r[1:]))) for r in pg if r[0] == layer]
    p = _iu(keep_um(layer))
    below = "M%d" % (int(layer[1:]) - 1)
    keep = [(a - p, b - p, c + p, e + p) for rs in sig.values() for r in rs if r[0] in (layer, below)
            for a, b, c, e in [norm(tuple(map(_iu, r[1:])))]]
    if layer == "M7" and PG_ACCESS_MARK in head.splitlines():
        # Exact-window export retains the routed M7 geometry over these M5
        # stripes. Avoid recreating the removed bloat as synthetic pocket OBS.
        keep.extend((a - p, b - p, c + p, e + p) for r in pg if r[0] == "M5"
                    for a, b, c, e in [norm(tuple(map(_iu, r[1:])))])
    rects = fill_gaps(obst, keep, _iu(d)) if d > 0 else []
    rec.update(d_um=d, pitch_um=pitch, obstacles=len(obst), rects=[tuple(v / U for v in r) for r in rects], _int=rects)
    return rec


def pin_spacing_violations(text):
    """signal pin rects with a same-layer OBS rect closer than the spacing the router needs for an access stub on the pin
    (wide-metal spacing WIDE_SPACING_UM when the OBS rect is wider than the layer's min width, else one min spacing):
    [(pin, layer, gap um, need um, obs rect)].  Such a pin has no DRC-clean access point (DRT-0073 in the parent)."""
    head, obs = split_lef(text)
    sig, _ = pin_rects(head)
    by = obs_rects(obs)
    out = []
    for pin, rs in sig.items():
        for r in rs:
            layer = r[0]
            if layer not in WIDE_SPACING_UM or layer not in by:
                continue
            a, b, c, e = (min(r[1], r[3]), min(r[2], r[4]), max(r[1], r[3]), max(r[2], r[4]))
            minw = PITCH_UM[layer] / 2
            for o in by[layer]:
                x0, y0, x1, y1 = (min(o[0], o[2]), min(o[1], o[3]), max(o[0], o[2]), max(o[1], o[3]))
                need = WIDE_SPACING_UM[layer] if min(x1 - x0, y1 - y0) > minw + 1e-6 else minw
                # parallel run along the layer's preferred direction only (M4 / M6 horizontal, M5 / M7 vertical);
                # end-of-line neighbours are governed by the EOL rule, not by the spacing table
                if int(layer[1:]) % 2 == 0:
                    if not (x1 > a and x0 < c):
                        continue
                    g = max(y0 - e, b - y1)
                else:
                    if not (y1 > b and y0 < e):
                        continue
                    g = max(x0 - c, a - x1)
                if 1e-6 < g < need - 1e-6:
                    out.append((pin, layer, round(g, 4), need, (x0, y0, x1, y1)))
    return out


CHAIN_MAX = 64  # own-conductor chain links followed per pin end


def chain_stubs(head, obs):
    """step 1c (FAM-S81-COL-H10-R4 11-22): an OBS rect on the pin's layer with exactly the pin's cross span that ABUTS a
    pin rect's end (no overlap, so step 1 skips it) is the pin's own conductor; it, and the collinear rects abutting it in
    turn, move into the pin's PORT.  Left as OBS, the pin's inner line end touches blockage metal and every connected pin
    is a Lef58EolKeepOut on both corners (J6 hw ROM view, face pins: 1444 EOL in the view-alone probe once the pin copy
    OBS is gone).  Returns (head, obs, {pin: [(layer, rect strings)]})."""
    if os.environ.get("OT_OBS_CHAIN", "1") == "0":
        return head, obs, {}
    sig, _ = pin_rects(head)
    by = obs_rects(obs)
    ends = {}  # (layer, vertical, cross lo, cross hi, coordinate) -> [obs rect index]
    ints = {lay: [tuple(map(_iu, r)) for r in rs] for lay, rs in by.items()}
    for lay, rs in ints.items():
        for k, (a, b, c, e) in enumerate(rs):
            a, b, c, e = min(a, c), min(b, e), max(a, c), max(b, e)
            ends.setdefault((lay, True, a, c, b), []).append(k)
            ends.setdefault((lay, True, a, c, e), []).append(k)
            ends.setdefault((lay, False, b, e, a), []).append(k)
            ends.setdefault((lay, False, b, e, c), []).append(k)
    take, owner = {}, {}
    for pin, rs in sig.items():
        for lay, *pr in rs:
            if lay not in ints:
                continue
            a, b, c, e = map(_iu, (min(pr[0], pr[2]), min(pr[1], pr[3]), max(pr[0], pr[2]), max(pr[1], pr[3])))
            for vert in (True, False):
                lo, hi = (a, c) if vert else (b, e)
                todo = [(b, e)] if vert else [(a, c)]
                seen = 0
                while todo and seen < CHAIN_MAX:
                    s0, s1 = todo.pop()
                    for at in (s0, s1):
                        for k in ends.get((lay, vert, lo, hi, at), ()):
                            r = ints[lay][k]
                            r0, r1 = (min(r[1], r[3]), max(r[1], r[3])) if vert else (min(r[0], r[2]), max(r[0], r[2]))
                            if (lay, k) in owner or not (r1 == at or r0 == at) or (r0 < s1 and s0 < r1):
                                continue
                            owner[(lay, k)] = pin
                            take.setdefault(pin, []).append((lay, k))
                            todo.append((r0, r1)); seen += 1
    if not take:
        return head, obs, {}
    kill = {(lay, by[lay][k]) for (lay, k) in owner}
    out, cur, moved = [], None, {}
    gone = set()
    for line in obs.split("\n"):
        m = re.match(r"\s*LAYER (\S+)", line)
        if m:
            cur = m.group(1); out.append(line); continue
        mr = re.match(r"\s*" + _RECT, line)
        if mr and cur:
            key = (cur, tuple(map(float, mr.groups())))
            if key in kill and key not in gone:
                gone.add(key)
                k = by[cur].index(key[1])
                moved.setdefault(owner[(cur, k)], []).append((cur, mr.groups())); continue
        out.append(line)
    obs = "\n".join(out)
    for pn, rs in moved.items():
        add = "".join(f"\n    PORT\n      LAYER {l} ;\n        RECT  {a} {b} {c} {d} ;\n    END" for l, (a, b, c, d) in rs)
        head = re.sub(rf"(  PIN {re.escape(pn)}\n.*?)(\n  END {re.escape(pn)})", lambda m: m.group(1) + add + m.group(2), head, count=1, flags=re.S)
    return head, obs, moved


def close_pockets(head, obs):
    """step 2; returns (head, obs, pocket record or None when disabled)"""
    if os.environ.get("OT_OBS_CLOSE", "1") == "0":
        return head, obs, None
    rec = find_pockets(head + obs, use_marker=False)
    layer, rects = rec["layer"], rec.get("_int", [])
    if not layer:
        return head, obs, rec
    if rects:
        lines, cur, last = obs.split("\n"), None, None
        for k, line in enumerate(lines):
            m = re.match(r"\s*LAYER (\S+)", line)
            if m: cur = m.group(1); last = k if cur == layer else last; continue
            if cur == layer and re.match(r"\s*RECT", line): last = k
        ind = re.match(r"\s*", lines[last]).group() if "RECT" in lines[last] else "     "
        lines[last + 1:last + 1] = [f"{ind}RECT  {_um(a)} {_um(b)} {_um(c)} {_um(e)} ;" for a, b, c, e in rects]
        obs = "\n".join(lines)
    prev = rec["marker"]["added"] if rec["marker"] and rec["marker"]["layer"] == layer else 0
    head = MARK_RE.sub("", head) + f"\n  # OT_OBS_CLOSED layer={layer} d_um={rec['d_um']:g} added={prev + len(rects)}"
    return head, obs, rec


SHADOW_RE = re.compile(r"\n[ \t]*# OT_OBS_SHADOW [^\n]*")
# M2/M3 carry the parent std-cell pin access next to a macro (col pv11b73b67: a shadow down to M2 left a DFF RESETN with
# no access point, DRT-1231); the via-stack-through-OBS class is M4 under M5, so the shadow stops at M4
SHADOW_MIN_LEVEL = 4
# FABLE-CLOSURE lever 1 (FAM-S81-COL-H10-R3 11-21): the shadow stays this far inside the macro outline, so a parent cell
# (relay / face flop) beside the macro keeps M2..M4 access within the 0.072 um wide-shape spacing of the shadow OBS
# (col pv11b73b67 ECO: DRT-1231 on a DFF pin beside u_cf).  OT_OBS_SHADOW_EDGE_UM=<um> overrides it.
SHADOW_EDGE_UM = 0.30
EOL_FWD_UM = {"M4": 0.048, "M5": 0.048, "M6": 0.048, "M7": 0.048}   # asap7 LEF58_EOLKEEPOUT forward extension
EOL_WIDTH_UM = {"M4": 0.025, "M5": 0.025, "M6": 0.05, "M7": 0.05}  # ... applies below this line-end width


def _bucket(rects, cell=_iu(BUCKET_UM)):
    idx = {}
    for k, r in enumerate(rects):
        for bx in range(r[0] // cell, r[2] // cell + 1):
            for by in range(r[1] // cell, r[3] // cell + 1):
                idx.setdefault((bx, by), []).append(k)
    return idx, cell


def _hits(idx, rects, r):
    ix, cell = idx
    ks = set()
    for bx in range(r[0] // cell, r[2] // cell + 1):
        for by in range(r[1] // cell, r[3] // cell + 1):
            ks.update(ix.get((bx, by), ()))
    return [rects[k] for k in sorted(ks) if _ov(r, rects[k])]


def _append_obs(obs, layer, rects):
    """add integer rects to the OBS block under `LAYER layer` (a new LAYER section when the layer has none)"""
    if not rects:
        return obs
    new = [f"     RECT  {_um(a)} {_um(b)} {_um(c)} {_um(e)} ;" for a, b, c, e in rects]
    lines = obs.split("\n")
    for k, line in enumerate(lines):
        if re.match(rf"\s*LAYER {re.escape(layer)} ;", line):
            lines[k + 1:k + 1] = new
            return "\n".join(lines)
    for k, line in enumerate(lines):
        if re.match(r"\s*OBS\s*$", line):
            lines[k + 1:k + 1] = [f"    LAYER {layer} ;"] + new
            return "\n".join(lines)
    raise AssertionError("no OBS line")


def shadow_lower(head, obs, only=None, mark=True):
    """step 3; returns (head, obs, {layer: rects added}).  only: the layers that may receive OBS (porous_views: its replaced
    layers, so everything else stays byte-identical); mark False: no marker line in the head (same reason)"""
    if os.environ.get("OT_OBS_SHADOW", "1") == "0":
        return head, obs, None
    sig, _ = pin_rects(head)
    by = obs_rects(obs)
    top = top_obs_layer(by)
    added = {}
    if not top:
        return head, obs, added
    norm = lambda r: (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))
    above = [norm(tuple(map(_iu, r))) for r in by[top]]
    ms = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", head)
    full = (_iu(float(ms.group(1))) * _iu(float(ms.group(2)))) if ms else 0
    ed = _iu(float(os.environ.get("OT_OBS_SHADOW_EDGE_UM", SHADOW_EDGE_UM)))
    inner = (ed, ed, _iu(float(ms.group(1))) - ed, _iu(float(ms.group(2))) - ed) if ms else None
    clip = lambda q: q if inner is None else (max(q[0], inner[0]), max(q[1], inner[1]), min(q[2], inner[2]), min(q[3], inner[3]))
    for n in range(int(top[1:]) - 1, SHADOW_MIN_LEVEL - 1, -1):
        L, up = "M%d" % n, "M%d" % (n + 1)
        own = [norm(tuple(map(_iu, r))) for r in by.get(L, [])]
        if full and any((r[2] - r[0]) * (r[3] - r[1]) >= 0.9 * full for r in own):
            break          # blanket layer (and everything below it in a kit view): nothing reachable to shadow
        if only is not None and L not in only:
            above = own
            continue
        oidx = _bucket(own)
        p = _iu(keep_um(L))
        keep = [(a - p, b - p, c + p, e + p) for rs in sig.values() for r in rs if r[0] in (L, up)
                for a, b, c, e in [norm(tuple(map(_iu, r[1:])))]]
        kidx = _bucket(keep)
        add = []
        for r in above:
            hs = _hits(kidx, keep, r)
            for q in (rect_minus(r, hs) if hs else [r]):
                q = clip(q)    # edge inset (SHADOW_EDGE_UM)
                if q[2] <= q[0] or q[3] <= q[1]:
                    continue
                if not any(o[0] <= q[0] and o[1] <= q[1] and o[2] >= q[2] and o[3] >= q[3] for o in _hits(oidx, own, q)):
                    add.append(q)   # (a piece already inside one own OBS rect is skipped: re-running adds nothing)
        added[L] = add
        obs = _append_obs(obs, L, add)
        above = own + add
    pm = re.search(r"# OT_OBS_SHADOW layers=(\S*) added=(\d+)", head)
    if not mark or not (any(added.values()) or pm):
        return head, obs, added
    lays = set(pm.group(1).split(",")) - {""} if pm else set()
    lays |= {l for l, v in added.items() if v}
    tot = (int(pm.group(2)) if pm else 0) + sum(map(len, added.values()))
    # always re-appended last, so a re-run (close_pockets re-appends its own marker first) gives identical bytes
    head = SHADOW_RE.sub("", head) + "\n  # OT_OBS_SHADOW layers=%s added=%d" % (",".join(sorted(lays, key=lambda l: -int(l[1:]))), tot)
    return head, obs, added


def eol_stubs(head, obs, force=False):
    """step 4; returns (obs, [(pin, layer, old rect, new rect)]); force: run even when OT_OBS_EOLSTUB=0 (defects() counts)"""
    if not force and os.environ.get("OT_OBS_EOLSTUB", "1") == "0":
        return obs, None
    sig, _ = pin_rects(head)
    by = obs_rects(obs)
    g = 120  # 12 nm past the keep-out (the probe-proven 0.144 end on qfd_dv_s5_sc2_leaf)
    fix = {}
    for pin, rs in sig.items():
        for lay, *pr in rs:
            if lay not in EOL_FWD_UM or lay not in by:
                continue
            a, b, c, e = map(_iu, (min(pr[0], pr[2]), min(pr[1], pr[3]), max(pr[0], pr[2]), max(pr[1], pr[3])))
            fwd = _iu(EOL_FWD_UM[lay])
            vert = (c - a) < (e - b)
            if (c - a if vert else e - b) >= _iu(EOL_WIDTH_UM[lay]):
                continue
            for o in by[lay]:
                x0, y0, x1, y1 = map(_iu, o)
                if vert and (x0, x1) == (a, c):
                    lo, hi, plo, phi = y0, y1, b, e
                elif not vert and (y0, y1) == (b, e):
                    lo, hi, plo, phi = x0, x1, a, c
                else:
                    continue
                if not (0 < hi - lo < fwd):
                    continue
                if lo == phi:
                    nlo, nhi = lo, phi + fwd + g
                elif hi == plo:
                    nlo, nhi = plo - fwd - g, hi
                else:
                    continue
                cont = any(((_iu(q[0]), _iu(q[2])) == (a, c) if vert else (_iu(q[1]), _iu(q[3])) == (b, e))
                           and (_iu(q[1] if vert else q[0]) == hi if lo == phi else _iu(q[3] if vert else q[2]) == lo)
                           for q in by[lay] if q is not o)
                if cont:
                    continue
                new = (a, nlo, c, nhi) if vert else (nlo, b, nhi, e)
                fix[(lay, o)] = (pin, new)
    if not fix:
        return obs, []
    out, cur, done = [], None, []
    for line in obs.split("\n"):
        m = re.match(r"\s*LAYER (\S+)", line)
        if m:
            cur = m.group(1)
        mr = re.match(r"(\s*)" + _RECT, line)
        if mr and cur:
            key = (cur, tuple(map(float, mr.groups()[1:])))
            if key in fix:
                pin, (x0, y0, x1, y1) = fix.pop(key)
                done.append((pin, cur, key[1], tuple(v / U for v in (x0, y0, x1, y1))))
                line = f"{mr.group(1)}RECT  {_um(x0)} {_um(y0)} {_um(x1)} {_um(y1)} ;"
        out.append(line)
    return "\n".join(out), done


def defects(text):
    """static pin-access defect counts of a LEF (SELF-GUARD, FABLE-FLOW-0800 class A1 11-22):
    pinobs  = same-layer OBS rects overlapping a signal pin rect (child_lint (f): no access point),
    eolstub = own-conductor OBS stubs shorter than the line-end keep-out (step 4's finding),
    dupport = signal pin rects inside another rect of the same pin on the same layer,
    pinabut = signal pin rects with no same-layer OBS over them whose end abuts a same-layer OBS rect of the same cross span
              (the pin's own conductor left as blockage: J6 hw view 96 -> 1444 Lef58EolKeepOut once its pin copies were gone)"""
    head, obs = split_lef(text)
    sig, _ = pin_rects(head)
    idx = pin_index(sig)
    names = list(sig)
    pinobs = 0
    for lay, rs in obs_rects(obs).items():
        if lay not in idx:
            continue
        for r in rs:
            if any(x[0] == lay and _ov(r, x[1:]) for k in _candidates(idx, lay, r) for x in sig[names[k]]):
                pinobs += 1
    dup = 0
    for rs in sig.values():
        for i, a in enumerate(rs):
            if any(j != i and b[0] == a[0] and _inside(a[1:], b[1:]) and (a[1:] != b[1:] or j < i) for j, b in enumerate(rs)):
                dup += 1
    by = {lay: [tuple(map(_iu, (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])))) for r in rs]
          for lay, rs in obs_rects(obs).items()}
    bidx = {lay: _bucket(rs) for lay, rs in by.items()}
    abut = 0
    for rs in sig.values():
        for lay, *pr in rs:
            if lay not in by:
                continue
            a, b, c, e = map(_iu, (min(pr[0], pr[2]), min(pr[1], pr[3]), max(pr[0], pr[2]), max(pr[1], pr[3])))
            near = _hits(bidx[lay], by[lay], (a - 1, b - 1, c + 1, e + 1))
            if any(_ov((a, b, c, e), o) for o in near):
                continue
            if any(((o[0], o[2]) == (a, c) and (o[3] == b or o[1] == e)) or ((o[1], o[3]) == (b, e) and (o[2] == a or o[0] == c))
                   for o in near):
                abut += 1
    return {"pinobs": pinobs, "eolstub": len(eol_stubs(head, obs, force=True)[1]), "dupport": dup, "pinabut": abut}


def process(text):
    """(new LEF text, summary line)"""
    head, obs = split_lef(text)
    pins, _ = pin_rects(head)
    head, obs, moved = move_stubs(head, obs, pins)
    head, obs, chain = chain_stubs(head, obs)
    head, obs, rec = close_pockets(head, obs)
    obs, eol = eol_stubs(head, obs)
    head, obs, sh = shadow_lower(head, obs)
    msg = f"pinstub: {sum(map(len, moved.values()))} OBS rects moved into {len(moved)} pins: " + ", ".join(sorted(moved)[:12])
    if DROPPED:
        msg += f"; {len(DROPPED)} OBS rects inside pin metal dropped ({len({d[0] for d in DROPPED})} pins)"
    if chain:
        msg += f"; chain: {sum(map(len, chain.values()))} abutting own-conductor OBS rects moved into {len(chain)} pins"
    if rec is None:
        msg += "; pockets: closing disabled (OT_OBS_CLOSE=0)"
    elif not rec["layer"]:
        msg += "; pockets: no metal OBS layer"
    else:
        msg += f"; pockets: {len(rec['rects'])} OBS rects added on {rec['layer']} (gaps < {rec['d_um']:g} um between own-layer obstacles)"
    if eol:
        msg += f"; eol stubs: {len(eol)} own-conductor OBS stubs lengthened past the line-end keep-out"
    if sh:
        msg += "; via shadow: " + ", ".join(f"{l} +{len(v)}" for l, v in sh.items())
    return head + obs, msg


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr); return 2
    src, dst = argv
    text = open(src).read()
    out, msg = process(text)
    # SELF-GUARD (FABLE-FLOW-0800 class A1 11-22): never write a LEF with more static pin-access defects than its input
    before, after = defects(text), defects(out)
    print("pinstub-defects before " + " ".join(f"{k}={v}" for k, v in before.items())
          + " after " + " ".join(f"{k}={v}" for k, v in after.items()))
    worse = [k for k in before if after[k] > before[k]]
    if worse:
        print(f"pinstub: REFUSED, output has more {', '.join(worse)} than the input; {dst} not written", file=sys.stderr)
        return 3
    # atomic replace, not an in-place write: ref_tile export rewrites the view LEF in place (dst == src) and the exporter's
    # container leaves it root-owned (open(dst, "w") -> PermissionError, hgi_topk_heap_rt_m5-h3m5-6d8d554ba collect 10-12);
    # the view directory itself is the job user's
    fd, tmp = tempfile.mkstemp(prefix=".pinstub.", dir=os.path.dirname(os.path.abspath(dst)))
    with os.fdopen(fd, "w") as f:
        f.write(out)
    os.chmod(tmp, 0o664)
    os.replace(tmp, dst)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
