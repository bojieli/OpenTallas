#!/usr/bin/env python3
"""FALLBACK-HEAD (OWNER 10-26 16:5x, IF.FALLBACK): bottom-up landed fallback plan for the s81_head die.

Every clock region closes its own local tree; every inter-region plan port is a LANDED crossing (registered both
sides, forwarded-clock ring write, local-clock read, fixed static latency, no credits: ot_dp_clk_landing, the proved
nominal +3 data-cycle contract of clock_landings.network_lane_cycles).  Existing hard cores are reused unchanged.

    fallback_land.py plan  PLAN --out DIR [--granularity part|rowpair] [--observer ctl]
        DIR/regions_<g>.json     region table in the exact clock_landings / clock_landing_plan input format
        DIR/summary_<g>.json     crossings, bits, lane deltas, head-pass critical seams, ring area bound
    fallback_land.py compose PLAN --table DIR/regions_part.json --out DIR
        runs the EXISTING tools (clock_landings.requirements, clock_landing_plan.compose, landing_contract.check,
        schema.Plan) on the table: DIR/landed_plan.json + DIR/landed_sidecar.json + DIR/compose_report.json

No canonical plan is edited.  Numbers are plan-level (UNCHECKED until NUMBER-CHECK) and say nothing about routed
timing: ring-window STA and die GRT on real views remain the freeze gate (METHODOLOGY 12.4a).
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))

CYC = 3                       # proved nominal contract: ring OFFSET 2 + RDREG 1 (clock_landings.network_lane_cycles)
UM2_PER_BIT = 4.66            # QC qc_cross basis (6.79 M FF / 5.874 mm2 / 1.26 M bits), logical, UNMAPPED
FF_UM2 = 0.2916               # ASAP7 DFFHQNx1 (clock_landing_plan._storage_band basis)


def load(p):
    return json.loads(Path(p).read_text())


def part_boxes(plan):
    T = plan["partition_types"]
    out = {}
    for p in plan["partitions"]:
        w, h = T[p["type"]]["outline_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        x, y = p["origin_um"]
        out[p["name"]] = [x, y, x + w, y + h]
    return out


def region_of(plan, gran):
    """{part: tag}.  part = one region per partition (each partition closes its own CTS tree from its single entry;
    no die-level related pair crosses a partition boundary).  rowpair = W/E half row-pair chain (tiles + turns) as
    one region, every spine node / band partition its own region (comparison only: inter-tile pairs stay related)."""
    if gran == "part":
        return {p["name"]: p["name"] for p in plan["partitions"]}
    if gran.startswith("map:"):     # DIE-HEAD 10-27 (12.13a): any {part: region} map (locality / feed-following), opt-in
        m = load(gran[4:])
        m = m.get("part_region", m)
        miss = [p["name"] for p in plan["partitions"] if p["name"] not in m]
        if miss:
            raise SystemExit(f"region map misses {len(miss)} partitions: {miss[:5]}")
        return {p["name"]: m[p["name"]] for p in plan["partitions"]}
    reg = {}
    for p in plan["partitions"]:
        n = p["name"]
        m = re.match(r"^t([WE])(\d+)[ob]\d+$", n) or re.match(r"^turn([WE])(\d+)[ab]$", n)
        reg[n] = f"ch{m.group(1)}{m.group(2)}" if m else n
    return reg


def table(plan, gran):
    B = part_boxes(plan)
    reg = region_of(plan, gran)
    lane_of = {pid: ln["id"] for ln in plan["lanes"] for pid in ln["ports"]}
    regions = collections.defaultdict(list)
    for pn, tag in reg.items():
        regions[tag].append(pn)
    rows = []
    for tag, parts in sorted(regions.items()):
        bs = [B[p] for p in parts]
        rows.append(dict(tag=tag, box_um=[min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs),
                                          max(b[3] for b in bs)], parts=len(parts)))
    # region boxes must hold exactly their own partitions' centres (clock_landings uses centre-in-box)
    for p, b in B.items():
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        hit = [r["tag"] for r in rows if r["box_um"][0] <= cx < r["box_um"][2] and r["box_um"][1] <= cy < r["box_um"][3]]
        if hit != [reg[p]]:
            raise SystemExit(f"region box overlap/miss for {p}: {hit}")
    ports = []
    for pr in plan["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if "@" in (a[:1] + b[:1]) or reg[a] == reg[b]:
            continue
        ports.append(dict(port=pr["id"], lane=lane_of.get(pr["id"]), src=a, dst=b, src_region=reg[a],
                          dst_region=reg[b], width=int(pr["width"]), kind=pr.get("kind", "data"), added_cycles=CYC))
    return dict(schema="opentallas.fallback_head_regions.v1", granularity=gran, added_cycles_per_crossing=CYC,
                regions=rows, ports=ports)


def head_pass(plan, tab):
    """Serial landed crossings of one lm_head pass: ctl -> spine down to row-pair k -> W/E chain -> spine up -> ctl
    (max over k and halves), plus the TP4 rank all-gather legs (m*/coll lanes) reported separately."""
    landed = collections.Counter(r["lane"] for r in tab["ports"])
    # added cycles per lane: +CYC per crossing (old ring), or the count-aligned per-crossing schedule latency
    # (count_align_bind.annotate_table sets r["added_cycles"]; MESO-INTEG-1)
    cyc = collections.Counter()
    for r in tab["ports"]:
        cyc[r["lane"]] += int(r.get("added_cycles", CYC))
    lanes = {ln["id"]: ln for ln in plan["lanes"]}
    nsp = len([l for l in lanes if re.match(r"^sp_x\d+$", l)])
    best = (0, None, 0)
    for k in range(nsp):
        for h in "WE":
            ch = [l for l in lanes if l.startswith(f"ch{h}{k}_")]
            if not ch:
                continue
            down = sum(landed[f"sp_x{i}"] for i in range(k + 1))
            up = sum(landed[f"sp_b{i}"] for i in range(k + 1))
            n = down + sum(landed[l] for l in ch) + up
            c = (sum(cyc[f"sp_x{i}"] + cyc[f"sp_b{i}"] for i in range(k + 1)) + sum(cyc[l] for l in ch))
            if (c, n) > (best[2], best[0]):
                best = (n, dict(rowpair=k, half=h, spine_down=down, chain=sum(landed[l] for l in ch), spine_up=up,
                                chain_lanes=len(ch)), c)
    gather = {l: landed[l] for l in lanes if re.match(r"^(m\d[SN]_|coll_|kd|ku|unit_lep|ctrl_lep|lepf)", l) and landed[l]}
    worst_leg = max(gather.values()) if gather else 0
    gcyc = {l: cyc[l] for l in gather}
    # round trip = the worst one-way leg (by added cycles) twice: tx and rx legs are separate lanes of equal depth
    worst_leg_cyc = max(gcyc.values()) if gcyc else 0
    return dict(head_pass_crossings=best[0], path=best[1], added_cycles=best[2],
                gather_lanes=gather, gather_worst_one_way_crossings=worst_leg,
                gather_round_trip_added_cycles=2 * worst_leg_cyc,
                total_added_cycles_per_head_pass=best[2] + 2 * worst_leg_cyc,
                count_aligned=any("added_cycles" in r and r["added_cycles"] != CYC for r in tab["ports"]))


def summary(plan, tab):
    bits = sum(r["width"] for r in tab["ports"])
    lane_add = collections.Counter()
    for r in tab["ports"]:
        lane_add[r["lane"]] += CYC
    live_ff = sum(5 * (r["width"] + 1) for r in tab["ports"])
    ctl_ff = sum(73 + 4 * ((r["width"] + 64) // 64) for r in tab["ports"])
    die_um2 = plan["die"]["outline_um"][0] * plan["die"]["outline_um"][1]
    ring_um2 = bits * UM2_PER_BIT
    return dict(granularity=tab["granularity"], regions=len(tab["regions"]), crossings=len(tab["ports"]),
                plan_ports=len(plan["ports"]), bits=bits, lanes_touched=len(lane_add),
                lane_added_cycles_hist=dict(sorted(collections.Counter(lane_add.values()).items())),
                ring_live_ff=live_ff, ring_ctl_ff_upper=ctl_ff,
                ring_area_mm2_basis_4p66=round(ring_um2 / 1e6, 3),
                ring_area_mm2_ff_only=round((live_ff + ctl_ff) * FF_UM2 / 1e6, 3),
                ring_area_pct_die=round(100 * ring_um2 / die_um2, 3),
                head_pass=head_pass(plan, tab),
                labels="UNCHECKED plan-level; area logical UNMAPPED; no routed timing")


def cmd_plan(a):
    plan = load(a.plan)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for g in a.granularity:
        tab = table(plan, g)
        if g.startswith("map:"):
            g = tab["granularity"] = "map"
        (out / f"regions_{g}.json").write_text(json.dumps(tab, indent=1) + "\n")
        s = summary(plan, tab)
        (out / f"summary_{g}.json").write_text(json.dumps(s, indent=1) + "\n")
        res[g] = s
    print(json.dumps(res, indent=1))
    return 0


def cmd_compose(a):
    import clock_landings as CL
    import clock_landing_plan as CLP
    import landing_contract as LC
    import schema as S
    plan = load(a.plan)
    tab = load(a.table)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = dict(table=a.table, granularity=tab.get("granularity"))
    req = CL.requirements(plan, tab)
    (out / "requirements.json").write_text(json.dumps(req, indent=1) + "\n")
    rep["requirements"] = {k: req[k] for k in ("crossings", "required_new_scalar_pins", "added_live_data_storage_flops",
                                                "type_count_before", "type_count_after")}
    rep["requirements"]["split_types"] = sorted(req["split_types"])
    observer = load(a.observer_spec) if a.observer_spec else None
    if observer:
        required = ("module", "instance_suffix", "fault_port", "ready_port")
        missing = [k for k in required if not observer.get(k) or observer[k] == "OPEN"]
        if missing:
            raise ValueError("explicit observer spec missing actual binding: " + repr(missing))
        observer = {k: observer[k] for k in required}
    try:
        raw, side = CLP.compose(plan, tab, a.plan, observer_part=a.observer,
                               observer=observer, monitor=a.monitor, band_reserve=a.band_reserve,
                               band_spread=a.band_spread, band_ring=a.band_ring)
    except Exception as e:  # report the exact first blocker; do not invent geometry
        rep["compose"] = dict(status="FAIL", error=f"{type(e).__name__}: {e}")
        (out / "compose_report.json").write_text(json.dumps(rep, indent=1) + "\n")
        print(json.dumps(rep, indent=1))
        return 1
    # Historical plans keep an explicit OPEN observer. A current provider can
    # declare its actual one-bit inputs; clock_landings validates that binding
    # against the emitted native body before it can instantiate any ring.
    obs = dict(part=a.observer, **observer) if observer else dict(part=a.observer, module=plan["partition_types"][next(p["type"] for p in plan["partitions"]
                                                                    if p["name"] == a.observer)]["module"],
               instance_suffix="OPEN", fault_port="OPEN", ready_port="OPEN")
    side["collector"]["observer"] = obs
    raw["clock"]["landing_network"]["root_observer"] = obs
    from head_source_delta import rebase_pin_assets
    rep['plan_relative_pin_assets'] = rebase_pin_assets(raw, Path(a.plan), out / 'landed_plan.json', ROOT)
    (out / "landed_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    (out / "landed_sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
    P = S.Plan(raw, str(out / "landed_plan.json"))
    lc = LC.check(P, sidecar=side)
    nl = CL.network_lane_cycles(raw)
    pf = side["collector"]["placement_failures"]
    # DIE-HEAD-21 (COORD 10-28 22:37): fail-closed -- any landing-contract error (after the declared START tree is
    # proved) is a FAIL verdict and a non-zero exit, never "OK" with errors
    rep["compose"] = dict(status="FAIL" if lc["errors"] else "OK", types_before=len(plan["partition_types"]), types_after=len(raw["partition_types"]),
                          new_ports=len(raw["ports"]) - len(plan["ports"]),
                          infra_edges=len(raw["clock"]["landing_network"]["edges"]),
                          placement_failures=len(pf), placement_failures_by_type=dict(collections.Counter(f["type"] for f in pf)),
                          boot_ready_max_cycles=side["collector"]["boot_budget"]["ready_at_glue_max_cycles"],
                          monitor_max_die_hop_um=side["collector"]["max_die_hop_um"],
                          landing_contract=dict(errors=len(lc["errors"]), first_errors=lc["errors"][:12], pins=lc["pins"],
                                                edges=lc["edges"], max_hop_um=round(lc["max_hop_um"], 3)),
                          network_lane_cycles=dict(lanes=len(nl), total=sum(nl.values())),
                          observer=obs)
    if "start_tree" in lc:
        rep["compose"]["landing_contract"]["start_tree"] = lc["start_tree"]
    if lc["errors"]:
        rep["compose"]["error"] = f"landing_contract: {len(lc['errors'])} error(s), first: {lc['errors'][0]}"
    (out / "compose_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    return 1 if lc["errors"] else 0


def phy_rect_type_frame(plan, tn):
    """VDDPHY domain rect of a type in its own frame (first instance; all instances share it), or None."""
    doms = plan["die"].get("pg", {}).get("domains", [])
    T = plan["partition_types"][tn]
    w, h = T["outline_um"]
    for p in plan["partitions"]:
        if p["type"] != tn:
            continue
        for d in doms:
            if any(io.startswith("io_" + p["name"] + "_") for io in d.get("io", [])):
                x0, y0, x1, y1 = d["rect_um"]
                ox, oy = p["origin_um"]
                r = [x0 - ox, y0 - oy, x1 - ox, y1 - oy]
                o = p.get("orient", "R0")
                if o in ("MY", "R180"):
                    r[0], r[2] = w - r[2], w - r[0]
                if o in ("MX", "R180"):
                    r[1], r[3] = h - r[3], h - r[1]
                return [max(0.0, r[0]), max(0.0, r[1]), min(w, r[2]), min(h, r[3])]
        return None
    return None


def cmd_variant(a):
    """Die-clock variant FB1 for the die GRT incl. clock: ONE clock entry (region root) per partition, at the type's
    declared clock.tap_um (else its centre); grid/density/sink/CP2-early core taps removed, because under the fallback
    each partition's own CTS tree distributes from that entry to every sink (hard-core pins included).  Nothing
    else in the plan changes (outlines, ports, lanes, PG, reset are byte-identical)."""
    plan = load(a.plan)
    plan["budgets"]["tap_pitch_um"] = 1.0e5          # every type fits one R4 cell -> it keeps clock.tap_um
    rows = {}
    for tn, t in plan["partition_types"].items():
        ck = t.setdefault("clock", {})
        w, h = t["outline_um"]
        xy = ck.get("tap_um") if isinstance(ck.get("tap_um"), list) and len(ck["tap_um"]) == 2 else [w / 2, h / 2]
        phy = phy_rect_type_frame(plan, tn)
        if phy and phy[0] <= xy[0] <= phy[2] and phy[1] <= xy[1] <= phy[3]:
            # entry inside the VDDPHY domain (no core rows): move it to the middle of the digital strip
            lo, hi = (0.0, phy[1]) if phy[1] > 0 else (phy[3], h)
            xy = [xy[0], round(round((lo + hi) / 2 / 8.64) * 8.64, 3)]
        gone = [k for k in ("taps", "core_taps", "tap_mode", "sink_sites_um") if k in ck]
        for k in gone:
            ck.pop(k)
        ck["tap_um"] = [float(xy[0]), float(xy[1])]
        ck["note"] = "FALLBACK-HEAD FB1: single region-root entry; partition-local CTS to all sinks; landed seams"
        rows[tn] = dict(tap_um=ck["tap_um"], removed=gone)
    plan["note"] = plan.get("note", "") + " | FALLBACK-HEAD FB1 die-clock variant (one entry per partition), NOT canonical"
    Path(a.out).write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps(rows, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--granularity", action="append", help="part | rowpair | map:REGION_MAP.json ({part: region} or part_region; DIE-HEAD opt-in)")
    c = sub.add_parser("compose")
    c.add_argument("plan")
    c.add_argument("--table", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--observer", default="ctl")
    c.add_argument("--observer-spec", help="JSON actual {module,instance_suffix,fault_port,ready_port}; binding is checked by clock_landings, default stays OPEN")
    c.add_argument("--band-spread", type=float, default=1.0,
                   help="ring_ff only: band area = spread x reserve, ring spread over the whole band (DIE-HEAD-12; 2.0 = ~0.5 density)")
    c.add_argument("--band-ring", default="all", choices=["all", "ff"],
                   help="ring_ff only: ff = place only the ring flops FIRM in bit-major order, ring logic to GPL (DIE-HEAD-13)")
    c.add_argument("--band-reserve", default="padded", choices=["padded", "live", "ring_ff"],
                   help="storage band size: padded (default), live, ring_ff (DIE-HEAD-11: ring flop count x mapped footprint)")
    c.add_argument("--monitor", default="reset", choices=["reset", "dataflow", "region"], help="monitor network: reset-wavefront cohorts (default), uniform dataflow (no type split) or region (dataflow walk incl. same-region links; landed-mask type split)")
    v = sub.add_parser("variant")
    v.add_argument("plan")
    v.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "plan" and not a.granularity:
        a.granularity = ["part", "rowpair"]
    return dict(plan=cmd_plan, compose=cmd_compose, variant=cmd_variant)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
