#!/usr/bin/env python3
"""QC-S28-DIEVIEW (11-12): whole-die per-type audit of a QC plan, read-only.

    cd REPO && python3 -I qc_die_audit.py PLAN OUT_DIR --rs ROUTE_SUPPLY.tsv [--cells route_supply_cells.json]
                                          [--stages kit_wave_stages.tsv] [--jobs 8]

Per type (type frame, from the plan and the files it names; nothing is built):
  slot W x H, aspect (long/short), macro area/frac, soft area, cells (route_supply row) and an estimated cell area
  (measured synth um2/cell where route_supply_cells has it, else the die median um2/cell), soft fill = cell area /
  soft area, total fill = (cell area + macro area) / slot area;
  macro channels: for every pair of hard cores whose projections overlap, the street between them (V street = x gap,
  H street = y gap; only the nearest neighbour on each side counts) and the core-to-outline margins; min street;
  ft: slot count, bits, ft_track_frac; landing ring bands (count, area);
  clock taps: schema.tap_grid (the final taps), sinks = taps.sink_sites (bins file or planned sinks), split by
  taps.assign (the kit rule: nearest + cap moves within tap_radius_um); n taps, max sinks/tap, taps over cap, far um;
  hops > 405 um: every internal_stations segment (from -> regs -> to) and every ft slot station-to-station segment
  (regs_um chain, Manhattan); max hop;
  content-natural outline: soft area needed at target util (0.55) + macro area + 15 % channel/ring allowance;
  route_supply p99 / worst region; kit-wave latest status/class and the FAIL count.
Writes OUT_DIR/audit.json (with die-frame geometry for the renderer) and OUT_DIR/audit.tsv."""
import csv
import json
import math
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path("tools/die_plan").resolve()))
import schema  # noqa: E402
import taps as TP  # noqa: E402

REACH = 405.0
UTIL_T = 0.55
P = None


def _load(path):
    global P
    if P is None:
        P = schema.Plan(json.loads(Path(path).read_text()), path)
    return P


def rects(t):
    out = []
    for h in t.get("hard_cores", []) or []:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((h["inst"], x, y, x + w, y + hh, h.get("module", "")))
    return out


def channels(R, W, H):
    v, h = [], []   # (gap, a, b)
    for i, a in enumerate(R):
        best = {}
        for j, b in enumerate(R):
            if i == j:
                continue
            yo = min(a[4], b[4]) - max(a[2], b[2])
            xo = min(a[3], b[3]) - max(a[1], b[1])
            if yo > 1.0 and b[1] >= a[3] - 1e-6:          # b east of a
                g = b[1] - a[3]
                if g < best.get("E", (1e9,))[0]:
                    best["E"] = (g, a[0], b[0], (a[3], max(a[2], b[2]), b[1], min(a[4], b[4])))
            if xo > 1.0 and b[2] >= a[4] - 1e-6:          # b north of a
                g = b[2] - a[4]
                if g < best.get("N", (1e9,))[0]:
                    best["N"] = (g, a[0], b[0], (max(a[1], b[1]), a[4], min(a[3], b[3]), b[2]))
        if "E" in best:
            v.append(best["E"])
        if "N" in best:
            h.append(best["N"])
    return v, h


