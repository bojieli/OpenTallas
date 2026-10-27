#!/usr/bin/env python3
"""Bottom-up LANDED fallback (IF.FALLBACK, OWNER 10-26 16:5x): per-region local clock trees + landed seams.

The fallback runs in parallel with the 12.7 master-plan path.  The die clock is split into REGIONS (the plan's
dataflow cuts, die_clock_mesh --region-spec); each region is one local tree with its own CPPR root.  A seam is
  landed   registered both sides, forwarded-clock hop, fixed static latency (+K cycles), no credits:
           * region : the two partitions sit in different clock regions (die_clock_mesh landed_crossings.json),
           * phy    : one side is a PHY partition (regional PHY registers; --land-type regex),
           * ctl    : a reset / start wavefront hop (dst bus arst_n / start_i; static offsets already, boot time only);
  related  everything else: a single-cycle pair under one region tree (12.4a TT setup / FF hold).
The classes are STRUCTURAL (region boxes, partition types, bus role), never chosen from slacks.

  fallback_land.py plan     PLAN --landed LC.json [--land-type RE] [--k K] --out FB.json [--lane-delta LD.json --lat LAT]
  fallback_land.py gate     FB.json --sta C=die_sta.json ... [--rel C=die_sta_related.json ...] --run-bhold-ps B
                            [--contract-ps W] --out GATE.json

gate: related seams keep their die_sta (flat, real netlists) min/max slacks.  A run whose stand-ins carry the
OT_BHOLD_<B> receiver contract is re-read at contract W by the exact constant shift W - B on the hold slack (the
contract is one constant delay per input bit in front of its face flop); when W != B the number is labelled
MODEL-SHIFT, when W == B it is the run itself.  Landed seams leave the single-cycle check: their die number is the
plan landing window check of die_sta_related (region-to-region clock damage vs window, --rel), their single-cycle
slacks are INFO.  Intra-partition pairs come from die_sta --intra-pairs (absent = NOT RUN, never PASS).
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CTL_BUSES = ("arst_n", "start_i")


def _regions(lc):
    return [(r["tag"], r["box_um"]) for r in lc["regions"]]


def part_regions(plan, lc):
    types = plan["partition_types"]
    T = {t["name"]: t for t in types} if isinstance(types, list) else types
    out = {}
    for p in plan["partitions"]:
        w, h = T[p["type"]]["outline_um"]
        x, y = p["origin_um"]
        cx, cy = x + w / 2.0, y + h / 2.0
        hit = [tag for tag, b in _regions(lc) if b[0] <= cx < b[2] and b[1] <= cy < b[3]]
        if len(hit) != 1:
            raise SystemExit(f"fallback_land: partition {p['name']} centre in {len(hit)} regions")
        out[p["name"]] = hit[0]
    return out


def seam_class(src, dst, bus, reg, ptype, land_type):
    if reg.get(src) is None or reg.get(dst) is None:
        return "io"
    if reg[src] != reg[dst]:
        return "region"
    if land_type and (re.search(land_type, ptype.get(src, "")) or re.search(land_type, ptype.get(dst, ""))):
        return "phy"
    if bus in CTL_BUSES:
        return "ctl"
    return "related"


def cmd_plan(a):
    plan = json.loads(Path(a.plan).read_text())
    lc = json.loads(Path(a.landed).read_text())
    reg = part_regions(plan, lc)
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    # every plan port is one physical hop; classify it
    lc_ports = {q["port"] for q in lc["ports"]}
    ports, lane_of = [], {}
    for lane in plan["lanes"]:
        for pid in lane["ports"]:
            lane_of[pid] = lane["id"]
    cnt, bits = Counter(), Counter()
    mism = []
    for pr in plan["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        c = seam_class(s, d, pr["dst"]["bus"], reg, ptype, a.land_type)
        if (c == "region") != (pr["id"] in lc_ports):
            mism.append(pr["id"])
        cnt[c] += 1
        bits[c] += int(pr["width"])
        if c in ("region", "phy"):
            ports.append(dict(port=pr["id"], lane=lane_of.get(pr["id"]), cls=c, src=s, dst=d, src_region=reg[s],
                              dst_region=reg[d], width=int(pr["width"]), added_cycles=a.k))
    lane_cross = Counter(p["lane"] for p in ports)
    fb = dict(schema="opentallas.die_plan.fallback_land.v1", plan=str(a.plan), landed_crossings=str(a.landed),
              die=plan.get("die"), regions=lc["regions"], k=a.k, land_type=a.land_type, ctl_buses=list(CTL_BUSES),
              part_region=reg, port_classes=dict(cnt), port_bits=dict(bits),
              landed_ports=ports, landed_lanes=dict(lane_cross),
              region_class_vs_clock_tool_mismatch=mism,
              note="ctl seams are generated reset/start wavefront hops (not plan ports): classified in gate from die_sta")
    if a.lane_delta:
        lat = json.loads(Path(a.lat).read_text())
        pmap = {p["id"]: p for p in plan["ports"]}
        ends = {}
        for lane in plan["lanes"]:
            x, y = pmap[lane["ports"][0]], pmap[lane["ports"][-1]]
            ends[lane["id"]] = (x["src"]["part"] + "." + x["src"]["bus"], y["dst"]["part"] + "." + y["dst"]["bus"])
        byend = defaultdict(list)
        for n, v in lat["lanes"].items():
            byend[(v["src"]["part"] + "." + v["src"]["bus"], v["dst"]["part"] + "." + v["dst"]["bus"])].append(n)
        rows = {n: dict(lane=n, src=v["src"]["part"] + "." + v["src"]["bus"], dst=v["dst"]["part"] + "." + v["dst"]["bus"],
                        width=v["width"], delta=0) for n, v in lat["lanes"].items()}
        miss = []
        for lid, c in lane_cross.items():
            hits = byend.get(ends.get(lid), [])
            if not hits:
                miss.append(lid)
            for h in hits:
                rows[h]["delta"] += a.k * c
        Path(a.lane_delta).write_text(json.dumps(dict(
            note=f"fallback landed seams: +{a.k} per landed hop (classes region+phy)", lanes=list(rows.values()),
            unmapped_landed_lanes=miss), indent=0) + "\n")
        fb["lane_delta"] = dict(file=str(a.lane_delta), unmapped=miss, lanes_with_delta=sum(1 for r in rows.values() if r["delta"]),
                                max_lane_delta=max(r["delta"] for r in rows.values()))
    Path(a.out).write_text(json.dumps(fb, indent=1) + "\n")
    print(f"fallback plan: ports {dict(cnt)} bits {dict(bits)} landed lanes {len(lane_cross)} "
          f"clock-tool region mismatch {len(mism)}")


def _kv(items):
    out = {}
    for s in items:
        c, f = s.split("=", 1)
        out[c] = json.loads(Path(f).read_text())
    return out


def cmd_gate(a):
    fb = json.loads(Path(a.fb).read_text())
    plan = json.loads(Path(fb["plan"]).read_text())
    reg = fb["part_region"]
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    W = a.contract_ps if a.contract_ps is not None else a.run_bhold_ps
    shift = W - a.run_bhold_ps
    label = "RUN" if shift == 0 else f"MODEL-SHIFT {shift:+.1f} ps (run carries OT_BHOLD {a.run_bhold_ps:g}, contract {W:g})"
    out = dict(schema="opentallas.die_plan.fallback_gate.v1", fallback=str(a.fb), contract_ps=W, run_bhold_ps=a.run_bhold_ps,
               hold_basis=label, corners={})
    for C, d in _kv(a.sta).items():
        seams = d["corners"][C]["seams"]
        agg = defaultdict(lambda: dict(seams=0, bits=0, setup_worst=None, hold_worst=None, setup_neg=0, hold_neg=0,
                                       hold_neg_bits=0, worst_setup_seam=None, worst_hold_seam=None))
        for k, v in seams.items():
            sd, bus = k.split("/", 1)
            s, t = sd.split("->")
            c = seam_class(s, t, bus, reg, ptype, fb.get("land_type"))
            g = agg[c]
            g["seams"] += 1
            mx, mn = v["max"], v["min"]
            g["bits"] += int(mn.get("paths", 0))
            hs = mn["worst"] + shift
            if g["setup_worst"] is None or mx["worst"] < g["setup_worst"]:
                g["setup_worst"], g["worst_setup_seam"] = mx["worst"], k
            if g["hold_worst"] is None or hs < g["hold_worst"]:
                g["hold_worst"], g["worst_hold_seam"] = round(hs, 3), k
            g["setup_neg"] += mx["worst"] < 0
            if hs < 0:
                g["hold_neg"] += 1
                g["hold_neg_bits"] += int(mn.get("neg", 0)) if shift == 0 else int(mn.get("paths", 0))
        intra = d["corners"][C].get("intra") or {}
        iw = [(v["min"].get("worst"), p) for p, v in intra.items() if v.get("min", {}).get("n")]
        isw = [(v["max"].get("worst"), p) for p, v in intra.items() if v.get("max", {}).get("n")]
        cc = dict(classes=dict(agg),
                  intra=dict(status="RUN" if iw else "NOT RUN (die_sta --intra-pairs 0)",
                             hold_worst=min(iw)[0] if iw else None, hold_worst_part=min(iw)[1] if iw else None,
                             setup_worst=min(isw)[0] if isw else None,
                             hold_neg_parts=sum(1 for x in iw if x[0] < 0)))
        out["corners"][C] = cc
    for C, r in _kv(a.rel or []).items():
        L = r["corners"][C]["classes"].get("landed", {}).get("plan_landing")
        out["corners"].setdefault(C, {})["landing_window"] = L
    tt, ff = out["corners"].get("TT", {}), out["corners"].get("FF", {})
    rel_tt = tt.get("classes", {}).get("related", {})
    rel_ff = ff.get("classes", {}).get("related", {})
    lw_ok = all((out["corners"].get(c, {}).get("landing_window") or {}).get("verdict") == "PASS" for c in ("TT", "FF"))
    intra_ok = all(out["corners"].get(c, {}).get("intra", {}).get("status") == "RUN" and
                   out["corners"][c]["intra"]["hold_worst"] is not None and out["corners"][c]["intra"]["hold_worst"] >= 0 for c in ("FF",))
    v = dict(related_setup_TT=rel_tt.get("setup_worst"), related_hold_FF=rel_ff.get("hold_worst"),
             related_hold_FF_neg_seams=rel_ff.get("hold_neg"), landing_window_TT_FF=lw_ok,
             intra_FF=ff.get("intra", {}).get("status"), intra_hold_FF=ff.get("intra", {}).get("hold_worst"))
    ok = lambda x: x is not None and x >= 0
    v["verdict"] = "PASS" if ok(v["related_setup_TT"]) and ok(v["related_hold_FF"]) and lw_ok and intra_ok else "FAIL"
    v["evidence"] = ("stand-in views (declared 12.3 budget): NOT freeze evidence until signed kit views replace them"
                     if a.standins else "views as given")
    if shift:
        v["evidence"] += "; hold at contract W is a MODEL-SHIFT of the run"
    out["verdict"] = v
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for C, cc in out["corners"].items():
        for k, g in sorted(cc.get("classes", {}).items()):
            print(f"{C} {k:8s} seams {g['seams']:5d} bits {g['bits']:7d} setup {g['setup_worst']} hold {g['hold_worst']} "
                  f"hold_neg {g['hold_neg']} worst_hold {g['worst_hold_seam']}")
        print(f"{C} intra {cc.get('intra')}  landing {cc.get('landing_window', {}) and {k: cc['landing_window'][k] for k in ('damage_max_ps', 'setup_margin_ps', 'verdict')}}")
    print("VERDICT", json.dumps(v))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("--landed", required=True, help="die_clock_mesh landed_crossings.json (regions + region ports)")
    p.add_argument("--land-type", default=r"^kv3_phy", help="partition types whose seams are landed (regional PHY regs)")
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--out", required=True)
    p.add_argument("--lane-delta")
    p.add_argument("--lat", help="lane latency table (lat_v39r qwen_kvsys_latency.json) for --lane-delta")
    g = sub.add_parser("gate")
    g.add_argument("fb")
    g.add_argument("--sta", action="append", required=True, help="CORNER=die_sta.json")
    g.add_argument("--rel", action="append", help="CORNER=die_sta_related.json (landing window)")
    g.add_argument("--run-bhold-ps", type=float, required=True, help="OT_BHOLD value the run's stand-ins carry")
    g.add_argument("--contract-ps", type=float, help="seam hold contract W (plan clock.seam_hold.seam_ps)")
    g.add_argument("--standins", action="store_true")
    g.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    (cmd_plan if a.cmd == "plan" else cmd_gate)(a)


if __name__ == "__main__":
    main()
