#!/usr/bin/env python3
"""DIE-S81-31 10-29 fix-only plan event: slice_station clock taps (GEOM-64 t23 FAIL, COORD t8 A2 clock_reach FAIL).

Measured (geom_rules on the placed canaries): t23 (density taps over face/ft sinks only) leaves the reset-entry /
collector-root flops at the NE corner (u_rst_in, u_cland_collect_rst_root_n) 1043 um and the N-edge wire relays
(u_rrl_0/1, collectors) 348-695 um from every tap; fclk_out_cland_up launches from clk_t15 1040 um away.  t8 (R4 grid
4x4, 360x307 cells) leaves 6346 sinks > 220 um from every tap (cell corners are 333 um from the 4 centres) and loads
taps 3..3076 sinks.  Both are the tap method, not the band or the RTL.

Event (existing opt-ins only, no tool change): every slice_station type takes clock.tap_mode "density"
(OWNER decision 5 density taps, as t23 already has) with clock.control_sinks (arst_n / rst_o / start pins are sinks)
and plan-declared clock.sink_sites_um rows for the sinks the planned_sinks inventory does not see:
  * band rows: each landing ring band's local-read flops (clock_roles.local_read_flops) spread along the band;
  * monitor rows: each seam child's cland_dn monitor capture (2-bit ring + collector) at its xy;
  * chain rows (iterated to a fixed point): every reset/collector relay of the type's wavefront tree, and every
    forwarded-clock output pin, that is farther than tap_radius_um from every tap.
Then the stored landing contract fields that are functions of the taps are recomputed with the same tool functions
compose() uses (collector_tree = reset_tree.for_type, local-source taps, consumer-indexed rst_n_t nodes, forwarded clock
source taps).  Invariants checked (fail closed): the die wavefront (per-partition parent, source, release, per-type
in_um / outs / depth_K) is unchanged, so no release offset, START time or die reset wire moves.

usage: delta_stationtaps_1029.py PLAN_IN PLAN_OUT --radius 150 [--report r.json] [--types t8,t23]
"""
import argparse, copy, json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S, reset_tree as RT, taps as TP, gen_phys as GP  # noqa: E402
import compact_plan  # noqa: E402

BAND_STEP_UM = 54.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def stations(raw, only=None):
    out = [tn for tn in raw["partition_types"] if tn.startswith("slice_station__")]
    return [tn for tn in out if not only or tn.split("__")[1] in only or tn in only]


def base_rows(t):
    """band local-read rows + seam-monitor rows (type frame)."""
    lc = t["clock"].get("landing_contract") or {}
    rows = []
    for bus, b in sorted((lc.get("bands") or {}).items()):
        r = b.get("rect_um")
        if not r or bus.startswith("monitor_"):
            continue
        n = float((b.get("clock_roles") or {}).get("local_read_flops", 0))
        if n <= 0:
            continue
        x0, y0, x1, y1 = r
        horiz = (x1 - x0) >= (y1 - y0)
        L = (x1 - x0) if horiz else (y1 - y0)
        k = max(1, math.ceil(L / BAND_STEP_UM))
        for i in range(k):
            f = (i + 0.5) / k
            xy = ((x0 + f * (x1 - x0), (y0 + y1) / 2) if horiz else ((x0 + x1) / 2, y0 + f * (y1 - y0)))
            rows.append([round(xy[0], 3), round(xy[1], 3), round(n / k, 3)])
    for c in lc.get("collector_children") or []:
        if c.get("seam"):
            rows.append([round(c["xy_um"][0], 3), round(c["xy_um"][1], 3), 8.0])
    return rows


def configure(t, radius, rows):
    ck = t["clock"]
    ck.update(tap_mode="density", tap_target_sinks=600, tap_max_sinks=1500, tap_radius_um=float(radius),
              control_sinks=True, sink_sites_um=rows)


def chain_points(P, tn):
    """relay sites of the type's wavefront tree + forwarded clock out pins (type frame)."""
    T = RT.for_type(P, tn)
    pts = [tuple(T["root"])] + [tuple(r["xy"]) for r in T["relays"]]
    lc = P.types[tn]["clock"].get("landing_contract") or {}
    pts += [tuple(p["xy_um"]) for p in lc.get("pins", []) if p["kind"] == "clock" and p["dir"] == "out"]
    return pts


