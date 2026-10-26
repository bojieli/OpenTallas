"""Optional clock-tap overlays for placement/clock review plots.

Call ``draw_tap_overlay(ax, read_tap_overlay(table))`` from a renderer before
saving its figure. Actual records require an explicit ``actual_odb`` basis and
instance/owner identity; a centroid/created-port table is never upgraded to an
actual placement record. Legacy NL/N59 tables are accepted only with
``basis="planned"`` and are visibly marked PLANNED.

Actual TSV columns: inst, owner_root, x_um, y_um, load_sinks, radius_um,
cap_sinks, radius_limit_um, coordinate_basis. Optional: kind, checkpoint_sha256.
Radius is the measured maximum Manhattan sink distance, not the policy limit.
The limits are the collector's declared policy; this module does not infer them.
"""
from dataclasses import dataclass
import csv
import math
from pathlib import Path


@dataclass(frozen=True)
class TapOverlay:
    name: str
    owner_root: str
    x_um: float
    y_um: float
    load_sinks: int
    radius_um: float
    cap_sinks: int | None
    radius_limit_um: float | None
    coordinate_basis: str
    kind: str = "reg"
    checkpoint_sha256: str = ""

    @property
    def violations(self):
        reasons = []
        if self.cap_sinks is not None and self.load_sinks > self.cap_sinks:
            reasons.append("load")
        if self.radius_limit_um is not None and self.radius_um > self.radius_limit_um:
            reasons.append("radius")
        return tuple(reasons)


def _number(row, key, *, integer=False):
    try:
        value = float(row[key])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"missing/invalid {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"nonfinite {key}")
    if integer and (value < 0 or value != int(value)):
        raise ValueError(f"{key} must be a nonnegative integer")
    return int(value) if integer else value


def read_tap_overlay(path, *, basis="actual"):
    """Read an explicit actual-ODB table, or an explicitly requested legacy plan.

    No coordinate, owner, cap or radius is silently filled in for actual data.
    The caller must produce the actual table from its fresh checkpoint; the
    optional checkpoint hash is retained for the plot's review sidecar.
    """
    if basis not in ("actual", "planned"):
        raise ValueError("basis must be actual or planned")
    records = []
    names = set()
    with Path(path).open(newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream, delimiter="\t"), 2):
            try:
                if basis == "actual":
                    if row.get("coordinate_basis") != "actual_odb":
                        raise ValueError("actual overlay requires coordinate_basis=actual_odb")
                    name = row.get("inst", "").strip()
                    owner = row.get("owner_root", "").strip()
                    if not name or not owner:
                        raise ValueError("actual overlay requires inst and owner_root")
                    load = _number(row, "load_sinks", integer=True)
                    radius = _number(row, "radius_um")
                    cap = _number(row, "cap_sinks", integer=True)
                    limit = _number(row, "radius_limit_um")
                    coordinate_basis = "actual_odb"
                else:
                    # Existing NL port table and N59 centroid table.
                    name = (row.get("subtap") or row.get("port") or row.get("inst") or "").strip()
                    owner = (row.get("owner_root") or row.get("port") or "").strip()
                    if not name:
                        raise ValueError("planned overlay requires a tap identity")
                    load = _number(row, "sinks" if "sinks" in row else "load_sinks", integer=True)
                    radius = _number(row, "max_dist_um" if "max_dist_um" in row else "radius_um")
                    cap = _number(row, "cap_sinks", integer=True) if row.get("cap_sinks") else None
                    limit = _number(row, "radius_limit_um") if row.get("radius_limit_um") else None
                    coordinate_basis = "planned"
                if name in names:
                    raise ValueError(f"duplicate tap identity {name}")
                names.add(name)
                x, y = _number(row, "x_um"), _number(row, "y_um")
                if radius < 0 or (limit is not None and limit < 0):
                    raise ValueError("radius and radius limit must be nonnegative")
                records.append(TapOverlay(name, owner, x, y, load, radius, cap, limit,
                                          coordinate_basis, row.get("kind") or "reg",
                                          row.get("checkpoint_sha256") or ""))
            except ValueError as exc:
                raise ValueError(f"{path}:{line}: {exc}") from exc
    if not records:
        raise ValueError(f"{path}: empty tap table")
    return records


def draw_tap_overlay(ax, records, *, annotate=True, show_radius=False):
    """Draw on an existing physical-coordinate Axes; return a review summary.

    Diamonds = actual ODB instances, hollow triangles = explicitly planned taps.
    Owners use consistent colours; actual load/radius overruns have a red edge.
    Optional diamonds outline the Manhattan radius measured at the checkpoint.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    owners = sorted({tap.owner_root for tap in records})
    cmap = plt.get_cmap("tab20")
    colours = {owner: cmap(i % 20) for i, owner in enumerate(owners)}
    summary = {"actual": 0, "planned": 0, "empty_loads": 0,
               "violations": [], "checkpoints": sorted({tap.checkpoint_sha256 for tap in records
                                                         if tap.checkpoint_sha256})}
    labelled = set()
    for tap in records:
        actual = tap.coordinate_basis == "actual_odb"
        basis = "actual" if actual else "planned"
        summary[basis] += 1
        summary["empty_loads"] += int(tap.load_sinks == 0)
        if tap.violations:
            summary["violations"].append({"inst": tap.name, "reasons": list(tap.violations)})
        colour = colours[tap.owner_root] if actual else "0.45"
        edge = "red" if actual and tap.violations else colour
        label = "actual ODB sub-tap" if actual else "PLANNED tap (not placed evidence)"
        ax.scatter([tap.x_um], [tap.y_um], marker="D" if actual else "^", s=38,
                   facecolors=colour if actual else "none", edgecolors=edge,
                   linewidths=1.5 if tap.violations else 0.9, zorder=12,
                   label=label if basis not in labelled else "_nolegend_")
        labelled.add(basis)
        if show_radius:
            x, y, r = tap.x_um, tap.y_um, tap.radius_um
            ax.add_patch(Polygon([(x-r, y), (x, y+r), (x+r, y), (x, y-r)],
                                 fill=False, edgecolor=edge, alpha=.3, linewidth=.5, zorder=10))
        if annotate:
            cap = "?" if tap.cap_sinks is None else str(tap.cap_sinks)
            limit = "?" if tap.radius_limit_um is None else f"{tap.radius_limit_um:g}"
            text = ("" if actual else "PLANNED ") + tap.name + f" [{tap.owner_root}]"
            text += f"\nn={tap.load_sinks}/{cap} r={tap.radius_um:g}/{limit}um"
            if tap.violations:
                text += " OVER:" + ",".join(tap.violations)
            ax.annotate(text, (tap.x_um, tap.y_um), xytext=(3, 3),
                        textcoords="offset points", fontsize=5, color=edge, zorder=13)
    return summary
