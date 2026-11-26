#!/usr/bin/env python3
"""src_centroid.py (C-LEG405 SRC-NOT-AT-LEAF, 11-26): the real source / consumer register of an internal_stations bus, from placed geometry.

ADV-LEG405-STAGED and the G0 routed_reach check start an out bus at its leaf_um / from_um and end an in bus at to_um.  That is the
pin side of the chain, not where the registers are: QC sle_su_c x_su_l0_o launches from core flops (procdff_*) about 680 um from leaf_um, so the
placed first hop is 565.8 um while the plan reads 171.  The geom.tsv that the automated review dumps from 3_place.odb (tools/autopilot/geom_dump.tcl:
C cells, N nets) has them.  For a station chain u_ist_<bus>_<k> (k = 0 .. n-1):

  out bus: first stations u_ist_<bus>_0/* (seq cells); every net that feeds one of them is traced back through inverters / buffers to its
           driving register: the SOURCE registers; hop = Manhattan(source register, first-station register).
  in bus : last station u_ist_<bus>_<n-1>/*; every net that its Q drives is traced forward to the consuming registers: the CONSUMER registers;
           hop = Manhattan(last-station register, consumer register).

source_chain(geom, bus) -> dict(src_centroid, n_edges, max_um, n_over, worst).  Order of preference for the chain end used by the checks:
plan regs_um (explicit), this placed centroid, leaf_um / from_um / to_um.   Report only.
"""
import re
import sys

LIMIT_UM = 405.0
_RST = re.compile(r"(rst|reset|arst)", re.I)


def load(path):
    """-> (cells {id: (kind, x, y, name)}, drv {sink_id: [driver_id, ...]} (a flop has a D driver and a reset driver), fanout {driver_id: [sink_id]});
    coordinates are cell centres, um"""
    cells, drv, fan = {}, {}, {}
    with open(path, errors="replace") as f:
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            t = p[0]
            try:
                if t == "C":
                    cells[int(p[1])] = (p[2], (float(p[4]) + float(p[6])) / 2, (float(p[5]) + float(p[7])) / 2, p[8] if len(p) > 8 else "")
                elif t == "N" and len(p) > 3 and p[2].startswith("i") and not p[2].endswith("c"):
                    d = int(p[2][1:])
                    for s in p[3:]:
                        if s.startswith("i") and not s.endswith("c") and s[1:].isdigit():
                            drv.setdefault(int(s[1:]), []).append(d)
                            fan.setdefault(d, []).append(int(s[1:]))
            except (ValueError, IndexError):
                continue
    return cells, drv, fan


def _station_cells(cells, bus, k):
    pre = re.compile(r"(^|\.)u_ist_" + re.escape(bus) + "_" + str(k) + r"/")
    return [i for i, (kind, _x, _y, nm) in cells.items() if kind == "S" and pre.search(nm)]


def _n_stations(cells, bus):
    pre = re.compile(r"(^|\.)u_ist_" + re.escape(bus) + r"_(\d+)/")
    ks = {int(m.group(2)) for _i, (kind, _x, _y, nm) in cells.items() if kind == "S" for m in [pre.search(nm)] if m}
    return max(ks) + 1 if ks else 0


def _back(cells, drv, i, depth=6):
    """driving (non-reset) register of cell i through inverters / buffers (kind B) -> id or None"""
    front = [i]
    for _ in range(depth):
        nxt = []
        for c in front:
            for d in drv.get(c, []):
                if d not in cells:
                    continue
                kind, _x, _y, nm = cells[d]
                if kind == "S":
                    if not _RST.search(nm):
                        return d
                elif kind == "B":
                    nxt.append(d)
        front = nxt
        if not front:
            return None
    return None


def _fwd(cells, fan, i, depth=6):
    out, front = [], [i]
    for _ in range(depth):
        nxt = []
        for c in front:
            for s in fan.get(c, []):
                if s not in cells:
                    continue
                kind, _x, _y, nm = cells[s]
                if kind == "S" and not _RST.search(nm):
                    out.append(s)
                elif kind == "B":
                    nxt.append(s)
        front = nxt
        if not front:
            break
    return out


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def source_chain(g, bus, out_bus=True, limit=LIMIT_UM):
    """g = load(geom.tsv).  -> dict or None when the bus has no u_ist_ stations in the placed netlist"""
    cells, drv, fan = g
    n = _n_stations(cells, bus)
    if not n:
        return None
    edges = []
    if out_bus:
        for s in _station_cells(cells, bus, 0):
            src = _back(cells, drv, s)
            if src is not None:
                edges.append(((cells[src][1], cells[src][2]), (cells[s][1], cells[s][2]), cells[src][3]))
    else:
        for s in _station_cells(cells, bus, n - 1):
            for c in _fwd(cells, fan, s):
                edges.append(((cells[c][1], cells[c][2]), (cells[s][1], cells[s][2]), cells[c][3]))
    inter = []                                   # placed station k -> station k+1 register edges (the chain between the pin-side hop and the far end)
    for k in range(n - 1):
        nxt = set(_station_cells(cells, bus, k + 1))
        for s in _station_cells(cells, bus, k):
            for c in _fwd(cells, fan, s):
                if c in nxt:
                    inter.append(man((cells[s][1], cells[s][2]), (cells[c][1], cells[c][2])))
    inter_max = round(max(inter), 1) if inter else 0.0
    if not edges:
        return dict(stations=n, n_edges=0, src_centroid=None, max_um=0.0, n_over=0, worst=[], inter_max_um=inter_max)
    hops = sorted(((man(a, b), nm) for a, b, nm in edges), reverse=True)
    return dict(stations=n, n_edges=len(edges), src_centroid=(round(sum(e[0][0] for e in edges) / len(edges), 1), round(sum(e[0][1] for e in edges) / len(edges), 1)),
                max_um=round(hops[0][0], 1), n_over=sum(1 for h, _ in hops if h > limit), worst=[(round(h, 1), nm) for h, nm in hops[:3]],
                inter_max_um=inter_max, inter_n_over=sum(1 for h in inter if h > limit))


def overrides(g, t, limit=LIMIT_UM):
    """{conn: dict(end='src'|'dst', xy=(x, y), chain=source_chain(...))} for every internal_stations bus of type t whose registers the placed geometry
    shows: an out bus (t['buses'][name]['dir'] == 'out') overrides the chain START, an in bus the chain END.  Buses without placed stations are absent
    (the checks then keep leaf_um / from_um / to_um)."""
    dirs = {b.get("name"): b.get("dir") for b in t.get("buses") or [] if isinstance(b, dict)}
    out = {}
    for e in t.get("internal_stations") or []:
        conn = str(e.get("conn", ""))
        bus = conn[4:] if conn.startswith("bus:") else conn
        d = dirs.get(bus)
        if d not in ("out", "in") or conn in out:
            continue
        r = source_chain(g, bus, d == "out", limit)
        if r and r["src_centroid"] is not None:
            out[conn] = dict(end="src" if d == "out" else "dst", xy=r["src_centroid"], chain=r)
    return out


if __name__ == "__main__":
    g = load(sys.argv[1])
    for bus in sys.argv[2:]:
        print(bus, source_chain(g, bus))
