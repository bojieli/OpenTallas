#!/usr/bin/env python3
"""PAD-REACH census (FABLE-FIX-KV-PV class D 11-19): do the landing pads of a bound partition type have the register
stages their in-bus -> hard-core-pin runs need?  Plan geometry + the bound kit RTL only (no bind, no placement).

    pad_reach_census.py PLAN.json TYPE BOUND.sv [--hop 300] [--min-spread 400] [--no-route] [--lift BUS_RE=N ..]
                        [--bus BUS_RE] [--json OUT]

BOUND.sv is the type's bound wrapper (kit work/rtl/<type>_part_bound.sv or bind rtl/): every hard-core input pin fed by
an in bus (`<bus>_q[j]` directly = pad 0, or through `ot_dp_dly[_keep] u_pd..` landing pads: shared pad, or tail-split
trunk + per-core copy) is grouped per (bus bit, pad) exactly like bind.py's tail split, and priced with
bind_pad_tail_split.reach() (the rule the bind applies with land_pad_tail_split.route / require_reach):

    split pad (>= 2 cores, spread > min-spread)   need = ceil(|src - T| / hop) + ceil(R / hop)
    shared pad                                    need = ceil(|src - farthest pin| / hop) - 1
    src = plan relay_sites u_bin_<bus>.q[..], else the centre of clock.landing_contract.bands.<bus>

Per bus: pads (groups), smallest pad, largest need, the stages short, the PLANNED worst hop (even stages: trunk
|src - T| / D with D = pad - K, copy R / K, shared run / (pad + 1)) and the pad flops (per-core copies / shared stages).  --lift BUS_RE=N prices the bus with every pad
raised by N (what an R8 owner table lift or added lane cycles give); exit 1 when any (lifted) pad is still short."""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_pad_tail_split as TS  # noqa: E402

INST = re.compile(r"^\s{4}(\w+) (?:#\(.*\) )?(u_\w+) \($")
PORT = re.compile(r"^\s+\.(\w+)\((.*)\),?\s*$")
DLY = re.compile(r"^\s+ot_dp_dly(?:_keep)? #\(\.W\((\d+)\), \.D\((\d+)\)\) (u_\w+) \(\.clk\(\w+\), \.d\((.+?)\), \.q\((.+?)\)\);")
TOK = re.compile(r"^(\w+)(?:\[(\d+)(?::(\d+))?\])?$")


def bits_of(expr):
    """[(name, bit | None)] MSB first, or None for an expression this parser does not read"""
    expr = expr.strip()
    toks = [x.strip() for x in expr[1:-1].split(",")] if expr.startswith("{") and expr.endswith("}") else [expr]
    out = []
    for t in toks:
        m = TOK.match(t)
        if not m:
            return None
        if m.group(3) is not None:
            hi, lo = int(m.group(2)), int(m.group(3))
            out += [(m.group(1), b) for b in (range(hi, lo - 1, -1) if hi >= lo else range(hi, lo + 1))]
        else:
            out.append((m.group(1), int(m.group(2)) if m.group(2) is not None else None))
    return out


def parse(sv, cores):
    """({wire: (D, source expr)}, {bus: lane pad}, {core rtl inst: {port: [(name, bit) MSB first]}})"""
    dly, lpad, conns = {}, {}, {}
    cur = None
    for ln in sv.splitlines():
        m = DLY.match(ln)
        if m:
            w, d, inst, src, q = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4), m.group(5)
            if inst.startswith("u_lpad_"):
                lpad[inst[len("u_lpad_"):]] = d
            elif w == 1 and TOK.match(q):
                dly[q] = (d, src)
            continue
        m = INST.match(ln)
        if m:
            cur = m.group(2) if m.group(2) in cores else None
            if cur:
                conns[cur] = {}
            continue
        if cur:
            if ln.startswith("    );"):
                cur = None
                continue
            m = PORT.match(ln)
            if m:
                b = bits_of(m.group(2))
                if b is not None:
                    conns[cur][m.group(1)] = b
    return dly, lpad, conns


def resolve(name, bit, dly, buses):
    """(bus, bit, landing pad) of a pin net fed by an in bus through landing pads only, else None"""
    pad = 0
    for _ in range(64):         # TRUNK-CHAIN: trunk -> trunk -> copy chains
        if name.endswith("_q") and name[:-2] in buses and bit is not None:
            return name[:-2], bit, pad
        if name not in dly:
            return None
        d, src = dly[name]
        pad += d
        b = bits_of(src)
        if not b or len(b) != 1:
            return None
        name, bit = b[0]
    return None


