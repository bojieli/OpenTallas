#!/usr/bin/env python3
"""KV-TIMING-FORMS-1 11-12 (DIE-KV-98): reset relay stages INSIDE kv3_phy and kv3_phy_v1 (hard wrappers, delivered reset).

WHY: both wrappers carry `wire rst_n = arst_n;`, so every ot_dp_st epoch flop (eq) of the type has its reset pin on the arst_n
port net: kv3_phy_v1 attempt_6 TT -120.9 / -60.7 (arst_n port -> 16 chained buffers -> u_ist_*/eq, u_ft_ft0_o_3/eq), FF hold
-27.5 (arst_n -> u_bout_*/eq); kv3_phy attempt_12 hold -26.7 / -16.2.  The type is 864 x 1520.6 um with the reset port at
reset.tap_um (842.4, 760.32): stations lie up to 1170 um (Manhattan) away.
FORM: reset.port_relays (tools/die_plan/reset_port_relays.py, KV-TYPES-5): clusters of the ot_dp_st sinks, each cluster
takes the reset from a chain of ot_dp_rrelay flops sited along the L path tap -> cluster centroid (hop <= REACH*0.98), last
relay within CLUSTER_R of every sink of its cluster.  Plan keys changed: partition_types[kv3_phy|kv3_phy_v1].reset.port_relays
(rows appended; the existing kv3_phy hrst row is kept) and .relay_sites (u_prl_<g>_<j>/q).  Nothing else.
BOOT-ONLY: the sinks assert/release depth clocks later than the rest of the wrapper (async assertion is NOT delayed: relays
are synchronous, assertion reaches them via the clocked reset, see reset_port_relays.py).  usage:
  phy_reset_relays.py PLAN_IN PLAN_OUT BOUND_RTL_DIR [--report R.json]"""
import copy, json, math, re, sys
from pathlib import Path
REACH = 405.0
HOP = REACH * 0.98
CLUSTER_R = 300.0
TYPES = ("kv3_phy", "kv3_phy_v1")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sinks_of(t, d, txt):
    """{ot_dp_st instance: (x,y)} for every instance whose rst_n is the delivered rst_n"""
    pos = {}
    ist = {e["conn"].split(":", 1)[1]: e for e in d.get("internal_stations", []) if e["conn"].startswith("bus:")}
    ft = {s["name"]: s for s in d.get("ft_slots", [])}
    rs = d.get("relay_sites", {})
    miss = []
    for m in re.finditer(r"ot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+(\w+)\s*\(([^;]*?)\);", txt, re.S):
        n, body = m[2], m[3]
        if not re.search(r"\.rst_n\(rst_n\)", body):
            continue
        p = None
        mm = re.fullmatch(r"u_ist_(\w+?)_(\d+)", n)
        if mm and mm[1] in ist:
            p = ist[mm[1]]["regs_um"][int(mm[2])]
        mm = re.fullmatch(r"u_bout_(\w+)", n)
        if p is None and mm and mm[1] in ist:
            p = ist[mm[1]]["to_um"]
        mm = re.fullmatch(r"u_ft_(\w+?)_o_(\d+)", n)
        if p is None and mm and mm[1] in ft:
            p = ft[mm[1]]["regs_um"][int(mm[2])]
        if p is None:
            q = [v for k, v in rs.items() if k.startswith(n + "/")]
            if q:
                p = [sum(v[0] for v in q) / len(q), sum(v[1] for v in q) / len(q)]
        if p is None and n == "u_bin_i_host_hbm_rst_n":
            p = rs.get("u_bin_i_host_hbm_rst_n/q")
        if p is None:
            miss.append(n)
        else:
            pos[n] = [float(p[0]), float(p[1])]
    return pos, miss


