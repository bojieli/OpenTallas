#!/usr/bin/env python3
"""KV-TYPES-5 11-08 PHY RE-FORM plan event (COORD 10:0x: kv3_phy@7R TT -145 at GRT, macro u_bound.u_core clk->q 218 ps
+ about 650 ps of wire to the far E-face register u_bout_o_phy_Q__sN_piN_d3/q[35]; next arst_n -> u_bin_i_host_hbm_rst_n
recovery -64 ps.  A design class: no retry.  OWNER 11-03/11-07: pin cycles are a lever).

(1) PI payload, kv3_phy AND kv3_phy_v1.  The macro's four 289-bit pi words leave on SIX out buses (fhN = pi0[11:0],
    piN = pi0[288:12]+pi1[3:0], d1 = pi1[288:4], d2 = pi2[284:0], d3 = pi2[288:285]+pi3[276:0], rhN = pi3[288:277]), so
    one word spans two lanes and all six get the SAME depth (relative lane timing unchanged).  Each bus gets 3 native
    source stations (tools/die_plan/native_istations.py, realised by kit_istations before u_bout_<bus>): stage 0 FIRM
    GAP um east of the macro E edge on the bus's own pin rows (the register at the macro output), stages 1-2 evenly on
    the straight line to the E-face window.  Every hop (worst bit) is checked <= reach * 0.98.  Lanes fixed_cycles
    0 -> 3 (+3 pin cycles; native_istations invariant fixed = source + destination stations, the pc receivers carry no
    entry on these buses so their pad stays 0).  The types are added to asbuilt.internal_stations_types.
(2) host reset, kv3_phy only.  reset.port_relays hrst (tools/die_plan/reset_port_relays.py): 2 ot_dp_rrelay stages from
    rst_n (= arst_n at reset.tap_um) to u_bin_i_host_hbm_rst_n.rst_n, FIRM via relay_sites u_prl_hrst_<j>/q on the L
    tap -> sink, and the sink's epoch flop (eq) FIRM at its q site so the last hop is bounded too.

Every key outside partition_types[kv3_phy|kv3_phy_v1].{internal_stations,reset,relay_sites} and
lanes[these lanes].fixed_cycles is asserted identical; the output validates against the schema.

usage: phy_pi_reform.py BASE_PLAN OUT_PLAN --lef MACRO.lef --bound kv3_phy=RTL --bound kv3_phy_v1=RTL
                        --asbuilt IN.json --asbuilt-out OUT.json [--report R.json]
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

REACH = 405.0
STEP = REACH * 0.98
GAP = 24.0            # stage 0: um east of the macro E edge (the halo is 3 um; clock islands start at x >= 325)
DEPTH = 3
TYPES = ("kv3_phy", "kv3_phy_v1")
BUSES = ("o_phy_Q__sN_fhN", "o_phy_Q__sN_piN", "o_phy_Q__sN_piN_d1", "o_phy_Q__sN_piN_d2", "o_phy_Q__sN_piN_d3",
         "o_phy_Q__sN_rhN")
HOST_SINK = "u_bin_i_host_hbm_rst_n"


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def r3(p):
    return [round(float(p[0]), 3), round(float(p[1]), 3)]


def lef_pins(path):
    """{(word, bit): (x, y)} macro-frame centre of the first RECT of each pi pin"""
    txt = Path(path).read_text()
    out = {}
    for m in re.finditer(r"PIN (pi\d)\[(\d+)\](.*?)END \1\[\2\]", txt, re.S):
        r = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", m[3])
        out[(m[1], int(m[2]))] = ((float(r[1]) + float(r[3])) / 2, (float(r[2]) + float(r[4])) / 2)
    return out


def bout_sources(rtl, bus):
    """[(word, bit)] of the u_bout_<bus> .d concatenation (w_core_piN[msb:lsb] terms)"""
    m = re.search(rf"\bu_bout_{re.escape(bus)}\s*\(.*?\.d\(([^)]*)\)", rtl)
    if not m:
        raise SystemExit(f"no u_bout_{bus} in the bound RTL")
    bits = []
    for t in re.finditer(r"w_core_(pi\d)\[(\d+):(\d+)\]", m[1]):
        bits += [(t[1], b) for b in range(int(t[3]), int(t[2]) + 1)]
    if not bits:
        raise SystemExit(f"u_bout_{bus}: no w_core_pi sources")
    other = re.sub(r"w_core_pi\d\[\d+:\d+\]", "", m[1]).replace("{", "").replace("}", "").replace(",", "").strip()
    if other:
        raise SystemExit(f"u_bout_{bus}: unexpected source terms {other!r}")
    return bits


def type_y(part, outline, die_y):
    ox, oy = part["origin_um"]
    W, H = outline
    o = part.get("orient", "R0")
    return die_y - oy if o in ("R0", "MY") else H - (die_y - oy)


def type_face(part, face):
    o = part.get("orient", "R0")
    if face in ("E", "W") and o in ("MY", "R180"):
        return {"E": "W", "W": "E"}[face]
    if face in ("N", "S") and o in ("MX", "R180"):
        return {"N": "S", "S": "N"}[face]
    return face


def build(raw, lef, bound):
    Q = copy.deepcopy(raw)
    parts = {p["name"]: p for p in Q["partitions"]}
    ports = {p["id"]: p for p in Q["ports"]}
    lanes = {ln["id"]: ln for ln in Q["lanes"]}
    pins = lef_pins(lef)
    report = dict(types={}, lanes={})
    for tn in TYPES:
        t = Q["partition_types"][tn]
        W, H = t["outline_um"]
        mac = next(c for c in t["contents"] if c.get("physical_inst") == "u_bound.u_core")
        assert mac.get("orient", "R0") == "R0", "macro orient"
        mx0, my0 = mac["origin_um"]
        mx1 = mx0 + mac["outline_um"][0]
        rtl = Path(bound[tn]).read_text()
        have = {e.get("conn") for e in t.get("internal_stations", [])}
        insts = [p for p in Q["partitions"] if p["type"] == tn]
        rows = {}
        for bus in BUSES:
            assert f"bus:{bus}" not in have, f"{tn}: {bus} already has internal_stations"
            b = next(x for x in t["buses"] if x["name"] == bus)
            assert b["dir"] == "out"
            src = bout_sources(rtl, bus)
            assert len(src) == b["width"], f"{tn}.{bus}: {len(src)} source bits != width {b['width']}"
            cp = [(mx0 + pins[k][0], my0 + pins[k][1]) for k in src]
            cen = (sum(x for x, _ in cp) / len(cp), sum(y for _, y in cp) / len(cp))
            # face window in the type frame, identical on every instance
            wins, lids = set(), []
            for ln in Q["lanes"]:
                a = ports[ln["ports"][0]]
                if a["src"].get("part") in parts and parts[a["src"]["part"]]["type"] == tn and a["src"]["bus"] == bus:
                    part = parts[a["src"]["part"]]
                    assert type_face(part, a["face"]) == "E", f"{tn}.{bus}: window not on the type E face"
                    ys = sorted(type_y(part, t["outline_um"], v) for v in a["window_um"])
                    wins.add(tuple(round(v, 2) for v in ys))
                    lids.append(ln["id"])
            assert len(wins) == 1, f"{tn}.{bus}: windows differ across instances {wins}"
            assert len(lids) == len(insts), f"{tn}.{bus}: {len(lids)} lanes for {len(insts)} instances"
            wy0, wy1 = next(iter(wins))
            win = (W, (wy0 + wy1) / 2)
            s0 = (mx1 + GAP, cen[1])
            regs_core_first = [s0] + [(s0[0] + (win[0] - s0[0]) * k / DEPTH, s0[1] + (win[1] - s0[1]) * k / DEPTH)
                                      for k in range(1, DEPTH)]
            # hops: worst bit pin -> s0, station -> station, last station -> worst face pin
            h0 = max(man(p, s0) for p in cp)
            hs = [man(a2, b2) for a2, b2 in zip(regs_core_first, regs_core_first[1:])]
            hl = max(man(regs_core_first[-1], (W, y)) for y in (wy0, wy1))
            worst = max([h0, hl] + hs)
            assert worst <= STEP, f"{tn}.{bus}: hop {worst:.1f} um > {STEP:.1f}"
            d_old = max(man(p, (W, y)) for p in cp for y in (wy0, wy1))
            words = sorted({w for w, _ in src})
            ent = dict(conn=f"bus:{bus}", from_um=r3(win), to_um=r3((mx0 + pins[src[0]][0], cen[1])),
                       regs_um=[r3(p) for p in reversed(regs_core_first)],
                       launch=f"u_core.{'+'.join(words)}", capture="face flop",
                       note=(f"KV-TYPES-5 11-08 PHY RE-FORM (COORD 10:0x): register at the macro output, "
                             f"stage 0 {GAP:g} um east of the macro edge on the bus pin rows, {DEPTH} source stations "
                             f"(one depth for all six PI buses, the pi words span lanes); worst bit macro pin -> face "
                             f"{d_old:.0f} um was unregistered, worst hop now {worst:.0f} um"))
            t.setdefault("internal_stations", []).append(ent)
            for lid in lids:
                ln = lanes[lid]
                assert int(ln.get("fixed_cycles", 0)) == 0, f"{lid}: fixed_cycles {ln.get('fixed_cycles')} != 0"
                d = ports[ln["ports"][-1]]["dst"]
                dt = Q["partition_types"][parts[d["part"]]["type"]]
                dest = [e for e in dt.get("internal_stations", []) if e.get("conn") == f"bus:{d['bus']}"]
                assert not dest, f"{lid}: receiver {d['part']}.{d['bus']} has internal stations"
                ln["fixed_cycles"] = DEPTH
                report["lanes"][lid] = dict(type=tn, bus=bus, fixed=[0, DEPTH], pin_cycles=DEPTH)
            rows[bus] = dict(bits=len(src), words=words, d_unregistered_um=round(d_old, 1),
                             hops_um=[round(h0, 1)] + [round(h, 1) for h in hs] + [round(hl, 1)],
                             regs_core_first=[r3(p) for p in regs_core_first], window_y=[wy0, wy1])
        report["types"][tn] = dict(buses=rows)
    # (2) host reset relays, kv3_phy
    t = Q["partition_types"]["kv3_phy"]
    rs = t.setdefault("relay_sites", {})
    sink = rs[f"{HOST_SINK}/q"]
    tap = t["reset"]["tap_um"]
    assert "port_relays" not in t["reset"]
    n = 2
    # L tap -> (sink.x, tap.y) -> sink, n points at equal arc length
    tot, dx = man(tap, sink), abs(sink[0] - tap[0])
    sites = []
    for k in range(1, n + 1):
        s = tot * k / (n + 1)
        sites.append([tap[0] + math.copysign(min(s, dx), sink[0] - tap[0]),
                      tap[1] + (math.copysign(s - dx, sink[1] - tap[1]) if s > dx else 0.0)])
    pts = [tap] + sites + [sink]
    hops = [man(a2, b2) for a2, b2 in zip(pts, pts[1:])]
    assert max(hops) <= STEP, f"reset relay hop {max(hops):.1f}"
    t["reset"]["port_relays"] = [dict(name="hrst", depth=n, sinks=[HOST_SINK])]
    for j, s in enumerate(sites):
        k = f"u_prl_hrst_{j}/q"
        assert k not in rs
        rs[k] = r3(s)
    k = f"{HOST_SINK}/eq"
    assert k not in rs
    rs[k] = list(sink)
    report["reset"] = dict(type="kv3_phy", tap_um=tap, sink_um=sink, relays=[r3(s) for s in sites],
                           hops_um=[round(h, 1) for h in hops], was_um=round(tot, 1))
    return Q, report


def check_preserved(raw, Q):
    """only the declared keys changed"""
    a, b = copy.deepcopy(raw), copy.deepcopy(Q)
    for tn in TYPES:
        for k in ("internal_stations", "reset", "relay_sites"):
            a["partition_types"][tn].pop(k, None)
            b["partition_types"][tn].pop(k, None)
    for la, lb in zip(a["lanes"], b["lanes"]):
        la.pop("fixed_cycles", None)
        lb.pop("fixed_cycles", None)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), "a key outside the event changed"
    # the old relay sites / reset / stations of the types are kept unchanged
    for tn in TYPES:
        for k in ("relay_sites", "reset"):
            old = raw["partition_types"][tn].get(k, {})
            new = Q["partition_types"][tn].get(k, {})
            assert all(new.get(x) == v for x, v in old.items()), f"{tn}.{k}: an existing entry changed"
        old = raw["partition_types"][tn].get("internal_stations", [])
        assert Q["partition_types"][tn].get("internal_stations", [])[:len(old)] == old


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--lef", required=True)
    ap.add_argument("--bound", action="append", required=True, help="TYPE=bound RTL file")
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--asbuilt-out", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    bound = dict(x.split("=", 1) for x in a.bound)
    assert set(bound) == set(TYPES)
    raw_bytes = Path(a.base).read_bytes()
    raw = json.loads(raw_bytes)
    Q, rep = build(raw, a.lef, bound)
    check_preserved(raw, Q)
    sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools/die_plan"))
    import schema as S
    errs = S.validate(Q)
    assert not errs, errs[:5]
    ab = json.loads(Path(a.asbuilt).read_text())
    sel = list(ab.get("internal_stations_types", []))
    assert not set(TYPES) & set(sel)
    ab2 = dict(ab, internal_stations_types=sorted(set(sel) | set(TYPES)))
    Path(a.out).write_text(json.dumps(Q, indent=1) + "\n")
    Path(a.asbuilt_out).write_text(json.dumps(ab2, indent=1) + "\n")
    rep.update(base_sha256=hashlib.sha256(raw_bytes).hexdigest(),
               out_sha256=hashlib.sha256(Path(a.out).read_bytes()).hexdigest(),
               asbuilt_out_sha256=hashlib.sha256(Path(a.asbuilt_out).read_bytes()).hexdigest())
    txt = json.dumps(rep, indent=1) + "\n"
    if a.report:
        Path(a.report).write_text(txt)
    print(json.dumps(dict(types={k: {b: v["hops_um"] for b, v in r["buses"].items()} for k, r in rep["types"].items()},
                          reset=rep["reset"], lanes=len(rep["lanes"])), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
