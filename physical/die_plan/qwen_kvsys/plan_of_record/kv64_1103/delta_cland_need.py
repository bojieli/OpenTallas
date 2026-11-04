#!/usr/bin/env python3
"""DIE-KV-64 11-03 CLAND class fix: grow every KV ring band (ring_place all) that is smaller than its measured ring need.

Measured: the ring cells of 1,040 KV ring bands in the event28w_c kit netlists (1_synth_odb.v, intel1). Each cell's
reserved footprint is ceil(w/0.4/site) x row height, the landing_placement.tcl reserve. The need is linear in the bus
width: need_um2 <= 7.25*w + 125 for every measured band (w = 1 .. 1559; 130.9 .. 11388 um2).  Every OT_CLAND site
failure in the wave (io_cor_v1 ft19_i, hgi ft2_i, pv*) is a band with need/area > 1.  Many bands hold 0.67x their need;
those are the padded reserve.
Target area = 1.10 x model need (the cursor fill packed 98 % of a 1.03x-over band before it stopped).

Form per band, preferred first:
  (1) in-place grow: extend the current rect along x or y (one side or both) to the target area;
  (2) the planner's _storage_band search at that area (DIE-KV-32 resize form).
Every candidate must stay clear of the obstacles _storage_band uses: blockages, other bands, die islands, die clock
reserved sites, ft station sites, PHY supply regions, reset relay sites and start/status groups.  It must also keep the
17.28-um margin and the 405-um hop.  The 'spread' keys that _storage_band adds under _scale are dropped, so
landing_placement does not widen the footprint.
Bands with ring_place ff, monitor_ bands and multi-rect bands are unchanged.
Usage: PYTHONPATH=tools/die_plan python3 delta_cland_need.py PLAN SIDECAR OUT_PLAN REPORT [types-regex]
"""
import copy, json, re, sys
import clock_landing_plan as C, reset_tree as RT, schema as S, landing_place as LP

