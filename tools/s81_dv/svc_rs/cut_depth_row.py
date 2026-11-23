#!/usr/bin/env python3
"""SVC-CUT-DEPTH row tool (S81-SVC-J9, rc15, 11-23): sizing and bookkeeping of the uniform extra depth on the hi svc attention cut.

The cut (dsdv_svc_att_cut inside dsdv_svc_rs_c, hi4 source pair) is a fixed-latency lock-step boundary: every registered in-lane
+1, every registered out-lane +1, no valid/ready.  Per-bus stations are therefore unsafe; the only safe form is one depth per
direction, the same on every hi piece pair (one RTL master): KA plain stages on the att side of the seam (wrapper CUT_D = 1 + KA)
and KR on the rest side (g_cutr relays in dsdv_svc_rs_c), written into the hi4 source by apply_cutdepth.py.

  cut_depth_row.py PLAN.json [--reach 405] [--ka N --kr N] [--rows OUT.json] [--report OUT.json]

1 SIZING (always): per hi piece pair, every internal cut lane (port note 'cut route leaf u_rsv_NN -> u_rsv_NN') window centre ->
  hard cores of each side, Manhattan in the type frame.  att side = engine cores (hcore / merge h4 / tr); rest side = all hard
  cores of the rest piece.  Printed min / median / max; segments = ceil(d / reach); K = segments - 1.  The uniform value this
  tool proposes is K of the largest MEDIAN over the pairs (the lanes end in soft logic the placer seats among the cores, and
  the engine cores sit behind their own SRX / XS stages); K(max) is printed as the hard-core-direct bound.
2 ROWS (--rows, needs --ka --kr): opentallas.latency_rows.v1 rows (rule R-RTL-6, kind RTL-INTERNAL), one per internal cut lane:
  added_cycles = KA + KR on the lane's direction.  The plan lane table is NOT changed: the stages are plain flops inside the
  two pieces (not u_bout / u_bin / u_ist / pads), so the bind lane count and LATCHECK read the same 2 boundary cycles as before.
  Schedule effect for the compiler: the attention share runs KA + KR edges later against the dn stream and every registered
  out-lane reaches the slice 2 x (KA + KR) edges later (the as-built cut already carries +1 / +2).
Exit 0; 2 when the plan has no hi cut lanes."""
import argparse, json, math, sys

ENG = ("ot_s81_svc_merge_h4", "ot_hdc_v41x_attn_tr_x", "ot_s81c_attn_hcore")
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def type_frame(part, typ, face, lo, hi):
    """die window on a part face -> (type face, centre along it)"""
    w, h = typ["outline_um"]; o = part.get("orient", "R0")
    if face in "NS":
        a, b = lo - part["origin_um"][0], hi - part["origin_um"][0]
        if o in ("MY", "R180"): a, b = w - b, w - a
        return (face if o not in ("MX", "R180") else OPP[face]), (a + b) / 2
    a, b = lo - part["origin_um"][1], hi - part["origin_um"][1]
    if o in ("MX", "R180"): a, b = h - b, h - a
    return (face if o not in ("MY", "R180") else OPP[face]), (a + b) / 2


def cut_ports(plan):
    for pr in plan["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if (s.startswith("svc_") and d.startswith("svc_") and s.split("_")[1] == d.split("_")[1] and s != d
                and "cut route leaf u_rsv" in pr.get("note", "") and pr.get("window_um")):
            yield pr


def sizing(plan, reach=405.0):
    T = plan["partition_types"]; parts = {p["name"]: p for p in plan["partitions"]}
    rows = {}
    for pr in cut_ports(plan):
        for part, face in ((pr["src"]["part"], pr["face"]), (pr["dst"]["part"], OPP[pr["face"]])):
            tn = parts[part]["type"]; t = T[tn]; w, h = t["outline_um"]
            f, c = type_frame(parts[part], t, face, *sorted(pr["window_um"]))
            px, py = {"W": (0, c), "E": (w, c), "S": (c, 0), "N": (c, h)}[f]
            cen = [(x["origin_um"][0] + x["outline_um"][0] / 2, x["origin_um"][1] + x["outline_um"][1] / 2, x.get("module") in ENG)
                   for x in t.get("hard_cores") or []]
            eng = [q for q in cen if q[2]]
            side = "att" if eng else "rest"
            dd = sorted(abs(px - x) + abs(py - y) for x, y, _ in (eng or cen))
            if not dd: continue
            r = rows.setdefault((int(pr["src"]["part"].split("_")[1]), tn, side), dict(lanes=0, bits=0, dmin=0.0, dmed=0.0, dmax=0.0, worst=None))
            r["lanes"] += 1; r["bits"] += pr["width"]
            if dd[-1] > r["dmax"]:
                r.update(dmin=dd[0], dmed=dd[len(dd) // 2], dmax=dd[-1], worst="%s@%s%d" % (pr["src"]["bus"], f, round(c)))
    k = lambda d: max(0, math.ceil(d / reach) - 1)
    out = []
    for (n, tn, side), r in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][2])):
        out.append(dict(pair="svc_%d" % n, type=tn, side=side, k_med=k(r["dmed"]), k_max=k(r["dmax"]), **{a: (round(v, 1) if isinstance(v, float) else v) for a, v in r.items()}))
    uni = {}
    for side in ("att", "rest"):
        v = [x for x in out if x["side"] == side]
        if v:
            uni[side] = dict(max_median_um=max(x["dmed"] for x in v), k_med=max(x["k_med"] for x in v), max_um=max(x["dmax"] for x in v), k_max=max(x["k_max"] for x in v))
    return out, uni


