"""Plan I/O through the shared opentools plan schema `opentools.plan/1`.

The schema lives in opentools/common/plan.py (owner OSS-CLKPLAN-1); this module
does not fork it.  ohier works on an internal *hier view* (dict with design,
die.bbox_um, clocks, regions, pins, budgets, metrics) and maps it onto the shared
document as follows (COORD 10-27 19:11: one clock region == one partition):

  shared field          ohier content
  ------------          -------------
  die {w, h}            die outline
  regions[]             {name: R<i>, rect: partition bbox, partition: <module>}
  macros[]              every partition as a hard block at die level:
                        {name: u_<module>, master: <module>, rect, kind: hard_core,
                         region: R<i>, clock_pins: [{name: clk, xy, insertion_ps}]}
                        (insertion_ps filled from the partition abstract by `ohier abstract`)
  clock                 {name, period_ps, target_latency_ps}  (common partition latency L)
  hier                  OUTPUT of this tool: the full hier view (pins, budgets, metrics,
                        region details) -- the only key ohier owns.

Input region map (12.13 locality regions -> partitions): an `opentools.plan/1`
document whose regions[] carry `name`, `rect` and (optionally) `partition`, plus
`hier.region_members = {region name: [instance-path prefix, ...]}`.  See
`region_map()`.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_OT = os.path.abspath(os.path.join(_HERE, "..", ".."))       # opentools/
if _OT not in sys.path:
    sys.path.insert(0, _OT)
from common import plan as CP    # noqa: E402  shared schema (OSS-CLKPLAN-1)

SCHEMA = CP.SCHEMA
HIER_VERSION = "ohier/0.2"

REGION_KEYS = ("id", "kind", "clock_region", "bbox_um", "module", "cells",
               "std_area_um2", "macro_area_um2", "macros", "items", "ports")
BUDGET_KEYS = ("net", "from_region", "to_regions", "period_ps", "src_budget_ps",
               "wire_ps", "dst_budget_ps", "clock_latency_ps")
PIN_KEYS = ("region", "port", "net", "edge", "offset_um", "layer", "xy_um")


def new_plan(design, units="um"):
    """Internal hier view."""
    return {"version": HIER_VERSION, "design": design, "units": units,
            "die": {}, "clocks": [], "macros": [], "regions": [], "budgets": [], "pins": [],
            "metrics": {}, "producer": "opentools/hier"}


def region_name(rid):
    return f"R{rid}"


def to_shared(hv, base=None):
    """hier view -> opentools.plan/1 document.  `base` (an input shared plan, e.g. the
    region map) is kept: its fields stay byte-stable, ohier only adds/overwrites `hier`,
    and the partition entries in regions[] / macros[]."""
    P = json.loads(json.dumps(base)) if base else {"schema": SCHEMA, "name": hv["design"]}
    P["schema"] = SCHEMA
    die = hv["die"]["bbox_um"]
    P.setdefault("die", {"w": die[2] - die[0], "h": die[3] - die[1]})
    ck = hv["clocks"][0] if hv["clocks"] else {}
    clock = P.setdefault("clock", {})
    clock.setdefault("name", ck.get("name", "clk"))
    clock.setdefault("period_ps", ck.get("period_ps"))
    clock.setdefault("target_latency_ps", ck.get("region_latency_target_ps"))
    regs = {r.get("name"): r for r in P.get("regions", [])}
    macs = {m.get("name"): m for m in P.get("macros", [])}
    pin_xy = {(p["region"], p["port"]): p["xy_um"] for p in hv.get("pins", [])}
    for r in hv["regions"]:
        rn = r.get("region_name") or region_name(r["id"])
        reg = regs.get(rn)
        if reg is None:
            reg = {"name": rn}
            P.setdefault("regions", []).append(reg)
            regs[rn] = reg
        reg.setdefault("rect", list(r["bbox_um"]))
        reg["partition"] = r["module"]
        inst = f"u_{r['module']}"
        m = macs.get(inst)
        if m is None:
            m = {"name": inst}
            P.setdefault("macros", []).append(m)
            macs[inst] = m
        cxy = None
        for c in hv["clocks"]:
            cxy = pin_xy.get((r["id"], c.get("port", "clk"))) or cxy
        m.update({"master": r["module"], "rect": list(r["bbox_um"]), "kind": "hard_core", "region": rn})
        old = {cp.get("name"): cp for cp in m.get("clock_pins", [])}
        cp = old.get("clk", {"name": "clk"})
        cp["xy"] = list(cxy) if cxy else [(r["bbox_um"][0] + r["bbox_um"][2]) / 2,
                                          (r["bbox_um"][1] + r["bbox_um"][3]) / 2]
        cp.setdefault("insertion_ps", {})
        cp["region"] = rn
        m["clock_pins"] = [cp]
    P["hier"] = dict(P.get("hier", {}), **hv)
    return P


def save(hv, path, base=None):
    P = to_shared(hv, base)
    errs = CP.validate(CP.fill_defaults(P))
    if errs:
        raise ValueError("ohier wrote an invalid shared plan:\n  " + "\n  ".join(errs))
    CP.save(P, path)
    return P


def load_shared(path):
    return CP.load(path)


def load(path):
    """Shared plan file -> internal hier view (validated by the shared loader)."""
    P = CP.load(path)
    if "hier" not in P or "regions" not in P["hier"]:
        raise ValueError(f"{path}: no ohier output (hier.regions); run `ohier plan` first")
    return P["hier"]


def region_map(path_or_doc):
    """Read the region map (input).  -> (doc, [dict(name, rect|None, partition|None, members[])])"""
    P = CP.load(path_or_doc) if isinstance(path_or_doc, str) else CP.fill_defaults(path_or_doc)
    mem = (P.get("hier") or {}).get("region_members") or {}
    out = []
    for r in P["regions"]:
        out.append({"name": r["name"], "rect": r.get("rect"), "partition": r.get("partition"),
                    "members": list(mem.get(r["name"], []))})
    unknown = set(mem) - {r["name"] for r in out}
    if unknown:
        raise ValueError(f"hier.region_members names unknown regions: {sorted(unknown)}")
    return P, out


def validate(plan):
    """Cheap structural checks on the hier view; returns a list of problems (empty = OK)."""
    errs = []
    ids = set()
    for r in plan.get("regions", []):
        for k in ("id", "bbox_um", "module"):
            if k not in r:
                errs.append(f"region missing {k}: {r.get('id')}")
        if r.get("id") in ids:
            errs.append(f"duplicate region {r.get('id')}")
        ids.add(r.get("id"))
        x0, y0, x1, y1 = r.get("bbox_um", (0, 0, 0, 0))
        if not (x1 > x0 and y1 > y0):
            errs.append(f"region {r.get('id')} has empty bbox")
    die = plan.get("die", {}).get("bbox_um")
    if die:
        for r in plan.get("regions", []):
            x0, y0, x1, y1 = r["bbox_um"]
            if x0 < die[0] - 1e-6 or y0 < die[1] - 1e-6 or x1 > die[2] + 1e-6 or y1 > die[3] + 1e-6:
                errs.append(f"region {r['id']} outside die")
    regs = plan.get("regions", [])
    for i, a in enumerate(regs):
        for b in regs[i + 1:]:
            ax0, ay0, ax1, ay1 = a["bbox_um"]
            bx0, by0, bx1, by1 = b["bbox_um"]
            if min(ax1, bx1) - max(ax0, bx0) > 1e-6 and min(ay1, by1) - max(ay0, by0) > 1e-6:
                errs.append(f"regions {a['id']} and {b['id']} overlap")
    for p in plan.get("pins", []):
        if p["region"] not in ids:
            errs.append(f"pin {p['port']} on unknown region {p['region']}")
    return errs
