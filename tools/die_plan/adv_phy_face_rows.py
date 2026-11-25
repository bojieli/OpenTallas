"""ADV-PHY-FACE-ROWS (FP-CONVERGE-QC 11-25, QC-PHY-GEN request; report only, never a gate).

Class: cell rows only on the far side of the macro from the ports.  QC phy_serdes: the SerDes macro fills the outline to the N face, the
ports (597-bit tx/rx flits) sit on the N face, the only free rows are 7 in the S strip: port buffers legalised 2320 um away, ~20k wire buffers,
DPL-0033.  Nothing read the free row area against the bus faces.

Per type with a hard macro (contents[] / hard_cores[] entry with a lef and origin_um + outline_um, type frame, um) and per bus face F with
buses: the free strip on F is the band between the macros that overlap the buses' window span (+MARGIN_UM each side) and the outline edge.
  FACE-STARVED  strip area on F < the port-buffer need: sum(bus width) x PORT_BUF_UM2 / ROW_UTIL (default 0.3 um2 per port, 0.5 util), or the
                strip is thinner than MIN_DEPTH_UM (one buffer row pair, 2 x 0.27 um).  Reports the opposite-face strip depth: a deeper
                opposite strip = FAR-SIDE (the legaliser puts the buffers there, one die height away).
findings(raw, plan_path, tree=None, **kw) -> WARN lines (+ LIST); never raises.  Fix: shrink / shift the macro to open a band >= the needed
depth on the port face, or move the port windows to the face with the free band (a move needs the matching neighbour port move).
"""
import os

CHECK = "ADV-PHY-FACE-ROWS"
PORT_BUF_UM2 = float(os.environ.get("OT_ADV_PHY_PORT_BUF_UM2", "0.3"))
ROW_UTIL = 0.5
MIN_DEPTH_UM = 0.54
MARGIN_UM = 100.0
MAX_EX = 4
FACES = ("N", "S", "E", "W")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _macros(t):
    out = []
    for key in ("contents", "hard_cores"):
        for c in t.get(key) or []:
            if isinstance(c, dict) and c.get("lef") and c.get("origin_um") and c.get("outline_um"):
                x, y = (float(v) for v in c["origin_um"][:2])
                w, h = (float(v) for v in c["outline_um"][:2])
                out.append((x, y, x + w, y + h, c.get("inst") or c.get("module") or "?"))
    return out


def strip_depth(face, lo, hi, macros, W, H):
    """free depth (um) on `face` over the span [lo, hi] along the face: outline edge minus the macro edge nearest to it"""
    d = H if face in ("N", "S") else W
    for x0, y0, x1, y1, _n in macros:
        a0, a1 = (x0, x1) if face in ("N", "S") else (y0, y1)
        if a1 <= lo or a0 >= hi:
            continue
        edge = {"N": H - y1, "S": y0, "E": W - x1, "W": x0}[face]
        d = min(d, max(edge, 0.0))
    return d


def type_findings(tn, t):
    if not t.get("outline_um"):
        return []
    W, H = (float(v) for v in t["outline_um"][:2])
    macros = _macros(t)
    if not macros:
        return []
    by = {}
    for b in t.get("buses") or []:
        f = b.get("face")
        if f in FACES and b.get("window_um"):
            by.setdefault(f, []).append(b)
    out = []
    for f, bs in sorted(by.items()):
        lo = min(float(b["window_um"][0]) for b in bs) - MARGIN_UM
        hi = max(float(b["window_um"][1]) for b in bs) + MARGIN_UM
        span = min(hi, W if f in ("N", "S") else H) - max(lo, 0.0)
        depth = strip_depth(f, lo, hi, macros, W, H)
        opp = {"N": "S", "S": "N", "E": "W", "W": "E"}[f]
        odepth = strip_depth(opp, lo, hi, macros, W, H)
        need = sum(int(b.get("width") or 1) for b in bs) * PORT_BUF_UM2 / ROW_UTIL
        area = depth * span
        if depth < MIN_DEPTH_UM or area < need:
            far = " FAR-SIDE" if odepth > depth else ""
            out.append(_w("FACE-STARVED" + far, f"{tn}: face {f} strip {depth:.2f} um x {span:.0f} um = {area:.0f} um2 < port-buffer need {need:.0f} um2 "
                          f"({sum(int(b.get('width') or 1) for b in bs)} ports); opposite face {opp} strip {odepth:.2f} um"))
    return out


def findings(raw, plan_path=None, tree=None, **_kw):
    try:
        out = []
        for tn, t in sorted((raw.get("partition_types") or {}).items()):
            if isinstance(t, dict):
                out += type_findings(tn, t)
        if out:
            out.append(f"LIST {CHECK} {len(out)} type face(s) with no free cell rows on a port face (fix: open a band on the port face, or move the windows)")
        return out[:60]
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