def census(plan, tn, sv, cfg, lifts=(), bus_re=None, plan_dir=None):
    t = plan["partition_types"][tn]
    hcs = t.get("hard_cores") or []
    rtl_of = {(h.get("physical_inst") or "u_bound.u_" + h["inst"]).split(".")[-1]: h["inst"] for h in hcs}
    tab = TS.pin_table(hcs, plan_dir)
    boxes = TS.core_boxes(hcs) if cfg["route"] else None
    buses = {b["name"] for b in t["buses"] if b["dir"] == "in"} | {f"ft{i}_i" for i in range(64)}
    dly, lpad, conns = parse(sv, rtl_of)
    groups = defaultdict(lambda: defaultdict(list))            # (bus, bit, pad) -> core -> [xy]
    nopin = 0
    for ri, ports in conns.items():
        inst = rtl_of[ri]
        for pn, bl in ports.items():
            pins = tab.get(inst, {}).get(pn)
            if pins is None:
                continue
            n = len(bl)
            for pos, (name, bit) in enumerate(bl):
                r = resolve(name, bit, dly, buses)
                if r is None or (bus_re and not re.search(bus_re, r[0])):
                    continue
                xy = pins.get(str(n - 1 - pos), pins.get("") if n == 1 else None)
                if xy is None:
                    nopin += 1
                    continue
                groups[r][inst].append(xy)
    out, worst = {}, dict(hop_um=0.0, short=0)
    for (bus, bit, pad), by in sorted(groups.items()):
        lift = max([n for rx, n in lifts if re.search(rx, bus)], default=0)
        have = pad + lpad.get(bus, 0) + lift
        src = TS.src_xy(t, bus)
        rr = TS.reach(have, by, cfg, src, boxes)
        pts = [xy for v in by.values() for xy in v]
        if rr["split"]:
            tc = TS.push_out(TS.l1_centre(pts), boxes) if boxes else TS.l1_centre(pts)
            run = max(TS.spread(pts) / 2.0, max((TS.route_len(tc, q, boxes)[0] for q in set(pts)), default=0.0) if boxes else 0.0)
            k = max(1, min(have, rr["tail"])) if have else 0
            d = have - k
            st = 0.0 if src is None else TS.md(src, tc)
            if k == 0:
                hop = st + run
            elif d == 0:
                hop = max(st + run / k, run / k)
            else:
                hop = max(st / d, run / k)
            cf, tf = len(by) * k, d
        else:
            hop = 0.0 if src is None else max(TS.md(src, q) for q in pts) / (have + 1)
            cf, tf = 0, have
        e = out.setdefault(bus, dict(pads=0, split=0, pins=0, cores=set(), lift=lift, lane_pad=lpad.get(bus, 0), src=src,
                                     min_pad=have, max_pad=have, need=0, short=0, short_pads=0, max_hop_um=0.0,
                                     copy_flops=0, shared_flops=0))
        e["pads"] += 1
        e["copy_flops"] += cf
        e["shared_flops"] += tf
        e["split"] += 1 if rr["split"] else 0
        e["pins"] += len(pts)
        e["cores"] |= set(by)
        e["min_pad"], e["max_pad"] = min(e["min_pad"], have), max(e["max_pad"], have)
        e["need"] = max(e["need"], rr["need"])
        e["short"] = max(e["short"], rr["short"])
        e["short_pads"] += 1 if rr["short"] else 0
        e["max_hop_um"] = max(e["max_hop_um"], round(hop, 1))
        e.setdefault("worst", None)
        if e["worst"] is None or rr["short"] > e["worst"]["short"] or (rr["short"] == e["worst"]["short"] and hop > e["worst"]["hop_um"]):
            e["worst"] = dict(bit=bit, pad=have, cores=len(by), hop_um=round(hop, 1), **rr)
    for e in out.values():
        e["cores"] = len(e["cores"])
        worst["hop_um"] = max(worst["hop_um"], e["max_hop_um"])
        worst["short"] = max(worst["short"], e["short"])
    return dict(type=tn, hop_um=cfg["hop_um"], min_spread_um=cfg["min_spread_um"], route=cfg["route"], pins_without_plan_xy=nopin,
                copy_flops=sum(e["copy_flops"] for e in out.values()), shared_flops=sum(e["shared_flops"] for e in out.values()),
                max_hop_um=worst["hop_um"], max_short=worst["short"], buses=out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("sv")
    ap.add_argument("--hop", type=float, default=300.0)
    ap.add_argument("--min-spread", type=float, default=400.0)
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--lift", action="append", default=[], metavar="BUS_RE=N")
    ap.add_argument("--bus", help="only in buses matching this regex")
    ap.add_argument("--plan-dir", help="directory the plan's pins_file paths are relative to (default: the plan's)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    cfg = dict(hop_um=a.hop, min_spread_um=a.min_spread, route=not a.no_route)
    lifts = [(x.rsplit("=", 1)[0], int(x.rsplit("=", 1)[1])) for x in a.lift]
    rep = census(json.load(open(a.plan)), a.type, Path(a.sv).read_text(), cfg, lifts, a.bus,
                 Path(a.plan_dir) if a.plan_dir else Path(a.plan).resolve().parent)
    for bus, e in sorted(rep["buses"].items(), key=lambda kv: (-kv[1]["short"], -kv[1]["max_hop_um"])):
        print(f"OT_PAD_REACH {a.type} {bus}: pads {e['pads']} (split {e['split']}) cores {e['cores']} pad {e['min_pad']}..{e['max_pad']}"
              f" (lane pad {e['lane_pad']}, lift {e['lift']}) need {e['need']} short {e['short']} ({e['short_pads']} pads)"
              f" max planned hop {e['max_hop_um']:.0f} um")
    print(f"OT_PAD_REACH {a.type} hop {a.hop:g} um: max planned hop {rep['max_hop_um']:.0f} um, max short {rep['max_short']}"
          f", pad flops {rep['copy_flops']} in per-core copies + {rep['shared_flops']} shared"
          f" -> {'PASS' if not rep['max_short'] else 'SHORT'}")
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    return 1 if rep["max_short"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
