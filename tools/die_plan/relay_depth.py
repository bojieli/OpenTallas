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
FABLE-FIX-S81-BANKLEAF 11-18: (a) the leaf name of a row is the bound instance name (bind rel_of), with or without the content
instance (u_r0_u_cf / u_cf) -- macro-to-macro wires of the r0 bank leaves get sink rows like every other direct wire;
(b) a DIRECT core-to-core wire is measured as the flight between the pin centroids (the wire crosses the cores above
their obs_max; report key flight_measured lists every one whose round-the-halo length is over the reach); (c) sequencer <-> cfg
ROM read loops (fixed latency inside ot_s81_cfg7_seq) never get a row: report key read_loops, over the reach = `unfixed`
(core placement); (d) the direct sinks of the lane FIFO's xa / xb / x2 / cc carry ONE depth (report key aligned_groups), so
payload and control stay on the same edge.  Relay chains are unchanged (polyline round the halos, as relay_mid.tcl places them).
usage: relay_depth.py PLAN.json TYPE_RE BOUND_DIR [--repo REPO] [--limit 405] [--out-plan OUT.json] [--report REPORT.json]
       BOUND_DIR holds <TYPE>_bound.sv or <TYPE>.sv (a bind out/rtl).  Without --out-plan nothing is written.
       relay_depth.py merge PLAN.json OUT.json REPORT.json ... [--equalise]   (rows of several --report runs, e.g. one per
       family, into a plan; --equalise = one row set per content module, the largest D; a measured type with no row loses its rows)"""
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
# a fixed-latency read loop: (source module, source port) -> (sink module, sink port); never pipelined by a row
READ_LOOP = ((re.compile(r"^ot_s81_cfg7_seq"), re.compile(r"^(a|ce\d+)$"), re.compile(r"^ot_rom_"), re.compile(r"^(addr_in|ce_in)$")),
             (re.compile(r"^ot_rom_"), re.compile(r"^rd_out$"), re.compile(r"^ot_s81_cfg7_seq"), re.compile(r"^q\d+$")))


# aligned source groups: (source module, ports whose direct sinks must carry one common depth)
ALIGN_GROUP = ((re.compile(r"^dsfd_cfifo_crs"), re.compile(r"^(xa|xb|x2|cc)$")),)


def _align_group(src_mod, src_port):
    return any(a.search(src_mod) and b.search(src_port) for a, b in ALIGN_GROUP)


def _is_read_loop(src_mod, src_port, sink_mod, sink_port):
    return any(a.search(src_mod) and b.search(src_port) and c.search(sink_mod) and d.search(sink_port) for a, b, c, d in READ_LOOP)
RELAY_MOD = re.compile(r"^(ot_s81_rly|dsfd_rly_\d+_[A-Z]+)$")
TRANSPORT_MOD = re.compile(r"^(ot_dp_dly|ot_dp_dly_keep)$")


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
    rows, unfixed, seen, direct, srcdirect = {}, [], 0, {}, {}
    leaf_cache, loops, flight, agroup, aligned = {}, [], [], defaultdict(list), []

    def leaf_rel(core):
        """bound leaf name (bind rel_of: the instance of the type module minus its u_) of hard core `core`, None when the core
        is not an instance of the type module.  FABLE-FIX-S81-BANKLEAF 11-18: bind keeps the content instance in the leaf name
        of some types (col_h9_r0_p1/p2/p4/p5, col_h10_r0_p1/p4: u_u_r0_u_cf) and drops it in others (the _nx contents of
        col_h9_r0_p3/p6, r1, r2: u_u_cf).  Only the dropped form was tried, so every DIRECT macro-to-macro wire of the first
        group (515 paths, 440..1740 um) was reported `unfixed` as a sub-core although both ends are leaves with a port."""
        if core not in leaf_cache:
            cands = [core] + ([core.split(".", 1)[1]] if "." in core else [])
            hit = None
            for c_ in cands:
                n_ = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", c_)).strip("_")
                if re.search(r"\n\s*\w+\s*(?:#\([^;]*?\))?\s*u_" + re.escape(n_) + r"\s*\(", text):
                    hit = n_
                    break
            leaf_cache[core] = hit
        return leaf_cache[core]
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
        relay = [v for v in p["via"] if _is_relay_inst(text, v)]
        seen += 1
        if relay:
            # a relay chain: its stations are cells, relay_mid.tcl spreads them along the polyline round the core halos
            worst = router.length(a, b)
        else:
            # FABLE-FIX-S81-BANKLEAF 11-18, a DIRECT core-to-core wire: no cell on it, and every col hard core stops below
            # the routing top (obs_max M4..M6, MAX_ROUTING_LAYER M8), so the wire crosses the cores: its length is the flight
            # (Manhattan) between the pin centroids, not the path round the 6.5-um station halos (which closes the 22-um gaps
            # between the ROMs on the 4-um grid: u_s2.a -> u_c2_5.addr_in 408 um round, 254 um flight; u_e4.st -> u_t2.nf
            # 1736 um round, 227 um flight).  The round-the-halo length stays in the report (padded_um) for audit.
            worst = abs(a[0] - b[0]) + abs(a[1] - b[1])
            padded = router.length(a, b)
            loop = _is_read_loop(hcs[src_core].get("module", ""), src_port, hcs[p["core"]].get("module", ""), p["port"])
            if _align_group(hcs[src_core].get("module", ""), src_port) and leaf_rel(p["core"]) is not None:
                agroup[src_core].append((leaf_rel(p["core"]), p["port"], p["bit_ranges"], round(worst, 1)))
            if loop or padded > limit:
                (loops if loop else flight).append(dict(
                    core=p["core"], port=p["port"], partner=p["partner"], path_um=round(worst, 1),
                    padded_um=None if padded == float("inf") else round(padded, 1)))
            if loop:
                # a sequencer <-> cfg ROM read loop has a FIXED latency inside the sequencer (ot_s81_cfg7_seq: a / ce out
                # flop -> ROM -> q in flop, capture DL edges later, bank select registered with the read): a stage on one
                # ROM's address, enable or data makes the sequencer capture the wrong word (tb_ot_s81_cfg7_seq + one stage
                # on ROM 5 / 6: FAIL).  Never a row; over the reach = a core placement item, listed as unfixed.
                if worst > limit:
                    unfixed.append(dict(core=p["core"], port=p["port"], partner=p["partner"], path_um=round(worst, 1), extra=0,
                                        reason="fixed-latency ROM read loop over the reach: move the sequencer / ROM "
                                               "(core placement), a pipeline stage here is a functional error"))
                continue
        need = max(0, math.ceil(worst / limit) - 1) if worst != float("inf") else 0
        extra = need - int(p["stages_existing"])
        if extra <= 0:
            continue
        if not relay:
            # a DIRECT core-to-core wire (nothing relay-like on it): stages in front of the sink input bits (side "sink"),
            # placed between the two pins by relay_mid.tcl like a relay chain
            rel = leaf_rel(p["core"])
            if rel is None:
                # the sink is a macro inside a bigger bound leaf (r0 ROM banks): no sink port to delay.  Delay the SOURCE leaf's
                # output port instead (every internal sink of that port gets the same D: a bank's ROMs stay aligned)
                srel = leaf_rel(src_core)
                if srel is not None:
                    cur = srcdirect.setdefault((srel, src_port), dict(D=0, path_um=0.0))
                    if extra > cur["D"]:
                        cur.update(D=extra, path_um=round(worst, 1))
                    continue
                unfixed.append(dict(core=p["core"], port=p["port"], partner=p["partner"], path_um=round(worst, 1),
                                    extra=extra, reason="neither end is a bound leaf of this type (sub-cores): no row; "
                                    "fix in the leaf: tools/s81_dv/frame_colrelay_depth.py form or core placement"))
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
    # FABLE-FIX-S81-BANKLEAF 11-18, aligned source groups: the lane FIFO hands the frame its payload (xa, xb, x2) and the
    # control word (cc) of the SAME edge; a stage on one of them alone shifts payload against control for every consumer
    # behind.  When any link of the group needs D stages, every link of the group gets D: the frame sees one stream D edges
    # later (the same as a D-deeper landing), aligned as built.
    for src_core, links in sorted(agroup.items()):
        dmax = max((d for rel, port, _br, _l in links for d, _ in direct.get((rel, port), {}).values()), default=0)
        if not dmax:
            continue
        for rel, port, br, L in links:
            cur = direct.setdefault((rel, port), {})
            for lo, hi in br:
                for bit in range(lo, hi + 1):
                    if cur.get(bit, (0, 0))[0] < dmax:
                        cur[bit] = (dmax, L)
            aligned.append(dict(source=src_core, sink=rel, port=port, D=dmax, path_um=L))
    out = sorted(rows.values(), key=lambda r: r["inst"])
    for (rel, port), v in sorted(srcdirect.items()):
        out.append(dict(inst=rel, port=port, side="source", D=v["D"], path_um=v["path_um"], stages_existing=0))
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
                     read_loops=loops, flight_measured=flight, aligned_groups=aligned,
                     inf_routes=sum(1 for v in router.cache.values() if v == float("inf")))


def _is_relay_inst(text, inst):
    m = re.search(r"\n\s*(\w+)\s*(?:#\([^;]*?\))?\s*" + re.escape(inst) + r"\s*\(", text)
    # CBC-RULES-1119 (COORD 11-19): the generic transport stages (ot_dp_dly / ot_dp_dly_keep, QC / KV / HEAD) are relay cells
    # too: a path through one is a relay chain, measured round the core halos like an S81 relay
    return bool(m and (RELAY_MOD.match(m.group(1)) or TRANSPORT_MOD.match(m.group(1))))


def apply_reports(plan, reports, equalise=False):
    """merge the rows_data of one or more --report files into plan (partition_types[T].relay_depth); returns rows written.
    equalise (FABLE-FIX-S81-BANKLEAF 11-18): every type that binds the same content module (col_h9_l4_lp_r0: p1/p2/p4/p5) gets
    the union of that module's rows at the largest D, so all frames of one master carry ONE depth per link and one compiler
    frame schedule covers them (tools/s81_dv/frame_schedule_asb.py refuses depths that differ between frame instances); a stage
    on the shorter copy of a link is only a flop.  Types without rows in the reports are left alone unless their module has rows."""
    n = 0
    pt = plan["partition_types"]
    per = {r["type"]: [dict(x) for x in r["rows_data"]] for rep in reports for r in rep if "rows_data" in r}
    if equalise:
        def mod(tn):
            c = pt[tn].get("contents") or []
            return c[0].get("module") if len(c) == 1 else None
        groups = defaultdict(dict)
        for tn, rows in per.items():
            for x in rows:
                k = (x["inst"], x["port"], x.get("side", "relay"), tuple(x.get("bits") or ()))
                cur = groups[mod(tn) or tn].setdefault(k, dict(x))
                if x["D"] > cur["D"] or (x["D"] == cur["D"] and x.get("path_um", 0) > cur.get("path_um", 0)):
                    cur.update(x)
        for g, rows in groups.items():
            runs = defaultdict(list)
            for (inst, port, side, bits) in rows:
                if side == "sink" and bits:
                    runs[(inst, port)].append(bits)
            for k, v in runs.items():
                v.sort()
                if any(a[1] >= b[0] for a, b in zip(v, v[1:])):
                    raise ValueError(f"equalise {g}: sink bit runs of {k[0]}.{k[1]} differ between types: {v}")
        for tn in list(per):
            g = mod(tn) or tn
            per[tn] = [dict(x) for _k, x in sorted(groups[g].items(), key=lambda kv: (kv[0][2] != "relay", kv[0]))]
    for tn, rows in per.items():
        if rows:
            pt[tn]["relay_depth"] = rows
            n += len(rows)
        elif "relay_depth" in pt[tn]:
            del pt[tn]["relay_depth"]             # a type the report measured clean must not keep stale rows
    return n


def main(argv):
    if len(argv) > 1 and argv[1] == "merge":          # relay_depth.py merge PLAN.json OUT.json REPORT.json [REPORT.json ...]
        plan = json.loads(Path(argv[2]).read_text())
        eq = "--equalise" in argv
        n = apply_reports(plan, [json.loads(Path(f).read_text()) for f in argv[4:] if f != "--equalise"], eq)
        Path(argv[3]).write_text(json.dumps(plan, indent=1))
        print(f"relay_depth merge: {n} rows into {argv[3]}{' (equalised per content module)' if eq else ''}")
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
