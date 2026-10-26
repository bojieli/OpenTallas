#!/usr/bin/env python3
"""KV-PLAN3 10-25: explicit channel station sites (ft_slots[].regs_um, type frame) for feed-through slots whose default
Z route (check.zroute: jog at mid-height) runs THROUGH a row of planned hard cores.  Hard cores obstruct every routing
layer of the partition (g2.probe_blockages), so such a hop has no track at all: kv3_hg_v3 ft2 (S->N 1 b + epoch, the
hub_Eo hop of the hg chain) jogged at y 760 through the head-core row -> G2 M2 overflow 1514 on capacity-0 GCells.
The slot keeps its windows and its station count (no latency change); the route is the channel path through the
WAYPOINTS (vertical channel of the in-window -> horizontal channel between head rows -> vertical channel next to the
out-window column -> the N strip above the ECTLK quarters), and stations sit at L*j/k along it (same rule as the
default route), so every hop is a channel hop.  face_flops.tcl (kits) and g2.py read regs_um.
usage: ft_channel_regs.py DIE_PLAN.json [--report R.json]    (in place)
"""
import argparse
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / "tools" / "die_plan"))
import check  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

# type -> slot -> waypoints between the in pin and the out pin (type frame; channel centre lines)
#   kv3_hg cores: columns x 17.28-233.28 | 336.96-552.96 | 656.64-872.64 | 976.32-1192.32,
#   head rows y 17-233 | 337-553 | 657-873 | 976-1192, ECTLK quarters y 1330.56-1503.36 (N face 1520.64)
ROUTES = {"kv3_hg_v3": {"ft2": "in_x:924.48 285.12:924.48 285.12:1512.0 out_x:1512.0"}}


def waypoints(spec, a, b):
    pts = [a]
    for tok in spec.split():
        x, y = tok.split(":")
        x = a[0] if x == "in_x" else b[0] if x == "out_x" else float(x)
        pts.append((x, float(y)))
    pts.append(b)
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--report")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(raw, Path(a.plan).resolve())
    rep = {}
    for tn, slots in ROUTES.items():
        pins = gen_phys.type_pins(P, tn)
        t = raw["partition_types"][tn]
        for s in t["ft_slots"]:
            if s["name"] not in slots:
                continue
            pi = sorted((x, y) for bus, bit, ln, x, y, f in pins if bus == s["name"] + "_i")
            po = sorted((x, y) for bus, bit, ln, x, y, f in pins if bus == s["name"] + "_o")
            ain = (sum(p[0] for p in pi) / len(pi), sum(p[1] for p in pi) / len(pi))
            bout = (sum(p[0] for p in po) / len(po), sum(p[1] for p in po) / len(po))
            seg = waypoints(slots[s["name"]], ain, bout)
            L = check.plen(seg)
            k = int(s.get("stations", 1))
            s["regs_um"] = [[round(c, 3) for c in check.point_at(seg, L * j / k)] for j in range(k)]
            hops = [check.plen([tuple(p), tuple(q)]) for p, q in zip(s["regs_um"], s["regs_um"][1:] + [list(bout)])]
            s["note"] = (s.get("note", "") + " | KV-PLAN3 v3.9e: channel station sites (default Z jog crossed the "
                         "head-core row; ft_channel_regs.py)").lstrip(" |")
            rep[f"{tn}.{s['name']}"] = dict(path=[[round(c, 2) for c in p] for p in seg], length_um=round(L, 1),
                                            stations=k, regs_um=s["regs_um"], hop_max_um=round(max(hops), 1))
    Path(a.plan).write_text(json.dumps(raw, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("ft_channel_regs:", json.dumps({k: (v["length_um"], v["hop_max_um"]) for k, v in rep.items()}))


if __name__ == "__main__":
    main()
