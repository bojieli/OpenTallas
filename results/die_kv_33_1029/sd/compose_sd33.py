#!/usr/bin/env python3
"""DIE-KV-33-SD 10-29 fix-only plan delta: re-compose kv3_sys_SD/_v1 reset local taps + landing storage bands around the
x6 SerDes PHY macro (no new gates; existing tools only).

Root cause (DIE-KV-32-KITS 12:33): the event26 compose placed all 12 sys_SD reset local_taps_um and both landing bands
inside the PHY abstract (composed without the macro), so reset_tree.consumer_taps fails closed ("local reset tap ... is
blocked") once the macro is in the plan.

Steps (all existing code paths):
 1. results/die_kv_32_1029/serdes/apply_serdes_phys.py with the event33 delta (abstract 1848.96 x 972, views
    results/kv_serdes_pg_event33, VDDPHY_SW/SE rects = the new content outline in die coordinates).
 2. every ring band of the two types re-composed by clock_landing_plan._storage_band in ring_ff mode (DIE-HEAD-11
    reserve, 405-um reach, macro/island/other-band free) -- the same call resize_undersized_bands makes, applied to every
    band because the old rects overlap the macro.
 3. reset.local_taps_um re-composed by s81_head/head_reset_local_taps.cover_sites (every free point within 300 um of a
    local site; the macro is a blockage via reset_tree.blockages), 4.32-um site grid (the rims are 8.64-12.96 um wide),
    landing bands excluded as sites (site_excl) so no relay is planned inside a FIRM ring band.
 4. the same reset.local_taps_um written into the bind plan (bound RTL relay tree must match the kit plan).
Fails closed if a band or the cover does not fit, if reset_tree.for_type fails, or if the type reset depth changes.

  compose_sd33.py REPO GEN_PLAN_IN BIND_PLAN_IN SIDECAR DELTA OUT_DIR
"""
import copy, json, subprocess, sys
from pathlib import Path

repo, gen_in, bind_in, sidecar, delta_p, out = sys.argv[1:7]
out = Path(out); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, f"{repo}/tools/die_plan"); sys.path.insert(0, f"{repo}/tools/s81_head")
import schema as S, reset_tree as RT, clock_landing_plan as CL, head_reset_local_taps as H  # noqa: E402

TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
phys = out / "plan_phys.json"
r = subprocess.run([sys.executable, f"{repo}/results/die_kv_32_1029/serdes/apply_serdes_phys.py", f"{repo}/tools/die_plan",
                    gen_in, delta_p, str(phys)], capture_output=True, text=True)
print("apply_serdes_phys", r.returncode, r.stdout.strip()[:400], r.stderr.strip()[-400:])
assert r.returncode == 0
gen = json.load(open(phys)); sc = json.load(open(sidecar)); rep = dict(types={})
base_depth = {}
for tn in TYPES:
    t = gen["partition_types"][tn]; w, h = t["outline_um"]
    tt = copy.deepcopy(t); tt["_cland_geom"] = copy.deepcopy(sc["collector"]["types"][tn]["bus_geometry"])
    saved = (CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING)
    CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING = "ring_ff", 1.0, "all"
    bands = t["clock"]["landing_contract"]["bands"]; used = []; rb = []
    try:
        for bus in sorted(bands):
            b = bands[bus]
            if bus.startswith("monitor_") or not b.get("rect_um"):
                continue
            nb = CL._storage_band(tt, bus, int(b["width"]), used)
            nb.update(instance=b.get("instance", "u_cland_" + bus), resized_from_um=list(b["rect_um"]),
                      resize="DIE-KV-33-SD re-composed with the PHY macro as a blockage (ring_ff reserve)")
            used.append(nb["rect_um"]); bands[bus] = nb
            x0, y0, x1, y1 = nb["rect_um"]
            rb.append(dict(bus=bus, old=b["rect_um"], new=nb["rect_um"], area=round((x1-x0)*(y1-y0), 1),
                           reserve=nb["area_reserve_um2"], hop=nb["max_pin_to_band_hop_um"]))
    finally:
        CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING = saved
    blk = RT.blockages(t)
    sites, worst, npts = H.cover_sites(w, h, blk, RT.CLEAR_UM, 300.0, g=4.32, site_excl=used)
    old = t["reset"].get("local_taps_um", [])
    t["reset"]["local_taps_um"] = [[round(x, 3), round(y, 3)] for x, y in sites]
    rep["types"][tn] = dict(bands=rb, old_local_taps=old, local_taps=t["reset"]["local_taps_um"], cover_worst_um=round(worst, 2),
                            cover_pts=npts, macro_blockage=blk)
bind = json.load(open(bind_in))
for tn in TYPES:
    bt = bind["partition_types"][tn]
    assert bt["reset"].get("local_taps_um") == rep["types"][tn]["old_local_taps"], tn
    bt["reset"]["local_taps_um"] = copy.deepcopy(gen["partition_types"][tn]["reset"]["local_taps_um"])
Pg, Pb = S.Plan(gen, str(phys)), S.Plan(bind, bind_in)
for tn in TYPES:
    Tg, Tb = RT.for_type(Pg, tn), RT.for_type(Pb, tn)
    assert Tg["depth"] == Tb["depth"] == 5, (tn, Tg["depth"], Tb["depth"])     # event26 depth (old taps, macro ignored) = 5
    assert [x["xy"] for x in Tg["relays"]] == [x["xy"] for x in Tb["relays"]], tn
    rep["types"][tn].update(depth=Tg["depth"], max_hop_um=Tg["max_hop_um"], n_taps=len(Tg["taps"]), n_relays=len(Tg["relays"]),
                            relays=[dict(q=x.get("q"), xy=x["xy"]) for x in Tg["relays"]])
    errs = [e for e in RT.check_type(Pg, tn)] if hasattr(RT, "check_type") else []
    assert not errs, errs[:3]
errs = [e for e in S.validate(gen) if "sys_SD" in e or "physical_" in e or "domain" in e]
assert not errs, errs[:5]
json.dump(gen, open(out / "die_plan_sd33.json", "w"), indent=1)
json.dump(bind, open(out / "bind_plan_sd33.json", "w"), indent=1)
json.dump(rep, open(out / "compose_report.json", "w"), indent=1)
for tn, v in rep["types"].items():
    print(tn, "bands", [(b["bus"], b["new"], b["area"], b["reserve"], b["hop"]) for b in v["bands"]])
    print(tn, "local taps", len(v["local_taps"]), "worst", v["cover_worst_um"], "depth", v["depth"], "max hop", v["max_hop_um"],
          "taps", v["n_taps"], "relays", v["n_relays"])
print("WROTE", out)