def latency_rows(plan, ka, kr, event="S81-SVC-J9-cutdepth"):
    lane_of = {}
    for ln in plan["lanes"]:
        for p in ln.get("ports", []): lane_of[p] = ln["id"]
    T = plan["partition_types"]; parts = {p["name"]: p for p in plan["partitions"]}
    is_att = lambda part: any(x.get("module") in ENG for x in T[parts[part]["type"]].get("hard_cores") or [])
    lat = (plan.get("latency") or {}).get("lanes") or {}
    rows = []
    for pr in cut_ports(plan):
        lid = lane_of.get(pr["id"])
        if lid is None: continue
        direction = "in (rest -> att)" if is_att(pr["dst"]["part"]) else "out (att -> rest)"
        cyc = (lat.get(lid) or {}).get("cycles")
        rows.append(dict(id="%s:%s" % (event, lid), lane=lid, parameter="LAT_" + lid.upper(), kind="RTL-INTERNAL", added_cycles=ka + kr,
                         clock="clk_core (833 ps)", pair=pr["src"]["part"].split("_")[0] + "_" + pr["src"]["part"].split("_")[1],
                         direction=direction, bus=pr["src"]["bus"], width=pr["width"], lane_table_cycles=cyc,
                         relative_to="plan lane table (unchanged: %s boundary cycles); the %d + %d stages are plain flops inside the pieces" % (cyc, ka, kr),
                         why="SVC-CUT-DEPTH: uniform cut depth, att side OT_SVC_CUT_KA=%d (wrapper CUT_D=%d), rest side OT_SVC_CUT_KR=%d" % (ka, 1 + ka, kr)))
    return dict(schema="opentallas.latency_rows.v1", rule="R-RTL-6", event=event, defines=dict(OT_SVC_CUT_KA=ka, OT_SVC_CUT_KR=kr),
                schedule=dict(att_share_vs_dn_stream_edges=ka + kr, registered_out_lane_at_slice_edges=2 * (ka + kr),
                              as_built_cut=dict(att_share=1, out_lane=2), note="lock-step: same depth on every registered lane of a direction, every hi pair"),
                rows=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--ka", type=int); ap.add_argument("--kr", type=int); ap.add_argument("--rows"); ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    tab, uni = sizing(plan, a.reach)
    if not tab:
        print("no hi cut lanes in the plan"); return 2
    for x in tab:
        print("%-7s %-34s %-4s lanes %2d bits %5d  d min/med/max %5.0f %5.0f %5.0f um  K(med) %d  K(max) %d  worst %s" % (
            x["pair"], x["type"], x["side"], x["lanes"], x["bits"], x["dmin"], x["dmed"], x["dmax"], x["k_med"], x["k_max"], x["worst"]))
    for side, u in uni.items():
        print("UNIFORM %-4s reach %.0f: largest median %.0f um -> K %d ; largest max %.0f um -> K %d" % (side, a.reach, u["max_median_um"], u["k_med"], u["max_um"], u["k_max"]))
    rep = dict(reach_um=a.reach, pairs=tab, uniform=uni)
    if a.rows:
        if a.ka is None or a.kr is None: ap.error("--rows needs --ka and --kr")
        doc = latency_rows(plan, a.ka, a.kr)
        json.dump(doc, open(a.rows, "w"), indent=1); print("ROWS %d lanes, +%d cycles each -> %s" % (len(doc["rows"]), a.ka + a.kr, a.rows))
        rep["rows"] = len(doc["rows"]); rep["ka"] = a.ka; rep["kr"] = a.kr
    if a.report: json.dump(rep, open(a.report, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