def cluster(pos):
    """greedy: sort by distance from the tap side, open a cluster when a sink is > CLUSTER_R from every centroid"""
    cl = []
    for n, p in sorted(pos.items(), key=lambda kv: (kv[1][1], kv[1][0], kv[0])):
        for c in cl:
            if man(c["c"], p) <= CLUSTER_R:
                c["m"].append((n, p))
                c["c"] = [sum(q[0] for _, q in c["m"]) / len(c["m"]), sum(q[1] for _, q in c["m"]) / len(c["m"])]
                break
        else:
            cl.append(dict(c=list(p), m=[(n, p)]))
    # settle: reassign every sink to the nearest centroid, then require the radius
    for _ in range(3):
        for c in cl:
            c["m"] = []
        for n, p in pos.items():
            min(cl, key=lambda c: man(c["c"], p))["m"].append((n, p))
        cl = [c for c in cl if c["m"]]
        for c in cl:
            c["c"] = [sum(q[0] for _, q in c["m"]) / len(c["m"]), sum(q[1] for _, q in c["m"]) / len(c["m"])]
    return cl


def lpath(a, b, depth):
    """depth sites on the x-then-y L path a -> b, the last one at b; consecutive hops <= HOP when depth >= ceil(len/HOP)"""
    L = man(a, b)
    out = []
    for j in range(1, depth + 1):
        s = L * j / depth
        dx = abs(b[0] - a[0])
        if s <= dx:
            x = a[0] + math.copysign(s, b[0] - a[0]); y = a[1]
        else:
            x = b[0]; y = a[1] + math.copysign(s - dx, b[1] - a[1])
        out.append([round(x, 3), round(y, 3)])
    return out


def apply(plan, bound_dir):
    out = copy.deepcopy(plan)
    rep = {}
    for tn in TYPES:
        d = out["partition_types"][tn]
        txt = Path(bound_dir, f"{tn}_part.sv").read_text()
        pos, miss = sinks_of(d, d, txt)
        already = {s for r in d["reset"].get("port_relays", []) for s in r["sinks"]}
        pos = {n: p for n, p in pos.items() if n not in already}
        tap = d["reset"]["tap_um"]
        outl = d["outline_um"]
        rows = d["reset"].setdefault("port_relays", [])
        sites = d.setdefault("relay_sites", {})
        cl = cluster(pos)
        cl.sort(key=lambda c: (c["c"][1], c["c"][0]))
        info = []
        for gi, c in enumerate(cl):
            c["c"] = [round(min(max(c["c"][0], 1.0), outl[0] - 1.0), 3), round(min(max(c["c"][1], 1.0), outl[1] - 1.0), 3)]
            L = man(tap, c["c"])
            depth = max(1, math.ceil(L / HOP))
            assert depth <= 8, (tn, gi, L)
            name = f"rg{gi}"
            pts = lpath(tap, c["c"], depth)
            for j, p in enumerate(pts):
                k = f"u_prl_{name}_{j}/q"
                assert k not in sites, k
                sites[k] = p
            far = max(man(c["c"], p) for _, p in c["m"])
            rows.append(dict(name=name, depth=depth, sinks=sorted(n for n, _ in c["m"])))
            info.append(dict(name=name, depth=depth, centroid=c["c"], sinks=len(c["m"]), path_len_um=round(L, 1),
                             max_hop_um=round(max(man(a, b) for a, b in zip([tap] + pts, pts)), 1), sink_radius_um=round(far, 1)))
        rep[tn] = dict(sinks=len(pos), unplaced=miss, groups=info)
    # nothing else may differ
    for tn in TYPES:
        a, b = plan["partition_types"][tn], out["partition_types"][tn]
        for k in a:
            if k in ("relay_sites",):
                continue
            if k == "reset":
                assert {x: y for x, y in a[k].items() if x != "port_relays"} == {x: y for x, y in b[k].items() if x != "port_relays"}
                continue
            assert a[k] == b[k], (tn, k)
    return out, rep


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    rp = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    if rp:
        a = [x for x in a if x != rp]
    plan = json.loads(Path(a[0]).read_text())
    out, rep = apply(plan, a[2])
    Path(a[1]).write_text(json.dumps(out, indent=1) + "\n")
    if rp:
        Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({t: dict(sinks=r["sinks"], unplaced=len(r["unplaced"]), groups=[(g["name"], g["depth"], g["sinks"], g["max_hop_um"], g["sink_radius_um"]) for g in r["groups"]]) for t, r in rep.items()}))
