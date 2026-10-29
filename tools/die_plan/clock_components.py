"""Measured clock delay decomposition, shared by the CA planner and die STA.

Only raw, source-edge-resolved T/N/F/M arrivals are accepted. The wire entering a
cell belongs to that cell's stage; the final port wire belongs to its last driver.
Components telescope to the measured arrival, including every upstream stage.
"""
import copy
import math
import re
from pathlib import Path

KEYS = ("late_ps", "early_ps", "fall_late_ps", "fall_early_ps")
NODE_KEYS = ("node_late_ps", "node_early_ps", "node_fall_late_ps", "node_fall_early_ps")
INV = "CKINVDCx16_ASAP7_75t_R"


def annotate(arrivals, netlist, raw):
    import die_sta_related as D
    from trial_tap_arrivals import read_arr
    if not any(line.startswith("# OT_EDGES v1") for line in Path(raw).read_text().splitlines()[:5]):
        raise ValueError("clock components: OT_EDGES v1 measured both-edge readout required")
    T, N, F, M = read_arr(raw)
    cells, drivers = {}, {}
    text = Path(netlist).read_text()
    aliases = dict(re.findall(r"\bassign\s+(\\?[^\s;=]+)\s*=\s*(\\?[^\s;]+)\s*;", text))

    def driver(net):
        seen = set()
        while net in aliases:
            if net in seen:
                raise ValueError("clock components: assign loop " + net)
            seen.add(net)
            net = aliases[net]
        return drivers.get(net)

    for m in D._INST_RE.finditer(text):
        pins = dict(D._PIN_RE.findall(m.group(3)))
        if "A" in pins and "Y" in pins:
            cells[m.group(2)] = (m.group(1), pins["A"], pins["Y"])
            if pins["Y"] in drivers:
                raise ValueError("clock components: multiple drivers " + pins["Y"])
            drivers[pins["Y"]] = m.group(2)
    if not cells:
        raise ValueError("clock components: no clock cells")
    memo, active = {}, set()

    def arrival(cell):
        if cell not in N or cell not in M:
            raise ValueError(f"clock components: missing measured rise/fall node {cell}")
        return N[cell] + M[cell]

    def increment(parts, master, delta):
        if not all(math.isfinite(x) and x >= -0.001 for x in delta):
            raise ValueError(f"clock components: invalid measured increment for {master}: {delta}")
        # Tiny negative differences can arise from printed-arrival rounding.
        old = parts.get(master, (0.,) * 4)
        parts[master] = tuple(x + y for x, y in zip(old, delta))

    def cell_parts(cell):
        if cell in memo:
            return memo[cell]
        if cell in active:
            raise ValueError("clock components: clock loop " + cell)
        active.add(cell)
        master, pin, _ = cells[cell]
        parent = driver(pin)
        base = arrival(parent) if parent else (0.,) * 4
        parts = dict(cell_parts(parent)) if parent else {}
        increment(parts, master, tuple(x-y for x, y in zip(arrival(cell), base)))
        memo[cell] = parts
        active.remove(cell)
        return parts

    def records(parts):
        return [dict(master=m, **dict(zip(KEYS, v))) for m, v in sorted(parts.items())]

    out = copy.deepcopy(arrivals)
    for tap in out["taps"]:
        port = tap["port"]
        cell = driver(port)
        if cell is None or port not in T or port not in F:
            raise ValueError(f"clock components: missing driven both-edge tap {port}")
        v = T[port][:2] + F[port]
        for k, x in zip(KEYS, v):
            if k not in tap or abs(tap[k]-x) > .001:
                raise ValueError(f"clock components: stale tap arrival {port} {k}")
        parts = dict(cell_parts(cell))
        increment(parts, cells[cell][0], tuple(x-y for x,y in zip(v, arrival(cell))))
        tap["clock_components"] = records(parts)
    nc = out.get("node_cell")
    if not nc or set(nc) != set(out.get("node_late_ps", {})):
        raise ValueError("clock components: complete node-to-cell inventory required")
    out["node_clock_components"] = {}
    for key, cell in nc.items():
        for k, x in zip(NODE_KEYS, arrival(cell)):
            if key not in out.get(k, {}) or abs(out[k][key]-x) > .001:
                raise ValueError(f"clock components: stale node arrival {key} {k}")
        out["node_clock_components"][key] = records(cell_parts(cell))
    out["clock_components_basis"] = "measured source-edge T/N/F/M; per-master telescoping stage delays"
    return out


def scaled(parts, values, corner, mode):
    import die_sta_related as D
    if not parts:
        raise ValueError("clock components: empty decomposition")
    totals = [sum(float(p[k]) for p in parts) for k in KEYS]
    for k, total in zip(KEYS, totals):
        if not math.isfinite(total) or k not in values or abs(total-values[k]) > .002:
            raise ValueError("clock components: decomposition does not sum to raw " + k)
    out = dict.fromkeys(KEYS, 0.)
    factors = ("rise_late", "rise_early", "fall_late", "fall_early")
    for p in parts:
        master = p["master"]
        if mode == "spice_edge" and master == INV:
            late, early = D.SPICE_CLOCK_CAL_INV[corner], D.SPICE_CLOCK_CAL_INV_EARLY[corner]
            fs = dict(rise_late=late, fall_late=late, rise_early=early, fall_early=early)
        else:
            fs = D.cell_cal_factors(corner, [master])
        for k, fk in zip(KEYS, factors):
            value = float(p[k])
            if not math.isfinite(value) or value < -.001:
                raise ValueError("clock components: invalid component " + k)
            out[k] += value * fs[fk]
    out["early_ps"] = min(out["early_ps"], out["late_ps"])
    out["fall_early_ps"] = min(out["fall_early_ps"], out["fall_late_ps"])
    return out


def apply(meta, taps, corner, mode):
    """Calibrate decomposed taps and nodes together; CPPR uses the same node arrivals."""
    nodes = meta.get("node_clock_components")
    if not nodes or set(nodes) != set(meta.get("node_late_ps", {})):
        raise ValueError("clock components: incomplete node decomposition")
    m, t = dict(meta), {}
    for k in NODE_KEYS:
        m[k] = {}
    for name, parts in nodes.items():
        raw = {k: meta[nk][name] for k, nk in zip(KEYS, NODE_KEYS)}
        values = scaled(parts, raw, corner, mode)
        for k, nk in zip(KEYS, NODE_KEYS):
            m[nk][name] = values[k]
    for name, tap in taps.items():
        t[name] = dict(tap, **scaled(tap.get("clock_components"), tap, corner, mode))
    m["cppr_node_range_ps"] = {k: round(max(0., m["node_late_ps"][k]-m["node_early_ps"][k]), 4)
                               for k in meta.get("cppr_node_range_ps", {})}
    m["clock_cal_components"] = mode
    return m, t
