"""Canonical realized soft CS banks shared by placement and clock planning.

One record describes one actual RTL class/stage, never a logical connection.
Sites are FF allocation lower-left corners. Constructors remove any superseded
manual sink_sites_um inventory; geometry cannot identify duplicate cell owners.
Bus station banks use internal_stations' existing exact-bank contract instead.
"""
import math


def _pair(value, label, positive=False):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"soft_reg_banks {label} requires an x/y pair")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           or (positive and v <= 0) for v in value):
        raise ValueError(f"soft_reg_banks {label} requires finite {'positive ' if positive else ''}coordinates")
    return tuple(float(v) for v in value)


def validated_banks(t):
    """Validate and return canonical records; absence preserves legacy behavior.

    Actual native FF matching and allocation footprint legality are checked by
    the emitter/planner. Duplicate bank identities, globs or exact sites fail
    here rather than count the same declared bank twice.
    """
    rows = t.get("clock", {}).get("soft_reg_banks", [])
    if not isinstance(rows, list):
        raise ValueError("soft_reg_banks must be an array")
    ids, globs, occupied, out = set(), set(), set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("soft_reg_banks record must be an object")
        for key, seen in (("id", ids), ("cell_glob", globs)):
            value = row.get(key)
            if not isinstance(value, str) or not value.strip() or value in seen:
                raise ValueError(f"soft_reg_banks requires unique nonempty {key}")
            seen.add(value)
        if not isinstance(row.get("source"), str) or not row["source"].strip():
            raise ValueError("soft_reg_banks requires nonempty source")
        cw, ch = _pair(row.get("bit_site_cell_um"), "bit_site_cell_um", positive=True)
        sites = row.get("bit_sites_um")
        if not isinstance(sites, list) or not sites:
            raise ValueError("soft_reg_banks requires nonempty flat bit_sites_um")
        points = []
        for site in sites:
            x, y = _pair(site, "bit_sites_um")
            if (x, y) in occupied:
                raise ValueError("soft_reg_banks duplicate FF allocation site")
            occupied.add((x, y))
            if "outline_um" in t:
                w, h = t["outline_um"]
                if x < 0 or y < 0 or x + cw > w + 1e-9 or y + ch > h + 1e-9:
                    raise ValueError("soft_reg_banks FF footprint outside outline")
            points.append((x, y))
        out.append(dict(row, bit_sites_um=points, bit_site_cell_um=(cw, ch)))
    return out


def sink_sites(t):
    """One unit clock sink at each realized FF allocation centre."""
    out = []
    for bank in validated_banks(t):
        cw, ch = bank["bit_site_cell_um"]
        out.extend((x + cw / 2, y + ch / 2, 1.0) for x, y in bank["bit_sites_um"])
    return out


def area(t):
    """Raw declared FF footprint sum, counted once per canonical bank.

    Excludes bank envelopes/clock space; this is not measured mapped area.
    """
    return sum(len(b["bit_sites_um"]) * b["bit_site_cell_um"][0] * b["bit_site_cell_um"][1]
               for b in validated_banks(t))
