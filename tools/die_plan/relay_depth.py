#!/usr/bin/env python3
"""S81-COLGEN-3 11-17 (S81-TYPES-R3 col relay class): relay depth from the real route, so no relay hop exceeds the 405-um reach.

Problem: the polyline relay chains of the col frames (u_y_rt_*, x2, lpl ... = ot_s81_rly / dsfd_rly_* leaves between two hard
cores) carry the as-built stage count n while the route between the two core pins, round the hard macros, is longer than
(n + 1) x 405 um (relay_mid.tcl OT_RELAY_POLY WARN: col_h10_r0_p1 746, col_h9_r0_p2 670, p4/p5 593, p6 485, p3/p1 478,
h10_r2 446 um).  Hops above the reach stop later in CTS / route.

What this does, per plan type (read-only on the bound module and the plan; writes only the plan key):
  1. core_conns_from_bind.trace(): every wiring path core.port <- ... <- core.port through relays / seams / kept delays with its
     existing stage count (stages_existing) and the stage instances on it (via);
  2. the route length L between the two core PINS (bit-wise, the longest bit of the bundle): shortest 4-neighbour path on a
     GRID_UM grid round every hard core grown by PAD_UM (relay_mid: 6.5 um, the stations avoid the same halos);
  3. stations needed = ceil(L / LIMIT) - 1  (every one of the stations + 1 hops <= LIMIT); extra = needed - stages_existing;
  4. extra > 0 on a path with a relay: row {"inst": the relay leaf nearest the sink, "port": "o", "D": extra}; on a DIRECT
     core-to-core wire (nothing relay-like on it): row {"inst": sink leaf, "port": its input, "side": "sink", "bits": [lo, hi],
     "D": extra} (bind puts the stages in front of those sink bits) -> plan
     partition_types[T].relay_depth, realised by bind.py as D relay-named stages (u_y_xd_*) after that output, declared per sink
     bit in bind_core_input_pipe.json (bind_verify, compiler / TOK).  Several paths through one relay: the largest D.
Cycles are the owner's pre-approved cost (S81-TYPES-R3 / COORD 11-17).  A path whose nearest-sink stage is not a relay leaf
(only seams / kept delays on it) is listed as `unfixed` -- never silently dropped.
usage: relay_depth.py PLAN.json TYPE_RE BOUND_DIR [--repo REPO] [--limit 405] [--out-plan OUT.json] [--report REPORT.json]
       BOUND_DIR holds <TYPE>_bound.sv or <TYPE>.sv (a bind out/rtl).  Without --out-plan nothing is written.
       relay_depth.py merge PLAN.json OUT.json REPORT.json ...   (rows of several --report runs, e.g. one per family, into a plan)"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LIMIT = 405.0
GRID_UM = 4.0
PAD_UM = 6.5
RELAY_MOD = re.compile(r"^(ot_s81_rly|dsfd_rly_\d+_[A-Z]+)$")


def _pin_table(hc, plan_dir):
    """{port: {bit(str): (x, y)}} of one hard core in the type frame (origin + track offset + orient), None without pins"""
    import check as C
    if not (hc.get("pins") or hc.get("pins_file")):
        return None
    raw = C.core_pins(hc, plan_dir)
    tab = defaultdict(dict)
    cw, ch = hc["outline_um"]
    o = hc.get("orient", "R0")
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    for nm, _ln, x, y in raw:
        pn, _, bit = nm.partition("[")
        tx, ty = C._orient_pt(o, cw, ch, x, y)
        tab[pn][bit.rstrip("]") or "0"] = (hc["origin_um"][0] + dx + tx, hc["origin_um"][1] + dy + ty)
    return tab


class Router:
    """4-neighbour A* on a uniform grid round the hard cores of one type"""

    def __init__(self, t, grid=GRID_UM, pad=PAD_UM):
        import numpy as np
        self.np = np
        self.g = grid
        w, h = t["outline_um"]
        self.nx, self.ny = int(math.ceil(w / grid)) + 1, int(math.ceil(h / grid)) + 1
        self.blk = np.zeros((self.nx, self.ny), dtype=bool)
        for hc in t.get("hard_cores", []):
            if "origin_um" not in hc or "outline_um" not in hc:
                continue
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            x0, y0 = hc["origin_um"][0] + dx - pad, hc["origin_um"][1] + dy - pad
            x1, y1 = x0 + hc["outline_um"][0] + 2 * pad, y0 + hc["outline_um"][1] + 2 * pad
            self.blk[max(0, int(x0 // grid)):min(self.nx, int(x1 // grid) + 1),
                     max(0, int(y0 // grid)):min(self.ny, int(y1 // grid) + 1)] = True
        self.cache = {}

    def length(self, a, b):
        """route length (um) a -> b, +inf when closed"""
        key = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
        if key not in self.cache:
            self.cache[key] = self._astar(a, b)
        return self.cache[key]

    def _astar(self, a, b):
        import heapq
        g = self.g
        r = int(math.ceil(12.0 / g))            # a pin sits on a core edge: free the halo round the end points
        blk = self.blk.copy()

        def cell(p):
            return min(self.nx - 1, max(0, int(p[0] // g))), min(self.ny - 1, max(0, int(p[1] // g)))
        s, e = cell(a), cell(b)
        for cx, cy in (s, e):
            blk[max(0, cx - r):cx + r + 1, max(0, cy - r):cy + r + 1] = False
        best = {s: 0.0}
        pq = [(abs(s[0] - e[0]) + abs(s[1] - e[1]), 0.0, s)]
        while pq:
            _f, d, n = heapq.heappop(pq)
            if n == e:
                return d * g
            if d > best.get(n, 1e18):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (n[0] + dx, n[1] + dy)
                if not (0 <= m[0] < self.nx and 0 <= m[1] < self.ny) or blk[m]:
                    continue
                nd = d + 1
                if nd < best.get(m, 1e18):
                    best[m] = nd
                    heapq.heappush(pq, (nd + abs(m[0] - e[0]) + abs(m[1] - e[1]), nd, m))
        return float("inf")


def type_rows(plan, tn, text, repo=None, plan_dir=None, limit=LIMIT):
    """-> (relay_depth rows, report dict) for one type"""
    import core_conns_from_bind as CC
    t = plan["partition_types"][tn]
    res = CC.trace(plan, tn, text, repo)
    hcs = {h["inst"]: h for h in t.get("hard_cores", [])}
    pins = {}
    router = Router(t)
    # one candidate per (partner pair, via): the longest bit
    rows, unfixed, seen, direct = {}, [], 0, {}
    for p in res["paths"]:
        if p["dir"] != "in" or "partner" not in p:
            continue
        src_core, _, src_port = p["partner"].rpartition(".")
        if src_core not in hcs or p["core"] not in hcs:
            continue
        # relay_mid.tcl measures centroid(source pins) -> centroid(sink pins): the same here.  The row names the sink bit
        # ranges only, the source port is taken whole (its centroid)
        sp = pins.get(("tab", src_core))
        if sp is None:
            sp = pins.setdefault(("tab", src_core), _pin_table(hcs[src_core], plan_dir))
        sk = pins.get(("tab", p["core"]))
        if sk is None:
            sk = pins.setdefault(("tab", p["core"]), _pin_table(hcs[p["core"]], plan_dir))
        if not sp or not sk or src_port not in sp or p["port"] not in sk:
            continue
        spts = list(sp[src_port].values())
        kpts = [sk[p["port"]][str(bit)] for lo, hi in p["bit_ranges"] for bit in range(lo, hi + 1) if str(bit) in sk[p["port"]]]
        if not spts or not kpts:
            continue
        a = (sum(x for x, _ in spts) / len(spts), sum(y for _, y in spts) / len(spts))
        b = (sum(x for x, _ in kpts) / len(kpts), sum(y for _, y in kpts) / len(kpts))
        worst, wbits = router.length(a, b), 1
        if not wbits:
            continue
        seen += 1
        need = max(0, math.ceil(worst / limit) - 1) if worst != float("inf") else 0
        extra = need - int(p["stages_existing"])
        if extra <= 0:
            continue
        relay = [v for v in p["via"] if _is_relay_inst(text, v)]
        if not relay:
            # a DIRECT core-to-core wire (nothing relay-like on it): stages in front of the sink input bits (side "sink"),
            # placed between the two pins by relay_mid.tcl like a relay chain
            rel = p["core"].split(".", 1)[1] if "." in p["core"] else p["core"]
            if not re.search(r"\n\s*\w+\s*(?:#\([^;]*?\))?\s*u_" + re.escape(re.sub(r"[^A-Za-z0-9_]", "_", rel)) + r"\s*\(", text):
                unfixed.append(dict(core=p["core"], port=p["port"], partner=p["partner"], path_um=round(worst, 1),
                                    extra=extra, reason="sink is not a bound leaf of this type (sub-core): no row"))
                continue
            for lo, hi in p["bit_ranges"]:
                for bit in range(lo, hi + 1):
                    cur = direct.setdefault((rel, p["port"]), {})
                    if extra > cur.get(bit, (0, 0))[0]:
                        cur[bit] = (extra, round(worst, 1))
            continue
        rel = relay[0][2:] if relay[0].startswith("u_") else relay[0]       # via[0] = nearest the sink
        key = (rel, "o")
        r = rows.setdefault(key, dict(inst=rel, port="o", D=0, path_um=0.0, stages_existing=int(p["stages_existing"])))
        if extra > r["D"]:
            r.update(D=extra, path_um=round(worst, 1), stages_existing=int(p["stages_existing"]))
    out = sorted(rows.values(), key=lambda r: r["inst"])
    for (rel, port), per in sorted(direct.items()):
        runs, bits = [], sorted(per)
        for b in bits:
            d, L = per[b]
            if runs and runs[-1]["bits"][1] == b - 1 and runs[-1]["D"] == d:
                runs[-1]["bits"][1] = b
                runs[-1]["path_um"] = max(runs[-1]["path_um"], L)
            else:
                runs.append(dict(inst=rel, port=port, side="sink", bits=[b, b], D=d, path_um=L, stages_existing=0))
        out += runs
    for r in out:
        if r["D"] > 4:
            unfixed.append(dict(inst=r["inst"], reason=f"D={r['D']} > 4 (schema max)", path_um=r["path_um"]))
            r["D"] = 4
    return out, dict(type=tn, paths_measured=seen, rows=len(out), extra_cycles=sum(r["D"] for r in out), unfixed=unfixed,
                     inf_routes=sum(1 for v in router.cache.values() if v == float("inf")))


def _is_relay_inst(text, inst):
    m = re.search(r"\n\s*(\w+)\s*(?:#\([^;]*?\))?\s*" + re.escape(inst) + r"\s*\(", text)
    return bool(m and RELAY_MOD.match(m.group(1)))


def apply_reports(plan, reports):
    """merge the rows_data of one or more --report files into plan (partition_types[T].relay_depth); returns rows written"""
    n = 0
    for rep in reports:
        for r in rep:
            if r.get("rows_data"):
                plan["partition_types"][r["type"]]["relay_depth"] = [dict(x) for x in r["rows_data"]]
                n += len(r["rows_data"])
    return n


def main(argv):
    if len(argv) > 1 and argv[1] == "merge":          # relay_depth.py merge PLAN.json OUT.json REPORT.json [REPORT.json ...]
        plan = json.loads(Path(argv[2]).read_text())
        n = apply_reports(plan, [json.loads(Path(f).read_text()) for f in argv[4:]])
        Path(argv[3]).write_text(json.dumps(plan, indent=1))
        print(f"relay_depth merge: {n} rows into {argv[3]}")
        return 0
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("type_re")
    ap.add_argument("bound_dir")
    ap.add_argument("--repo")
    ap.add_argument("--plan-dir", help="directory the plan's pins_file / lef paths are relative to (default: the plan's)")
    ap.add_argument("--limit", type=float, default=LIMIT)
    ap.add_argument("--out-plan")
    ap.add_argument("--report")
    a = ap.parse_args(argv[1:])
    plan = json.loads(Path(a.plan).read_text())
    plan_dir = Path(a.plan_dir or Path(a.plan).resolve().parent)
    reports, cache = [], {}
    for tn in sorted(plan["partition_types"]):
        if not re.search(a.type_re, tn):
            continue
        f = next((q for q in (Path(a.bound_dir) / f"{tn}_bound.sv", Path(a.bound_dir) / f"{tn}.sv") if q.is_file()),
                 Path(a.bound_dir) / f"{tn}.sv")
        if not f.is_file():
            reports.append(dict(type=tn, error="no bound module " + str(f)))
            continue
        t = plan["partition_types"][tn]
        # identical geometry + identical bound text -> identical rows (pv variants of one cl)
        geo = json.dumps([[h["inst"], h.get("origin_um"), h.get("orient"), h.get("module")] for h in t.get("hard_cores", [])]) + \
            str(hash(f.read_text()))
        if geo in cache:
            rows, rep = cache[geo]
            rep = dict(rep, type=tn, reused=True)
        else:
            rows, rep = type_rows(plan, tn, f.read_text(), a.repo, plan_dir, a.limit)
            cache[geo] = (rows, rep)
        if a.out_plan and rows:
            t["relay_depth"] = [dict(r) for r in rows]
        reports.append(dict(rep, rows_data=rows))
    if a.out_plan:
        Path(a.out_plan).write_text(json.dumps(plan, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(reports, indent=1))
    for r in reports:
        if "error" in r:
            print(f"{r['type']}: {r['error']}")
        else:
            print(f"{r['type']}: {r['rows']} relay rows, +{r['extra_cycles']} stages, {r['paths_measured']} paths measured, "
                  f"unfixed {len(r['unfixed'])}{' (reused)' if r.get('reused') else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