A, B, MARGIN, REACH = 7.25, 125.0, 17.28, 405 - 2.16
def need(w): return A * w + B
def ov(a, o): return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6
def area(r): return (r[2] - r[0]) * (r[3] - r[1])
def q(v, up): g = 0.54; return (-(-v // g) if up else v // g) * g

def obstacles(t, tn, plan_obj, side, lc, skip):
    ck = t.get("clock") or {}
    obs = [list(r) for r in RT.blockages(t)]
    obs += [list(r) for k, o in lc["bands"].items() if k != skip and o.get("rect_um") for r in (o.get("rects_um") or [o["rect_um"]])]
    obs += [list(r) for r in ck.get("die_islands_um", [])]
    obs += [list(r["rect_um"]) for r in ck.get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]
    for slot in t.get("ft_slots", []):
        cell = slot.get("bit_site_cell_um", [1.404, .27])
        for st in slot.get("bit_sites_um", []):
            if st: obs.append([min(p[0] for p in st) - cell[0] / 2, min(p[1] for p in st) - cell[1] / 2,
                               max(p[0] for p in st) + cell[0] / 2, max(p[1] for p in st) + cell[1] / 2])
        if not slot.get("bit_sites_um"): obs += [[x - 2.16, y - 2.16, x + 2.16, y + 2.16] for x, y in slot.get("regs_um", [])]
    obs += C.phy_supply_rects(plan_obj, tn) if plan_obj is not None else []
    obs += C.reset_site_rects(lc.get("collector_tree")) + C.reset_site_rects((side["collector"]["types"].get(tn) or {}).get("tree"))
    obs += [list(r) for _p, r, _t in LP._reader_start_groups(t) + LP._writer_start_groups(t) + LP._status_reset_groups(t)]
    obs += [list(r) for r in lc.get("group_rects_um", {}).values()]
    return obs

def hop(r, px, py): return max(abs(x - px) + abs(y - py) for x in (r[0], r[2]) for y in (r[1], r[3]))

def grow_in_place(r, tgt, w, h, obs, px, py):
    x0, y0, x1, y1 = r; cands = []
    dh = tgt / max(x1 - x0, 1e-9) - (y1 - y0); dw = tgt / max(y1 - y0, 1e-9) - (x1 - x0)
    for wid in (0, 0.54, 1.08, 2.16, 4.32):   # also try a slightly wider rect for each y grow
        ww = (x1 - x0) + wid; dhh = tgt / ww - (y1 - y0)
        for xs in ((x0, x1 + wid), (x0 - wid, x1)):
            for f in (0, 1, .5):
                cands.append([xs[0], q(y0 - dhh * f, False), xs[1], q(y1 + dhh * (1 - f), True)])
    for hid in (0, 0.54, 1.08, 2.16, 4.32):
        hh = (y1 - y0) + hid; dww = tgt / hh - (x1 - x0)
        for ys in ((y0, y1 + hid), (y0 - hid, y1)):
            for f in (0, 1, .5):
                cands.append([q(x0 - dww * f, False), ys[0], q(x1 + dww * (1 - f), True), ys[1]])
    ok = [c for c in cands if c[0] >= MARGIN and c[1] >= MARGIN and c[2] <= w - MARGIN and c[3] <= h - MARGIN
          and area(c) + 1e-6 >= tgt and hop(c, px, py) <= REACH and not any(ov(c, o) for o in obs)]
    return min(ok, key=lambda c: (area(c), hop(c, px, py))) if ok else None

def main(plan_p, side_p, out_p, rep_p, rx="^kv3_"):
    raw = json.load(open(plan_p)); side = json.load(open(side_p)); out = copy.deepcopy(raw)
    P = S.Plan(out) if (out.get("die") or {}).get("pg", {}).get("domains") and out.get("partitions") else None
    used_types = {p["type"] for p in out["partitions"]}
    rep = []; fails = []
    for tn in sorted(out["partition_types"]):
        if not re.search(rx, tn) or tn not in used_types: continue
        t = out["partition_types"][tn]; lc = ((t.get("clock") or {}).get("landing_contract") or {})
        bands = lc.get("bands") or {}
        if not bands: continue
        w, h = t["outline_um"]
        for bus in sorted(bands):
            b = bands[bus]
            if bus.startswith("monitor_") or not b.get("rect_um") or b.get("rects_um") or b.get("ring_place", "all") != "all": continue
            tgt = 1.10 * need(b["width"]); a0 = area(b["rect_um"])
            if a0 + 1e-6 >= tgt: continue
            try: px, py = C._bus_xy(t, bus)
            except Exception: px, py = [(b["rect_um"][0] + b["rect_um"][2]) / 2, (b["rect_um"][1] + b["rect_um"][3]) / 2]
            obs = obstacles(t, tn, P, side, lc, bus)
            nr = grow_in_place(b["rect_um"], tgt, w, h, obs, px, py); form = "in-place grow"
            if nr is None:
                saved = (C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING)
                try:
                    C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = "padded", 1.0, "all"
                    rw = 64 * -(-(b["width"] + 1) // 64); pad = (5 * rw * .2916 + 4 * rw * .0729 + 160 * .2916) / .40
                    tt = copy.deepcopy(t); tt["_cland_geom"] = copy.deepcopy(side["collector"]["types"][tn]["bus_geometry"])
                    used = [o for o in obs]
                    nb = C._storage_band(tt, bus, int(b["width"]), used, _scale=max(1.0, tgt / pad))
                    nr = nb["rect_um"]; form = "planner re-site (_storage_band at target area)"
                    if any(ov(nr, o) for o in obs): raise ValueError("re-site overlaps an obstacle")
                except Exception as e:
                    fails.append(dict(type=tn, bus=bus, area=round(a0, 1), target=round(tgt, 1), error=str(e)[:160])); continue
                finally:
                    C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = saved
            nb = dict(b); nb["resized_from_um"] = list(b["rect_um"]); nb["rect_um"] = [round(v, 4) for v in nr]
            nb["area_reserve_um2"] = round(tgt, 2)
            nb["resize"] = f"DIE-KV-64 11-03 CLAND measured ring need {need(b['width']):.1f} um2 (7.25*w+125) x1.10; {form}"
            bands[bus] = nb
            rep.append(dict(type=tn, bus=bus, width=b["width"], old_um2=round(a0, 1), new_um2=round(area(nr), 1),
                            form=form, rect_um=nb["rect_um"], hop_um=round(hop(nr, px, py), 1)))
    open(out_p, "w").write(json.dumps(out, indent=1) + "\n")
    json.dump(dict(resized=rep, failed=fails), open(rep_p, "w"), indent=1)
    from collections import Counter
    print("resized", len(rep), Counter(r["form"] for r in rep), "failed", len(fails))
    for f in fails[:20]: print("FAIL", f)

if __name__ == "__main__": main(*sys.argv[1:])
