"""Source-bound measured cell/row proof for a lattice/channel sizing exception.

This is a narrow coordinator-reviewed structural exception. Macro halos, declared
percentages and density bins cannot stand in for actual placed standard cells.
"""

import math
from bisect import bisect_right

CORE_MARGIN = 2.16
CHANNEL_UM = 20.0
APPROVERS = ("ROOT", "codex coordinator")


def lattice_band_errors(s, W, H, blocks, std_area):
    q = (s.get("fill_reason") or {}).get("lattice_channel_bound")
    errors = []
    if not isinstance(q, dict):
        return ["missing lattice_channel_bound object"]
    if not str(q.get("why", "")).strip() or q.get("approved_by") not in APPROVERS:
        errors.append("missing coordinator approval/reason")
    try:
        lo, hi = map(float, q["std_band_y_um"])
        density = std_area / ((W - 2 * CORE_MARGIN) * (hi - lo))
        if not (CORE_MARGIN <= lo < hi <= H - CORE_MARGIN and 0.4 <= density <= 0.6):
            errors.append("measured std-band density outside 40..60% or invalid band")
    except (ValueError, TypeError, KeyError, ZeroDivisionError):
        return errors + ["invalid standard-cell band"]
    if len(blocks) < 4:
        errors.append("fewer than four measured macros")
    for b in blocks:
        if b.get("kind") != "macro" or any(
            abs(b[a] / 43.2 - round(b[a] / 43.2)) > 1e-6 for a in ("x", "y")
        ):
            errors.append("macro origin off 43.2um lattice or non-macro child")
        if not (
            b["x"] >= CORE_MARGIN + CHANNEL_UM - 1e-6
            and b["y"] >= CORE_MARGIN + CHANNEL_UM - 1e-6
            and b["x"] + b["w"] <= W - CORE_MARGIN - CHANNEL_UM + 1e-6
            and b["y"] + b["h"] <= H - CORE_MARGIN - CHANNEL_UM + 1e-6
        ):
            errors.append("macro lacks core-edge channel")
        if not (b["y"] + b["h"] <= lo + 1e-6 or b["y"] >= hi - 1e-6):
            errors.append("macro overlaps standard-cell band")
    for i, b in enumerate(blocks):
        for c in blocks[i + 1 :]:
            gx = max(b["x"] - c["x"] - c["w"], c["x"] - b["x"] - b["w"])
            gy = max(b["y"] - c["y"] - c["h"], c["y"] - b["y"] - b["h"])
            if max(gx, gy) < CHANNEL_UM - 1e-6:
                errors.append("macro channel below 20um")
    return sorted(set(errors))


class RowCoverage:
    """Sweep the exact row union once; placement may contain thousands of fragments."""

    def __init__(self, rows):
        events = {}
        for i, (x0, y0, x1, y1) in enumerate(rows):
            if (
                not all(math.isfinite(v) for v in (x0, y0, x1, y1))
                or x1 <= x0
                or y1 <= y0
            ):
                raise ValueError("invalid legal row geometry")
            events.setdefault(y0, []).append((True, i, (x0, x1)))
            events.setdefault(y1, []).append((False, i, None))
        self.ys = sorted(events)
        self.spans = []
        active = {}
        for y in self.ys[:-1]:
            for add, i, span in events[y]:
                if add:
                    active[i] = span
                else:
                    active.pop(i, None)
            merged = []
            for left, right in sorted(active.values()):
                if merged and left <= merged[-1][1] + 1e-6:
                    merged[-1][1] = max(merged[-1][1], right)
                else:
                    merged.append([left, right])
            self.spans.append(merged)

    def covers(self, rect):
        x0, y0, x1, y1 = rect
        if (
            not all(math.isfinite(v) for v in rect)
            or x1 <= x0
            or y1 <= y0
            or not self.ys
            or y0 < self.ys[0] - 1e-6
            or y1 > self.ys[-1] + 1e-6
        ):
            return False
        i = max(0, bisect_right(self.ys, y0 + 1e-6) - 1)
        while i < len(self.spans) and self.ys[i] < y1 - 1e-6:
            if not any(
                left <= x0 + 1e-6 and right >= x1 - 1e-6
                for left, right in self.spans[i]
            ):
                return False
            i += 1
        return True


def rectangle_covered(rect, rows):
    """Exact row-union coverage, including multiheight cells."""
    return (rows if isinstance(rows, RowCoverage) else RowCoverage(rows)).covers(rect)


