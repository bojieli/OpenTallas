#!/usr/bin/env python3
"""DS85 CLKDIE-S81 (DO_NOT_COUNT): per-landing ring arrivals for landing_phase_sign.py (OT_LANDING_PHASE_ARRIVALS
schema: corners.<C>.<port> = {t_local_ps, t_fwd_ps, p_up_ps, p_dn_ps}, port = bind_clock_landings ports[].port).

Per bind landing (src partition s, bus fclk_out_<src_bus> -> dst partition d, ring u_cland_<dst_bus>), corner C:
  t_local = A_die(d.<read tap>) + I_d(read tap port -> ring read-side flop CLK, mean)
  t_fwd   = A_die(s.<fwd tap>)  + I_s(fwd tap port -> fclk_out_<src_bus> port) + N(fclk_out -> fclk_in, routed)
            + I_d(fclk_in_<dst_bus> port -> ring write flop CLK, mean)
  A_die   = clock-only die GRT route (estimate_parasitics -global_routing), late arrival at tap port t_<part>__<tap>,
            x the die STA spice clock cal of the die clock cell (die_sta_related SPICE_CLOCK_CAL_INV for inv/inv2)
  I_*     = the type's routed view (SPEF), OpenSTA NLDM at C, source-rise edge (type_clk.tcl / type_parse.py);
            fallback when the type has no routed view: plan budget (clock.common_latency_ps TT, x0.81 FF) for the
            read side and fclk_out, the measured median of the covered types for the write side, read tap = plan
            tap nearest the fclk_in pin, fwd tap = the plan pin's source_clock_port.
  p_up / p_dn = clk_aocv.branch_pessimism (the approved g = 0.21 %/mm table, as landed_phase_ocv / die_sta_related):
            branches below the last common die tree cell, die part class Ainv (stages = cells below the LCA), the
            partition-internal part class B (stages = round(I / mu_stage_B)), distance = bbox diagonal of the two taps,
            the LCA cell and the ring's fclk_in pin; droop: different clock regions -> +5.1 % one-sided late on the late
            branch.  p_up = local late + fwd early (d grows), p_dn = fwd late + local early.  The ring's own flop
            spread (read max-mean / mean-min, write mean-min / max-mean) is added to p_up / p_dn.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path


def arrivals(f):
    T, N, L, D = {}, {}, {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if not x:
            continue
        if x[0] == "T":
            T[x[1]] = float(x[2])
        elif x[0] == "N":
            N[x[1]] = float(x[2])
        elif x[0] == "L":
            L[x[1]] = float(x[2])
        elif x[0] == "D":
            D[x[1]] = (float(x[2]), float(x[3]))
    return T, N, L, D


def chain(tree, cell):
    out = [cell]
    while cell in tree["parent_of"]:
        cell = tree["parent_of"][cell]
        out.append(cell)
    return out


def lca(ca, cb):
    sb = set(cb)
    for i, c in enumerate(ca):
        if c in sb:
            return c, i, cb.index(c)
    raise ValueError("no common cell")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--bind", required=True)
    ap.add_argument("--route", required=True, help="combo dir: arr_TT.txt arr_FF.txt landing_nets.json")
    ap.add_argument("--tree", required=True)
    ap.add_argument("--types", required=True, nargs="+", help="dirs of <type>/type_clk.json, in priority order "
                    "(routed views first, then CTS-stage views); label = dir basename")
    ap.add_argument("--tools", required=True)
    ap.add_argument("--clock-cal", choices=("spice", "none"), default="spice")
    ap.add_argument("--out", required=True)
    ap.add_argument("--detail", required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.tools)
    import clk_aocv as CA
    import die_sta_related as DSR
    T = CA.load(Path(a.tools) / "clk_aocv_table_g021.json")
    plan = json.loads(Path(a.plan).read_text())
    parts = {p["name"]: p for p in plan["partitions"]}
    PT = plan["partition_types"]
    tree = json.loads(Path(a.tree).read_text())
    cc = (tree.get("meta") or {}).get("clock_cell")
    cmodel = "inv" if cc in ("inv", "inv2") else "buf"
    cls = DSR.CLOCK_CELL_AOCV_CLASS[cmodel]
    taps = {t["port"]: t for t in tree["taps"]}
    lnets = {d["id"]: d for d in json.loads((Path(a.route) / "landing_nets.json").read_text())}
    bind = json.loads(Path(a.bind).read_text())["ports"]
    tv, tkind = {}, {}
    for td_ in a.types:
        for f in Path(td_).glob("*/type_clk.json"):
            j = json.loads(f.read_text())
            if j and f.parent.name not in tv:
                tv[f.parent.name] = j
                tkind[f.parent.name] = Path(td_).name
    lat = float(plan["clock"]["common_latency_ps"])
    budget = {"TT": lat, "FF": lat * 0.81}

    def to_die(part, xy):
        p = parts[part]
        w, h = PT[p["type"]]["outline_um"]
        x, y = xy
        X, Y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[p.get("orient", "R0")]
        return p["origin_um"][0] + X, p["origin_um"][1] + Y

    def lc_pin(part, name):
        for q in PT[parts[part]["type"]]["clock"]["landing_contract"]["pins"]:
            if q["name"] == name:
                return q
        return None

    part_taps = {}
    for t in tree["taps"]:
        part_taps.setdefault(t["part"], []).append(t)

    def nearest_tap(part, xy):
        """die tree tap of `part` nearest (Manhattan, die coordinates) to the die point xy"""
        return min(part_taps[part], key=lambda t: abs(t["xy"][0] - xy[0]) + abs(t["xy"][1] - xy[1]))["tap"]

    # write-side fallback = median of the measured rings per corner
    wmed = {}
    for c in ("TT", "FF"):
        v = [r["write"]["mean"] for j in tv.values() if c in j for r in j[c]["rings"].values() if r["write"]["n"]]
        wmed[c] = statistics.median(v) if v else 0.0
    out = dict(source=None, corners={})
    detail = dict(method=__doc__, clock_cell=cc, aocv_class=cls, clock_cal=a.clock_cal, write_fallback_median=wmed,
                  budget=budget, corners={})
    for C in ("TT", "FF"):
        f = Path(a.route) / f"arr_{C}.txt"
        TA, NA, LA, DA = arrivals(f)
        k = DSR.spice_cal_factor(C, cmodel) if a.clock_cal == "spice" else 1.0
        yref = DA["fd_ref"][0]
        B = T["classes"]["B"][C]
        fc = T["classes"][cls][C]["cell_share"]
        rows, arr = [], {}
        for q in bind:
            s, d = q["src"], q["dst"]
            ts, td = parts[s]["type"], parts[d]["type"]
            obus, ibus = "fclk_out_" + q["src_bus"], "fclk_in_" + q["dst_bus"]
            src_v = tv.get(ts, {}).get(C)
            dst_v = tv.get(td, {}).get(C)
            pin_o, pin_i = lc_pin(s, obus), lc_pin(d, ibus)
            ring_xy = to_die(d, pin_i["xy_um"])
            src_meas = bool(src_v and src_v["fclk_out"].get(obus))
            ring = dst_v["rings"].get(q["dst_bus"]) if dst_v else None
            dst_meas = bool(ring and ring["write"]["n"] and ring["read"]["n"])
            if src_meas:
                ftap, i_out = src_v["fclk_out"][obus]["port"], src_v["fclk_out"][obus]["ins"]
            else:
                ftap, i_out = pin_o.get("source_clock_port") or nearest_tap(s, to_die(s, pin_o["xy_um"])), budget[C]
            if dst_meas:
                rbp = ring["read_by_port"]
                rtap = max(rbp, key=lambda k_: rbp[k_]["n"])
                i_rd, rd_max, rd_min = rbp[rtap]["mean"], rbp[rtap]["max"], rbp[rtap]["min"]
                i_wr, wr_max, wr_min = ring["write"]["mean"], ring["write"]["max"], ring["write"]["min"]
            else:
                rtap = nearest_tap(d, ring_xy)
                i_rd = rd_max = rd_min = budget[C]
                i_wr = wr_max = wr_min = wmed[C]
            tp_s, tp_d = f"t_{s}__{ftap}", f"t_{d}__{rtap}"
            if tp_s not in TA or tp_d not in TA:
                rows.append(dict(port=q["port"], error=f"tap missing {tp_s if tp_s not in TA else tp_d}"))
                continue
            a_s, a_d = TA[tp_s] * k, TA[tp_d] * k
            e = lnets["cland_clk__" + q["port"]]
            net = LA[f"lnd_out_{e['i']}"] - yref
            t_local = a_d + i_rd
            t_fwd = a_s + i_out + net + i_wr
            ta, tb = taps[tp_s], taps[tp_d]
            la_, lb_ = ta.get("driver", tree["node_buf"][str(ta["node"])]), tb.get("driver", tree["node_buf"][str(tb["node"])])
            ca_, cb_ = chain(tree, la_), chain(tree, lb_)
            node, ia, ib = lca(ca_, cb_)
            nxy = tree["sites"][node]
            pts = [ta["xy"], tb["xy"], nxy, list(ring_xy)]
            dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
            nd = NA[node] * k

            def br(u, internal, nst, net_extra=0.0):
                stg = {cls: nst}
                nB = max(1, round(internal / B["mu_stage_ps"])) if internal > 0 else 0
                if nB:
                    stg["B"] = nB
                return dict(cell_ps=fc * u + B["cell_share"] * internal,
                            net_ps=(1 - fc) * u + (1 - B["cell_share"]) * internal + net_extra, stages=stg)
            bfwd = br(a_s - nd, i_out + i_wr, ia, net)
            bloc = br(a_d - nd, i_rd, ib)
            p_up = CA.branch_pessimism(T, C, bloc, bfwd, dist, False, "setup")
            p_dn = CA.branch_pessimism(T, C, bfwd, bloc, dist, False, "setup")
            p_up += (rd_max - i_rd) + (i_wr - wr_min)
            p_dn += (i_rd - rd_min) + (wr_max - i_wr)
            arr[q["port"]] = dict(t_local_ps=round(t_local, 2), t_fwd_ps=round(t_fwd, 2), p_up_ps=round(p_up, 2),
                                  p_dn_ps=round(p_dn, 2))
            rows.append(dict(port=q["port"], lane=q["lane"], src=s, dst=d, src_type=ts, dst_type=td,
                             src_view=tkind[ts] if src_meas else "DECLARED", dst_view=tkind[td] if dst_meas else "DECLARED",
                             fwd_tap=tp_s, read_tap=tp_d, A_src=round(a_s, 2), A_dst=round(a_d, 2), lca=node,
                             die_stages_fwd=ia, die_stages_local=ib, dist_um=round(dist, 1), I_out=i_out,
                             net_ps=round(net, 2), hop_um=e["hop_um"], I_write=i_wr, I_read=i_rd,
                             d_ps=round(t_local - t_fwd, 2), **arr[q["port"]]))
        out["corners"][C] = arr
        detail["corners"][C] = dict(spice_factor=k, rows=rows)
    out["source"] = (f"DS85 CLKDIE-S81 clock-only die GRT route on plan_h2_2249 ({a.route}) + type routed views "
                     f"({a.types}); clock_cal {a.clock_cal}; DO_NOT_COUNT")
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    Path(a.detail).write_text(json.dumps(detail, indent=1) + "\n")
    for C in ("TT", "FF"):
        r = [x for x in detail["corners"][C]["rows"] if "d_ps" in x]
        print(C, len(r), "errors", sum(1 for x in detail["corners"][C]["rows"] if "error" in x),
              "both measured", sum(1 for x in r if "DECLARED" not in (x["src_view"], x["dst_view"])),
              "views", __import__("collections").Counter((x["src_view"], x["dst_view"]) for x in r).most_common())


if __name__ == "__main__":
    main()
