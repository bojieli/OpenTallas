#!/usr/bin/env python3
"""render_review.py -- AUTOPILOT review bundle for a routed run that did not sign off (read-only on the kit).

    render_review.py REVIEW_DIR

REVIEW_DIR/review.json (autopilot.py) names the kit, its routed ODB and the signoff.json.  Writes into REVIEW_DIR:
  paths_tt_setup.txt / paths_ff_hold.txt   the VIOLATED path reports of the sign-off STA (signoff/<corner>/sta.log:
                                            TT 'Path Type: max', FF 'Path Type: min'), verbatim
  summary.txt                               signoff verdict + reasons
  floorplan.png / density.png               tools/ref_tile/layout_png.py on layout.json (layout_dump.tcl of the ODB)
  paths.png / paths_zoom.png               the routed layout (whole outline / zoomed to the paths) with every failing path drawn cell to cell
                                            (red = TT setup, blue = FF hold; start = square, end = cross)
Prints AP_REVIEW_PNG <file> / AP_REVIEW_PATHS <file> lines for autopilot.py.  It changes nothing in the kit.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent / "ref_tile"))   # repo layout; the review dir holds a copy

PIN_LINE = re.compile(r"^\s*(?:-?[\d.]+\s+){2,}[v^]\s+(\S+)(?:\s+\((\S+)\))?")   # with or without fanout/cap/slew


def violated_blocks(text, path_type):
    """split an OpenSTA report_checks log into path blocks; keep the VIOLATED ones of path_type (max|min)"""
    out = []
    for blk in re.split(r"\n(?=Startpoint: )", text):
        if not blk.startswith("Startpoint: "):
            continue
        end = blk.find("slack (")
        if end < 0:
            continue
        blk = blk[:blk.find("\n", end) if blk.find("\n", end) > 0 else len(blk)]
        if f"Path Type: {path_type}" in blk and "slack (VIOLATED)" in blk:
            out.append(blk.strip())
    return out


def path_points(blk):
    """data-path pins of a report block (after the launch clock pin) -> [(name, is_port)]"""
    pts, data = [], False
    for line in blk.splitlines():
        if "data arrival time" in line:
            break
        if "input external delay" in line:
            data, pts = True, []                           # input-port launch: the next port line starts the path
            continue
        m = PIN_LINE.match(line)
        if not m:
            continue
        name, cell = m.group(1), m.group(2) or ""
        if cell in ("in", "out"):
            if data:                                       # (clock ports before the launch flop are not data)
                pts.append((name, True))
            continue
        if "/" not in name:
            continue
        inst, pin = name.rsplit("/", 1)
        if pin.upper() in ("CLK", "CK") and not data:
            pts = [(inst, False)]                          # launch flop: restart from its clock pin
            data = True
            continue
        if data:
            pts.append((inst, False))
    dedup = []
    for p in pts:
        if not dedup or dedup[-1] != p:
            dedup.append(p)
    return dedup


def norm(n):
    return n.replace("\\", "")


def path_coords(layout, groups):
    """[(color, k, [(x_um, y_um)...])] for every failing path whose cells / ports are in the layout dump"""
    cells = {norm(n): ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for n, m, s, *r in layout.get("std_cells", [])}
    cells.update({norm(b[0]): ((b[2] + b[4]) / 2, (b[3] + b[5]) / 2) for b in layout.get("blocks", [])})
    ports = {norm(n): ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for n, l, *r in layout.get("pins", [])}
    out = []
    for color, blks in groups:
        for k, blk in enumerate(blks):
            xy = [p for p in ((ports if is_port else cells).get(norm(n)) for n, is_port in path_points(blk)) if p]
            if xy:
                out.append((color, k, xy))
    return out


def zoom_window(layout, paths, margin=0.25, min_um=20.0):
    pts = [p for _, _, xy in paths for p in xy]
    if not pts:
        return None
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    w, h = max(x1 - x0, min_um), max(y1 - y0, min_um)
    d = layout["die"]
    return [max(d[0], x0 - margin * w), max(d[1], y0 - margin * h), min(d[2], x1 + margin * w), min(d[3], y1 + margin * h)]


def draw_paths(layout, groups, out_png, title, window=None):
    import layout_png as L
    v = L.View(window or layout["die"])
    c = L.Canvas(v.cw, v.ch)
    c.box(*v.rect(layout["die"]), (0, 0, 0), 2)
    for name, master, *r in layout.get("blocks", []):
        x0, y0, x1, y1 = v.rect(r)
        c.fill(x0, y0, x1, y1, (190, 190, 200))
        c.box(x0, y0, x1, y1, (90, 90, 110), 1)
    cells = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for n, m, st, *r in layout.get("std_cells", [])]
    if window:
        cells = [p for p in cells if window[0] <= p[0] <= window[2] and window[1] <= p[1] <= window[3]]
    step = max(1, len(cells) // 60000)
    for x, y in cells[::step]:
        c.fill(v.x(x), v.y(y), v.x(x) + 1, v.y(y) + 1, (150, 150, 150))
    drawn = 0
    for color, k, pts in path_coords(layout, groups):
        xy = [(v.x(p[0]), v.y(p[1])) for p in pts]
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            c.line(x0, y0, x1, y1, color, 2)
        (sx, sy), (ex, ey) = xy[0], xy[-1]
        c.fill(sx - 4, sy - 4, sx + 4, sy + 4, color)
        c.line(ex - 6, ey - 6, ex + 6, ey + 6, color, 2)
        c.line(ex - 6, ey + 6, ex + 6, ey - 6, color, 2)
        c.text(ex + 7, ey - 3, str(k + 1), color)
        drawn += 1
    c.text(6, 6, (title + (" (zoom %.0f,%.0f-%.0f,%.0f um)" % tuple(window) if window else ""))[:110], (0, 0, 0), 2)
    c.text(6, 24, f"failing sign-off paths: red = TT setup, blue = FF hold (start square, end cross, n = report order); "
                  f"{drawn} drawn", (60, 60, 60))
    return c.save(out_png)


def main(argv=None):
    argv = argv or sys.argv[1:]
    rev = Path(argv[0])
    meta = json.loads((rev / "review.json").read_text())
    so_path = Path(meta["signoff"])
    so = json.loads(so_path.read_text())
    (rev / "summary.txt").write_text(
        f"{meta.get('title', '')}\nkit {meta['kit']}\nodb {meta['odb']}\nsignoff {so_path}\nverdict {so.get('verdict')}\n"
        + "".join(f"  - {r}\n" for r in so.get("reasons") or []))
    groups = []
    for corner, ptype, fname, color in (("tt", "max", "paths_tt_setup.txt", (220, 0, 0)),
                                        ("ff", "min", "paths_ff_hold.txt", (0, 70, 220))):
        log = so_path.parent / corner / "sta.log"
        txt = log.read_text(errors="replace") if log.exists() else ""
        blks = violated_blocks(txt, ptype)
        if blks:
            (rev / fname).write_text("\n\n".join(blks) + "\n")
            print(f"AP_REVIEW_PATHS {rev / fname}")
        groups.append((color, blks))
    lj = rev / "layout.json"
    if not lj.exists():
        print("AP_REVIEW_ERROR no layout.json (dump failed); paths only")
        return 1
    import layout_png as L
    layout = json.loads(lj.read_text())
    for k, p in L.render_tile(layout, rev, None, meta.get("title", "")).items():
        if p:
            print(f"AP_REVIEW_PNG {p}")
    print(f"AP_REVIEW_PNG {draw_paths(layout, groups, rev / 'paths.png', meta.get('title', ''))}")
    win = zoom_window(layout, path_coords(layout, groups))
    if win:
        print(f"AP_REVIEW_PNG {draw_paths(layout, groups, rev / 'paths_zoom.png', meta.get('title', ''), win)}")
    try:
        lj.unlink()                                       # large (every std cell); the PNGs are the record
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