def seg_hops(pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        d = abs(a[0] - b[0]) + abs(a[1] - b[1])
        out.append((d, a, b))
    return out


def one(args):
    plan_path, tn, rs, cellmap, um2_med = args
    P = _load(plan_path)
    t = P.types[tn]
    W, H = t["outline_um"]
    R = rects(t)
    macro = sum((r[3] - r[1]) * (r[4] - r[2]) for r in R)
    soft = W * H - macro
    row = rs.get(tn, {})
    cells = float(row.get("cells") or 0) or float(t.get("cells") or 0)
    meas = cellmap.get(tn)
    um2 = (meas["synth_area_um2"] / meas["cells"]) if meas and meas.get("synth_area_um2") and meas.get("cells") else um2_med
    carea = cells * um2
    r = dict(type=tn, W=W, H=H, aspect=round(max(W, H) / max(1e-9, min(W, H)), 2), area_mm2=round(W * H / 1e6, 4),
             n_cores=len(R), macro_um2=round(macro), macro_frac=round(macro / (W * H), 3), cells=int(cells),
             um2_per_cell=round(um2, 4), cell_um2=round(carea), soft_fill=round(carea / soft, 3) if soft > 0 else None,
             total_fill=round((carea + macro) / (W * H), 3))
    # content-natural outline
    need = carea / UTIL_T + macro
    ft = t.get("ft_slots", []) or []
    bands = (t.get("clock", {}).get("landing_contract", {}) or {}).get("bands", {}) or {}
    band_area = sum((b["rect_um"][2] - b["rect_um"][0]) * (b["rect_um"][3] - b["rect_um"][1]) for b in bands.values()
                    if b.get("rect_um"))
    need = need * 1.15 + band_area
    r["natural_mm2"] = round(need / 1e6, 4)
    r["slot_over_natural"] = round(W * H / need, 2) if need > 0 else None
    # channels
    v, h = channels(R, W, H)
    r["min_street_V"] = round(min((g for g, *_ in v), default=float("nan")), 2) if v else None
    r["min_street_H"] = round(min((g for g, *_ in h), default=float("nan")), 2) if h else None
    r["streets_lt20"] = sum(1 for g, *_ in v + h if g < 20)
    # ft
    r["ft_slots"] = len(ft)
    r["ft_bits"] = sum(int(s.get("width", 0)) for s in ft)
    r["ft_track_frac"] = t.get("ft_track_frac")
    r["ring_bands"] = len(bands)
    r["ring_band_um2"] = round(band_area)
    # taps
    ck = t.get("clock", {})
    cap = int(ck.get("tap_max_sinks", 1200))
    rad = float(ck.get("tap_radius_um", 200.0))
    tap_rows, loads, far = [], [], []
    try:
        grid = schema.tap_grid(P, tn)
        sinks = TP.sink_sites(P, tn)
        if grid and sinks:
            load, farv, _ = TP.assign([(n, x, y) for n, x, y in grid], sinks, cap, rad, max_distance_um=rad)
            loads, far = load, farv
        tap_rows = [dict(name=n, x=x, y=y, sinks=round(loads[i]) if loads else None,
                         far=round(far[i], 1) if far else None) for i, (n, x, y) in enumerate(grid)]
        r["real_sinks"] = round(sum(p[2] for p in sinks))
        r["sink_src"] = "bins" if ck.get("sink_bins_file") else "planned"
    except Exception as e:  # noqa: BLE001
        r["tap_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    r["tap_mode"] = ck.get("tap_mode", "-")
    r["taps"] = len(tap_rows)
    r["max_sinks_tap"] = max((x["sinks"] or 0 for x in tap_rows), default=0)
    r["taps_over_cap"] = sum(1 for x in tap_rows if (x["sinks"] or 0) > cap)
    r["tap_cap"] = cap
    r["max_tap_far_um"] = max((x["far"] or 0 for x in tap_rows), default=0)
    r["edge_clocks"] = len(ck.get("edge_clocks", []) or [])
    # hops
    hops = []
    for s in t.get("internal_stations", []) or []:
        pts = [tuple(s["from_um"])] + [tuple(p) for p in s.get("regs_um", [])] + [tuple(s["to_um"])]
        for d, a, b in seg_hops(pts):
            hops.append(dict(kind="istn", name=s.get("conn"), bits=s.get("bits"), d=round(d, 1), a=a, b=b))
    for s in ft:
        regs = [tuple(p) for p in s.get("regs_um", [])]
        for d, a, b in seg_hops(regs):
            hops.append(dict(kind="ft", name=s.get("name"), bits=s.get("width"), d=round(d, 1), a=a, b=b))
    # stale station ends (DIE-QC-99 11-12, QC-S28-C y_o21 finding): an internal_station whose launch/capture names a
    # hard core must start/end on (within 25 um of) that core's CURRENT rect; a 'face flop' end must sit on the outline
    rb = {a[0]: a[1:5] for a in R}
    stale = []

    def _dist_rect(p, q):
        dx = max(q[0] - p[0], 0, p[0] - q[2])
        dy = max(q[1] - p[1], 0, p[1] - q[3])
        return dx + dy

    for s in t.get("internal_stations", []) or []:
        for end, key in (("from_um", "launch"), ("to_um", "capture")):
            nm = str(s.get(key, "") or "")
            p = s.get(end)
            if not p:
                continue
            inst = nm.split(".")[0]
            if inst in rb:
                d = _dist_rect(p, rb[inst])
                if d > 25:
                    stale.append(dict(conn=s.get("conn"), end=end, ref=nm, d=round(d, 1), at=p))
            elif "face" in nm:
                d = min(p[0], W - p[0], p[1], H - p[1])
                if d > 25:
                    stale.append(dict(conn=s.get("conn"), end=end, ref=nm, d=round(d, 1), at=p))
    # unregistered face legs (GEOM-VIS-2 11-12 cbx bc legs): a bus whose leaf is a hard core or a placed content
    # block with no internal_station: face window centre -> leaf block (Manhattan) > 405 um
    blk = dict(rb)
    for c in t.get("contents", []) or []:
        if c.get("origin_um") and c.get("outline_um"):
            (x, y), (w, hh) = c["origin_um"], c["outline_um"]
            blk.setdefault(c["inst"], (x, y, x + w, y + hh))
    istn = {str(s.get("conn", "")) for s in t.get("internal_stations", []) or []}
    legs = []
    for b in t.get("buses", []) or []:
        inst = str(b.get("leaf", "")).split(".")[0]
        if inst not in blk or f"bus:{b['name']}" in istn or not b.get("window_um"):
            continue
        m = sum(b["window_um"]) / 2
        p = {"N": (m, H), "S": (m, 0), "E": (W, m), "W": (0, m)}[b["face"]]
        d = _dist_rect(p, blk[inst])
        if d > REACH:
            q = blk[inst]
            legs.append(dict(kind="leg", name=b["name"], bits=b.get("width"), d=round(d, 1), a=p,
                             b=(min(max(p[0], q[0]), q[2]), min(max(p[1], q[1]), q[3]))))
    hops += legs
    r["legs_gt405"] = len(legs)
    r["stale_station_ends"] = len(stale)
    r["stale_gt60"] = sum(1 for x in stale if x["d"] > 60)
    r["stale_detail"] = ";".join(f"{x['conn']}.{x['end']}->{x['ref']}@{x['d']}" for x in stale)[:300]
    over = [x for x in hops if x["d"] > REACH]
    r["hops"] = len(hops)
    r["hops_gt405"] = len(over)
    r["max_hop_um"] = max((x["d"] for x in hops), default=0)
    r["route_p99"] = row.get("p99_ratio")
    r["route_region"] = f"{row.get('worst_region', '')}_{row.get('dir', '')}" if row else None
    r["route_verdict"] = row.get("verdict")
    r["route_flags"] = row.get("flag_regions")
    r["route_fix"] = row.get("fix")
    geom = dict(cores=[dict(inst=a[0], module=a[5], r=a[1:5]) for a in R],
                streets=[dict(g=round(g, 1), a=a, b=b, r=rr, dir="V") for g, a, b, rr in v] +
                        [dict(g=round(g, 1), a=a, b=b, r=rr, dir="H") for g, a, b, rr in h],
                bands=[dict(name=k, r=b["rect_um"]) for k, b in bands.items() if b.get("rect_um")],
                taps=tap_rows, over=over, stale=[x for x in stale if x['d'] > 60],
                ft=[dict(name=s.get("name"), w=s.get("width"), regs=s.get("regs_um", [])) for s in ft])
    return r, geom


def main():
    a = sys.argv[1:]
    plan, out = a[0], Path(a[1])
    opt = {a[i]: a[i + 1] for i in range(2, len(a) - 1) if a[i].startswith("--")}
    out.mkdir(parents=True, exist_ok=True)
    rs = {}
    if opt.get("--rs"):
        with open(opt["--rs"]) as f:
            for row in csv.DictReader((ln for ln in f if not ln.startswith("#")), delimiter="\t"):
                rs[row["type"]] = row
    cellmap = {}
    if opt.get("--cells"):
        cellmap = json.loads(Path(opt["--cells"]).read_text()).get("qwen_compute", {})
    ratios = [v["synth_area_um2"] / v["cells"] for v in cellmap.values() if v.get("synth_area_um2") and v.get("cells")]
    um2_med = statistics.median(ratios) if ratios else 0.12
    raw = json.loads(Path(plan).read_text())
    types = sorted(raw["partition_types"])
    jobs = int(opt.get("--jobs", 8))
    with ProcessPoolExecutor(jobs) as ex:
        res = list(ex.map(one, [(plan, tn, rs, cellmap, um2_med) for tn in types], chunksize=2))
    rows = {r["type"]: r for r, _ in res}
    geom = {r["type"]: g for r, g in res}
    parts = [dict(name=p["name"], type=p["type"], origin=p["origin_um"], orient=p.get("orient", "R0"))
             for p in raw["partitions"]]
    cnt = {}
    for p in parts:
        cnt[p["type"]] = cnt.get(p["type"], 0) + 1
    for tn in rows:
        rows[tn]["instances"] = cnt.get(tn, 0)
    stages = {}
    if opt.get("--stages"):
        with open(opt["--stages"]) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["die"] != "qwen_compute":
                    continue
                it = row["item"]
                stages.setdefault(it, []).append(row)
    for tn, r in rows.items():
        st = sorted(stages.get(tn, []), key=lambda x: x.get("updated", ""))
        r["kw_rows"] = len(st)
        r["kw_fail"] = sum(1 for x in st if x["status"].startswith("FAIL"))
        r["kw_last"] = f"{st[-1]['stage']}/{st[-1]['status']}/{st[-1]['class']}" if st else "-"
        r["kw_last_reason"] = (st[-1].get("reason", "") or "")[:160] if st else ""
    # types without a cell count (route_supply had no measured / estimated cells): estimate cells from the register
    # inventory (real_sinks, the bins file of a placed netlist) x the die median cells-per-register of the types that
    # have both; flagged fill_src=est
    kk = [r["cells"] / r["real_sinks"] for r in rows.values()
          if r.get("cells") and r.get("real_sinks") and r.get("sink_src") == "bins"]
    k = statistics.median(kk) if kk else 6.0
    for r in rows.values():
        r["fill_src"] = "cells" if r.get("cells") else "est"
        if not r.get("cells") and r.get("real_sinks"):
            soft = r["W"] * r["H"] - r["macro_um2"]
            ca = r["real_sinks"] * k * um2_med
            r["fill_est"] = round(ca / soft, 3) if soft > 0 else None
            r["fill_est_total"] = round((ca + r["macro_um2"]) / (r["W"] * r["H"]), 3)
            need = (ca / UTIL_T + r["macro_um2"]) * 1.15 + r["ring_band_um2"]
            r["natural_mm2"] = round(need / 1e6, 4)
            r["slot_over_natural"] = round(r["W"] * r["H"] / need, 2)
        else:
            r["fill_est"] = r["soft_fill"]
            r["fill_est_total"] = r["total_fill"]
    doc = dict(plan=plan, die=raw["die"]["outline_um"], cells_per_reg=k, um2_per_cell_median=um2_med, rows=rows, geom=geom, parts=parts,
               die_channels=raw["die"].get("channels", []))
    (out / "audit.json").write_text(json.dumps(doc) + "\n")
    cols = ["type", "instances", "W", "H", "aspect", "area_mm2", "n_cores", "macro_frac", "cells", "fill_src", "fill_est", "fill_est_total", "soft_fill",
            "total_fill", "natural_mm2", "slot_over_natural", "min_street_V", "min_street_H", "streets_lt20", "ft_slots",
            "ft_bits", "ft_track_frac", "ring_bands", "ring_band_um2", "tap_mode", "taps", "max_sinks_tap", "tap_cap",
            "taps_over_cap", "max_tap_far_um", "real_sinks", "sink_src", "edge_clocks", "hops", "hops_gt405",
            "max_hop_um", "legs_gt405", "stale_station_ends", "stale_gt60", "stale_detail", "route_p99", "route_region", "route_verdict", "route_flags", "kw_rows", "kw_fail", "kw_last",
            "kw_last_reason", "tap_error"]
    with open(out / "audit.tsv", "w") as f:
        f.write("\t".join(cols) + "\n")
        for tn in types:
            f.write("\t".join("" if rows[tn].get(c) is None else str(rows[tn].get(c)) for c in cols) + "\n")
    print(f"{len(rows)} types -> {out}/audit.tsv")


if __name__ == "__main__":
    main()
