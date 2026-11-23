"""ADV-BANK-OFFAREA (COORD 11-22, estimator, never a gate): exact / bank flop sites outside a type's placeable rows.

Every exact flop site the kit places FIRM at a fixed coordinate must lie on a placement row: inside CORE_AREA, the type outline
minus its core inset (kit_fit.kit_core_area: CORE_MARGIN_UM 4.32 on each side unless kit_core_margins_um says otherwise).  A site
outside it fails at place with "exact internal bank site is not on row/site" (kit_istations is_exact_bank) or the soft-CS / packed
equivalent, a day after the plan showed it.  Known positive (OPUS-FIX-KV-PV-R7 21:59): the D28 R5 exact bit-group banks on
kv3_pv_v3 (internal_stations 5, 6) and kv3_pv_v3e (0, 5) carried 749 bit sites outside CORE_AREA.

Sites checked, with their cell footprint (default 1.404 x 0.27 um, the async-reset DFF):
  partition_types[T].internal_stations[k].bit_sites_um[stage][bit]    (bit_site_cell_um)
  partition_types[T].internal_stations[k].face_bit_sites_um[bit]      (bit_site_cell_um)
  partition_types[T].soft_reg_banks[k].bit_sites_um[bit]              (cell_um / bit_site_cell_um)
A site is off-area when x < x0, y < y0, x + w > x1 or y + h > y1 for CORE_AREA (x0, y0, x1, y1).  One line per type
(count, rows, worst distance outside, first examples).
"""
import json
import sys
from pathlib import Path

CHECK = "ADV-BANK-OFFAREA"
CELL = (1.404, 0.27)
EPS = 1e-6


def _w(*parts):
    return " ".join(["WARN", CHECK] + [str(p) for p in parts])


def _core_area(t):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from kit_fit import kit_core_area
        return kit_core_area(t)
    except Exception:  # noqa: BLE001 -- schema-less fixture or older tree: the default inset
        w, h = t["outline_um"]
        m = 4.32
        return [m, m, w - m, h - m]


def _cell(row):
    c = row.get("bit_site_cell_um") or row.get("cell_um") or CELL
    try:
        return float(c[0]), float(c[1])
    except (TypeError, ValueError, IndexError):
        return CELL


def _sites(t):
    """-> [(row label, x, y, cw, ch)] of every exact site of a type"""
    out = []
    for k, e in enumerate(t.get("internal_stations") or []):
        cw, ch = _cell(e)
        for j, st in enumerate(e.get("bit_sites_um") or []):
            for b, xy in enumerate(st or []):
                if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                    out.append((f"internal_stations[{k}] stage {j} bit {b}", float(xy[0]), float(xy[1]), cw, ch))
        for b, xy in enumerate(e.get("face_bit_sites_um") or []):
            if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                out.append((f"internal_stations[{k}] face bit {b}", float(xy[0]), float(xy[1]), cw, ch))
    for k, e in enumerate(t.get("soft_reg_banks") or []):
        cw, ch = _cell(e)
        for b, xy in enumerate(e.get("bit_sites_um") or []):
            if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                out.append((f"soft_reg_banks[{k}] {e.get('id', '')} bit {b}".replace("  ", " "), float(xy[0]), float(xy[1]), cw, ch))
    return out


def type_hits(t):
    """-> (core area, [(label, x, y, distance outside um)])"""
    if not t.get("outline_um"):
        return None, []
    x0, y0, x1, y1 = _core_area(t)
    hits = []
    for lab, x, y, cw, ch in _sites(t):
        d = max(x0 - x, y0 - y, x + cw - x1, y + ch - y1)
        if d > EPS:
            hits.append((lab, x, y, round(d, 3)))
    return (x0, y0, x1, y1), hits


def _findings(raw, plan_path, tree=None, **kw):
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        area, hits = type_hits(t)
        if not hits:
            continue
        rows = sorted({h[0].split(" stage ")[0].split(" face ")[0].split(" bit ")[0] for h in hits})
        worst = max(hits, key=lambda h: h[3])
        ex = "; ".join(f"{h[0]} ({h[1]:g},{h[2]:g}) +{h[3]:g}" for h in hits[:3])
        out.append(_w(f"{tn}: {len(hits)} exact / bank flop site(s) outside CORE_AREA "
                      f"[{area[0]:g} {area[1]:g} {area[2]:g} {area[3]:g}] on {len(rows)} row(s) ({', '.join(rows[:4])}"
                      f"{' ...' if len(rows) > 4 else ''}); worst {worst[3]:g} um outside; place refuses them "
                      f"(not on row/site): {ex}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    p = sys.argv[1]
    for line in findings(json.loads(Path(p).read_text()), p):
        print(line)
