#!/usr/bin/env python3
"""Harvest exact placed pin/clock exceptions for a fill_reason.lattice_channel_bound band kit (HBM-MC3G 10-20).

measured_band_fill() accepts a standard cell outside the full-width band only when the spec lists it by exact
instance name with role pin/clock and an approver.  A band kit (physical/common_flow/std_band_fence.tcl) writes the
flow's own role list (pin = cells FIRM at their pins before global placement or on a port net; clock = clock-net
drivers) and the gate saves the placed census with it (gate_layout/placed_occupancy.json).  This tool turns that census
into placed_exceptions:
  * it REFUSES when the lattice_channel_bound itself carries no coordinator approval (no approval is created here);
  * every exception copies that approval and names its role source; it never adds band area;
  * any standard cell outside the band that the role list does not name (an ordinary cell the fence failed to hold)
    is an error: nothing is written and the gate's measured_band_fill must fail on it.
Usage: band_exception_harvest.py SPEC.json PLACED.json [--write] [--json OUT]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measured_band_fill import APPROVERS, CORE_MARGIN  # noqa: E402

ROLES_SCHEMA = "opentallas.band_roles.v1"


def harvest(spec, placed):
    """-> (exceptions, errors).  Pure: no file is touched."""
    errors = []
    q = (spec.get("fill_reason") or {}).get("lattice_channel_bound")
    if not isinstance(q, dict):
        return [], ["spec has no fill_reason.lattice_channel_bound"]
    approver = q.get("approved_by")
    if approver not in APPROVERS:
        errors.append("lattice_channel_bound has no coordinator approval: approve the band first (nothing harvested)")
    if not placed or placed.get("occupancy_schema") != "opentallas.layout.occupancy.v1":
        return [], errors + ["missing actual placed-cell occupancy evidence"]
    roles = placed.get("band_roles")
    if not isinstance(roles, dict) or roles.get("schema") != ROLES_SCHEMA:
        return [], errors + ["placed census carries no band role list (kit without std_band_fence?)"]
    try:
        lo, hi = map(float, q["std_band_y_um"])
        rlo, rhi = map(float, str(roles.get("band_y_um")).split(":"))
        if abs(rlo - lo) > 1e-6 or abs(rhi - hi) > 1e-6:
            errors.append("role list band differs from the spec band")
        W = float(placed["die"][2])
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        return [], errors + [f"invalid band/die: {exc}"]
    pin, clk = set(roles.get("pin", [])), set(roles.get("clock", []))
    if pin & clk:
        errors.append(f"{len(pin & clk)} instances carry both roles")
    out, unowned = [], []
    for c in placed["std_cells"]:
        name, _master, _status, x0, y0, x1, y1 = c
        inside = x0 >= CORE_MARGIN - 1e-6 and x1 <= W - CORE_MARGIN + 1e-6 and y0 >= lo - 1e-6 and y1 <= hi + 1e-6
        if inside:
            continue
        role = "pin" if name in pin else "clock" if name in clk else None
        if role is None:
            unowned.append(name)
            continue
        out.append({"inst": name, "role": role, "approved_by": approver,
                    "why": f"{role} cell outside the std band, from the flow role list at {roles.get('stage')} "
                           f"(std_band_fence.tcl); harvested by band_exception_harvest.py"})
    if unowned:
        errors.append(f"{len(unowned)} ordinary standard cells outside the band without a pin/clock role "
                      f"(fence did not hold them): {sorted(unowned)[:8]}")
    if any(any(ch in e["inst"] for ch in "*?") for e in out):
        errors.append("wildcard instance name")
    return sorted(out, key=lambda e: e["inst"]), sorted(set(errors))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("placed")
    ap.add_argument("--write", action="store_true", help="write placed_exceptions into the spec (only when clean)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text())
    placed = json.loads(Path(a.placed).read_text())
    ex, errors = harvest(spec, placed)
    rep = {"spec": a.spec, "placed": a.placed, "exceptions": len(ex),
           "roles": {r: sum(e["role"] == r for e in ex) for r in ("pin", "clock")}, "errors": errors}
    if a.json:
        Path(a.json).write_text(json.dumps(dict(rep, instances=ex), indent=1) + "\n")
    print(json.dumps(rep))
    if errors:
        return 1
    if a.write:
        spec["fill_reason"]["lattice_channel_bound"]["placed_exceptions"] = ex
        Path(a.spec).write_text(json.dumps(spec, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