def measured_band_fill(s, floorplan, placed):
    """Refuse approval without actual placed cells/rows. Exceptions never add band area."""
    result = {"valid": False, "errors": []}
    errors = result["errors"]
    if not placed or placed.get("occupancy_schema") != "opentallas.layout.occupancy.v1":
        errors.append("missing actual placed-cell/row occupancy evidence")
        return result
    try:
        die = list(map(float, placed["die"]))
        if die != list(map(float, floorplan["die"])) or die[:2] != [0.0, 0.0]:
            errors.append("floorplan/placement die mismatch")
        W, H = die[2:]
        if sorted(placed["blocks"]) != sorted(floorplan["blocks"]):
            errors.append("floorplan/placement macro geometry mismatch")
        blocks = [
            dict(kind="macro", x=b[2], y=b[3], w=b[4] - b[2], h=b[5] - b[3])
            for b in placed["blocks"]
        ]
        q = s["fill_reason"]["lattice_channel_bound"]
        lo, hi = map(float, q["std_band_y_um"])
        rows = RowCoverage([list(map(float, r[1:])) for r in placed["rows"]])
        if not rectangle_covered([CORE_MARGIN, lo, W - CORE_MARGIN, hi], rows):
            errors.append("legal rows do not cover full-width standard-cell band")
        exceptions = q.get("placed_exceptions", [])
        if not isinstance(exceptions, list):
            raise ValueError("placed_exceptions must be an exact-instance list")
        ex = {}
        for e in exceptions:
            if (
                e.get("approved_by") not in APPROVERS
                or not str(e.get("why", "")).strip()
                or e.get("role") not in ("clock", "pin")
                or not e.get("inst")
                or e["inst"] in ex
                or any(c in e["inst"] for c in "*?[]")
            ):
                errors.append("invalid exact clock/pin exception approval")
            ex[e.get("inst")] = e
        seen, used = set(), set()
        total, band_area, outside = 0.0, 0.0, 0.0
        for c in placed["std_cells"]:
            name, master, status, x0, y0, x1, y1 = c
            box = [x0, y0, x1, y1]
            area = (x1 - x0) * (y1 - y0)
            total += area
            if name in seen or area <= 0 or status in ("NONE", "UNPLACED"):
                errors.append("duplicate/invalid/unplaced standard cell")
            seen.add(name)
            if not all(math.isfinite(v) for v in box) or not (
                x0 >= CORE_MARGIN - 1e-6
                and y0 >= CORE_MARGIN - 1e-6
                and x1 <= W - CORE_MARGIN + 1e-6
                and y1 <= H - CORE_MARGIN + 1e-6
            ):
                errors.append("standard cell outside physical core")
            if not rectangle_covered(box, rows):
                errors.append("standard cell outside actual legal rows")
            if (
                x0 >= CORE_MARGIN - 1e-6
                and x1 <= W - CORE_MARGIN + 1e-6
                and y0 >= lo - 1e-6
                and y1 <= hi + 1e-6
            ):
                band_area += area
            else:
                outside += area
                if name not in ex:
                    errors.append("unapproved standard cell outside full-width band")
                else:
                    used.add(name)
            for b in blocks:
                if (
                    min(x1, b["x"] + b["w"]) > max(x0, b["x"]) + 1e-6
                    and min(y1, b["y"] + b["h"]) > max(y0, b["y"]) + 1e-6
                ):
                    errors.append("standard cell overlaps macro")
        if used != set(ex):
            errors.append("unused/stale standard-cell exception")
        if not seen:
            errors.append("empty measured standard-cell population")
        # Repair/CTS may change area since the floorplan. Only the placed census
        # must equal its own stats; floorplan area never substitutes for that mass.
        stats_area = float(placed["stats"]["std_area"])
        if not math.isfinite(stats_area) or abs(stats_area - total) > max(
            0.15, total * 1e-5
        ):
            errors.append("placed std_area disagrees with actual cell census")
        errors.extend(lattice_band_errors(s, W, H, blocks, band_area))
        result.update(
            std_area_um2=total,
            band_area_um2=band_area,
            outside_area_um2=outside,
            band_density=band_area / ((W - 2 * CORE_MARGIN) * (hi - lo)),
            exception_instances=sorted(used),
        )
    except (KeyError, ValueError, TypeError, ZeroDivisionError, IndexError) as exc:
        errors.append("malformed measured occupancy: " + str(exc))
    result["errors"] = sorted(set(errors))
    result["valid"] = not errors
    return result
