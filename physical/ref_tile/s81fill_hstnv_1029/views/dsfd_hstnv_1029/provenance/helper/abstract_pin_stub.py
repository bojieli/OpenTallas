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
   Nothing is added within one routing pitch of a signal pin rect on that layer (pin access stays).
   D = 32 routing pitches of the layer (2.048 um on M6); OT_OBS_CLOSE_UM=<um> overrides it, OT_OBS_CLOSE=0 disables the step.
   A closed LEF carries the comment line `# OT_OBS_CLOSED layer=M6 d_um=2.048 added=<n>` before OBS; child_lint (h)
   imports find_pockets() from this file and FAILs a marked LEF that still has a pocket.
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


def move_stubs(head, obs, pins):
    """step 1; returns (head, obs, moved {pin: [(layer, (x0, y0, x1, y1) strings)]})"""
    moved = {}
    out, cur = [], None
    for line in obs.split("\n"):
        m = re.match(r"\s*LAYER (\S+)", line)
        if m: cur = m.group(1); out.append(line); continue
        m = re.match(r"\s*RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", line)
        if m:
            r = tuple(map(float, m.groups()))
            hit = [p for p, rs in pins.items() if any(l == cur and _ov(r, x[1:]) for x in rs for l in [x[0]])]
            if len(hit) == 1:
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
    p = _iu(pitch)
    below = "M%d" % (int(layer[1:]) - 1)
    keep = [(a - p, b - p, c + p, e + p) for rs in sig.values() for r in rs if r[0] in (layer, below)
            for a, b, c, e in [norm(tuple(map(_iu, r[1:])))]]
    rects = fill_gaps(obst, keep, _iu(d)) if d > 0 else []
    rec.update(d_um=d, pitch_um=pitch, obstacles=len(obst), rects=[tuple(v / U for v in r) for r in rects], _int=rects)
    return rec


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


def process(text):
    """(new LEF text, summary line)"""
    head, obs = split_lef(text)
    pins, _ = pin_rects(head)
    head, obs, moved = move_stubs(head, obs, pins)
    head, obs, rec = close_pockets(head, obs)
    msg = f"pinstub: {sum(map(len, moved.values()))} OBS rects moved into {len(moved)} pins: " + ", ".join(sorted(moved)[:12])
    if rec is None:
        msg += "; pockets: closing disabled (OT_OBS_CLOSE=0)"
    elif not rec["layer"]:
        msg += "; pockets: no metal OBS layer"
    else:
        msg += f"; pockets: {len(rec['rects'])} OBS rects added on {rec['layer']} (gaps < {rec['d_um']:g} um between own-layer obstacles)"
    return head + obs, msg


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr); return 2
    src, dst = argv
    out, msg = process(open(src).read())
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