def wf_signature(P, types):
    W = RT.wf_plan(P)
    sig_t = {tn: {k: W["types"][tn][k] for k in ("in_um", "outs", "depth_K", "release_after_pin", "entry_stages")}
             for tn in types if tn in W["types"]}
    sig_p = {pn: {k: r.get(k) for k in ("parent", "source", "release", "depth_K")} for pn, r in W["parts"].items()}
    return json.loads(json.dumps(dict(types=sig_t, parts=sig_p, max_release=W["max_release"])))


def fix_contract(P, tn, old_cc):
    """recompute the tap-dependent landing contract fields of type tn (compose() rules)."""
    t = P.types[tn]
    lc = t["clock"].get("landing_contract")
    if not lc:
        return {}
    T = RT.for_type(P, tn)
    new_cc = RT.consumer_count(T)
    ch = {}

    def renode(n):
        if n and n.startswith("rst_n_t"):
            i = int(n[7:])
            if i >= old_cc:
                return f"rst_n_t{i - old_cc + new_cc}"
            raise SystemExit(f"{tn}: contract node {n} names a tap consumer (not a reset out); unsupported")
        return n
    tree = json.loads(json.dumps(T))
    if lc.get("collector_tree") is not None:
        lc["collector_tree"] = tree
        ch["collector_tree"] = len(tree["relays"])
    tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in T["relays"] if r["q"].startswith("rst_n_t")}
    for s in lc.get("collector_local_sources") or []:
        point = s["pin_xy_um"]
        tap = min(range(new_cc), key=lambda i: man(tapxy[i], point))
        status = None
        band = s.get("band") or {}
        if band.get("rect_um") and man(tapxy[tap], point) > 405:
            x0, y0, x1, y1 = band["rect_um"]
            status = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = min(range(new_cc), key=lambda i: man(tapxy[i], status))
        s["tap"] = tap
        s["xy_um"] = status or point
    if lc.get("collector_root_node"):
        lc["collector_root_node"] = renode(lc["collector_root_node"])
    for c in lc.get("collector_children") or []:
        c["node"] = renode(c["node"])
    roots = GP.clock_pins(P, tn)
    for pin in lc.get("pins", []):
        if pin["kind"] == "clock" and pin["dir"] == "out":
            tap = min(roots, key=lambda r: abs(r[1] - pin["xy_um"][0]) + abs(r[2] - pin["xy_um"][1]))[0]
            if pin.get("source_clock_tap") is not None:
                pin["source_clock_tap"] = tap
            else:
                pin["source_clock_port"] = tap
    ch.update(consumers=(old_cc, new_cc))
    return ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--radius", type=float, default=150.0)
    ap.add_argument("--types", default="")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--report", default="")
    ap.add_argument("--sidecar-in", default="")
    ap.add_argument("--sidecar-out", default="")
    a = ap.parse_args()
    t0 = time.time()
    raw0 = json.loads(Path(a.plan_in).read_text())
    only = set(x for x in a.types.split(",") if x)
    tns = stations(raw0, only)
    P0 = S.Plan(copy.deepcopy(raw0), a.plan_in)
    sig0 = wf_signature(P0, tns)
    old = {}
    for tn in tns:
        T0 = RT.for_type(P0, tn)
        old[tn] = dict(cc=RT.consumer_count(T0), taps=[list(x) for x in S.tap_grid(P0, tn)], depth=T0["depth"])
    print(f"baseline {len(tns)} station types, {time.time()-t0:.0f}s", flush=True)
    raw = copy.deepcopy(raw0)
    rows = {tn: base_rows(raw["partition_types"][tn]) for tn in tns}
    for tn in tns:
        configure(raw["partition_types"][tn], a.radius, rows[tn])
    for rnd in range(a.rounds):
        P = S.Plan(raw, a.plan_out)
        added = 0
        for tn in tns:
            taps = [(x, y) for _, x, y in S.tap_grid(P, tn)]
            for p in chain_points(P, tn):
                if min(man(p, q) for q in taps) > a.radius + 1e-6:
                    if not any(man(p, r[:2]) < 1e-3 for r in rows[tn]):
                        rows[tn].append([round(p[0], 3), round(p[1], 3), 1.0])
                        added += 1
        print(f"round {rnd}: +{added} chain rows ({time.time()-t0:.0f}s)", flush=True)
        if not added:
            break
        for tn in tns:
            raw["partition_types"][tn]["clock"]["sink_sites_um"] = rows[tn]
    else:
        raise SystemExit("chain rows did not converge")
    P = S.Plan(raw, a.plan_out)
    sig1 = wf_signature(P, tns)
    if sig1 != sig0:
        bad_t = [tn for tn in sig0["types"] if sig0["types"][tn] != sig1["types"].get(tn)]
        bad_p = [pn for pn in sig0["parts"] if sig0["parts"][pn] != sig1["parts"].get(pn)]
        rep = dict(types=bad_t[:20], parts=bad_p[:20],
                   sample={tn: dict(old=sig0["types"][tn], new=sig1["types"].get(tn)) for tn in bad_t[:3]},
                   max_release=(sig0["max_release"], sig1["max_release"]))
        Path(a.plan_out + ".wf_diff.json").write_text(json.dumps(rep, indent=1))
        raise SystemExit(f"die wavefront CHANGED: {len(bad_t)} types, {len(bad_p)} partitions (see .wf_diff.json)")
    report = {}
    for tn in tns:
        ch = fix_contract(P, tn, old[tn]["cc"])
        taps = TP.density_taps(P, tn)
        chain = chain_points(P, tn)
        tx = [(x, y) for _, x, y, _, _ in taps]
        report[tn] = dict(taps_old=len(old[tn]["taps"]), taps_new=len(taps), loads=[n for *_, n, _ in taps],
                          radius_max=max(r for *_, r in taps), chain_reach_max=round(max(min(man(p, q) for q in tx) for p in chain), 1),
                          rows=len(rows[tn]), contract=ch, depth=(old[tn]["depth"], RT.for_type(P, tn)["depth"]))
    # the plan file: every non-station byte unchanged; station types re-dumped in the compact form
    out = compact_plan.dumps(raw)
    Path(a.plan_out).write_text(out)
    back = json.loads(out)
    if back != json.loads(json.dumps(raw)):
        raise SystemExit("dump round trip mismatch")
    diff_types = [tn for tn in raw0["partition_types"] if raw0["partition_types"][tn] != back["partition_types"][tn]]
    if set(diff_types) - set(tns) or {k for k in raw0 if k != "partition_types" and raw0[k] != back[k]}:
        raise SystemExit("non-station content changed")
    if a.sidecar_in:
        sc = json.loads(Path(a.sidecar_in).read_text())
        bt = sc.get("collector", {}).get("types", {})
        for tn in tns:
            if tn in bt:
                lc = raw["partition_types"][tn]["clock"]["landing_contract"]
                bt[tn]["tree"] = lc["collector_tree"]
                bt[tn]["local_sources"] = lc["collector_local_sources"]
                bt[tn]["children"] = lc["collector_children"]
                if "collector_root_node" in bt[tn]:
                    bt[tn]["collector_root_node"] = lc["collector_root_node"]
        Path(a.sidecar_out).write_text(json.dumps(sc, separators=(",", ":")) + "\n")
    summ = dict(radius=a.radius, types=len(tns), taps_old=sum(r["taps_old"] for r in report.values()),
                taps_new=sum(r["taps_new"] for r in report.values()),
                load_max=max(max(r["loads"]) for r in report.values()),
                radius_max=max(r["radius_max"] for r in report.values()),
                chain_reach_max=max(r["chain_reach_max"] for r in report.values()),
                wavefront="UNCHANGED", seconds=round(time.time() - t0))
    if a.report:
        Path(a.report).write_text(json.dumps(dict(summary=summ, types=report), indent=1))
    print("OT_STATIONTAPS " + json.dumps(summ))


if __name__ == "__main__":
    main()
