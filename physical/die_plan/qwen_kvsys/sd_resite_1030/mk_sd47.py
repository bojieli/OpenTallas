#!/usr/bin/env python3
"""DIE-KV-47-SD 10-30 one-block geometry re-site of kv3_sys_SD / kv3_sys_SD_v1 on the KV plan of record event28w_c
(12.20 one-block rule, COORD ruling 15:05: DIE-KV-46 ASK default).  Fail-closed plan + sidecar data delta, existing
tools/methods only:
 1. declare the x6 SerDes PHY macro (DIE-KV-46 delta = Codex bc32cb591 form): contents[serdes] physical_inst/master,
    origin [17.28,54], outline [1848.96,972] R0, event33 views (results/kv_serdes_pg_event33); die.pg.domains
    phy_sys_SW_serdes / phy_sys_SE_serdes (VDDPHY, rect = the macro in die frame, DIE-KV-36 sd36A form).
 2. landing storage bands: clock_landing_plan._storage_band in ring_ff mode with the macro (reset_tree.blockages) and
    the PHY supply rects as obstacles (= resize_undersized_bands DIE-KV-42 path; DIE-KV-33 compose form).
 3. reset.local_taps_um: s81_head/head_reset_local_taps.cover_sites (300-um cover, 4.32 grid, bands excluded as
    sites) = DIE-KV-33 compose_sd33 form (the 12 old taps all sit on the macro).
 4. landing collector tree := reset_tree.for_type on the new plan (DIE-S81-36 delta_ves_coll / DIE-KV-36 mk_sd36 form),
    local sources re-tapped to the nearest rst_n_t* within 405 um; same tree + bands in eW_sidecar collector.types.
 5. a band that covers a reset relay/collector site box is re-sited with those boxes as obstacles (FLOW-7 form).
Asserts: outline, buses, pins (landing_contract.pins), count_straps, clock taps, edge clocks, reset depth/own_depth,
every other type, ports, partitions, all non-pg die fields byte-equal; 0 reset/collector sites on macro+halo; hops <=
reach; collector local depth <= sidecar boot local_registered_depths.
usage (repo root): mk_sd47.py PLAN_IN SIDECAR_IN DOMAINS OUT_DIR  -> OUT_DIR/{plan_c.json,eW_sidecar.json,report.json}"""
import copy, hashlib, json, os, re, sys
sys.path.insert(0, os.path.join("tools", "die_plan")); sys.path.insert(0, os.path.join("tools", "s81_head"))
import schema as S, reset_tree as RT, clock_landing_plan as CL, head_reset_local_taps as H  # noqa: E402

TYPES = {"kv3_sys_SD": 522, "kv3_sys_SD_v1": 521}
VIEWS = "results/kv_serdes_pg_event33"
ORIGIN, SIZE = [17.28, 54.0], [1848.96, 972.0]
MAC = (ORIGIN[0] - RT.CLEAR_UM, ORIGIN[1] - RT.CLEAR_UM, ORIGIN[0] + SIZE[0] + RT.CLEAR_UM, ORIGIN[1] + SIZE[1] + RT.CLEAR_UM)
on_mac = lambda p: MAC[0] < p[0] < MAC[2] and MAC[1] < p[1] < MAC[3]
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
ov = lambda a, o: min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

pin, sin, dom, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
raw0 = json.load(open(pin)); raw = copy.deepcopy(raw0)
side0 = json.load(open(sin)); side = copy.deepcopy(side0)
rep = dict(source_plan=pin, source_plan_sha256=sha(pin), source_sidecar=sin, source_sidecar_sha256=sha(sin), types={})

# 1. macro declaration + PHY domains
for tn, w in TYPES.items():
    t = raw["partition_types"][tn]
    assert t["outline_um"] == [1900.8, 1036.8], t["outline_um"]
    cs = [c for c in t["contents"] if c["inst"] == "serdes"]
    assert len(cs) == 1 and cs[0]["module"] == "ot_qfd_serdes_112g_x6_phy" and "lef" not in cs[0], cs
    m = f"ot_qfd_serdes_112g_x6_phy_w{w}"
    cs[0].update(physical_inst="u_bound.u_core.u_phy.g_native.u_macro", physical_master=m, origin_um=list(ORIGIN),
                 outline_um=list(SIZE), orient="R0", lef=f"{VIEWS}/{m}/{m}.lef", lib=f"{VIEWS}/{m}/{m}_tt.lib")
    assert os.path.isfile(cs[0]["lef"]) and os.path.isfile(cs[0]["lib"]), cs[0]
names = {d["name"] for d in raw["die"]["pg"]["domains"]}
for d in json.load(open(dom)):
    assert d["name"] not in names, d["name"]
    raw["die"]["pg"]["domains"].append(d)

P1 = S.Plan(copy.deepcopy(raw), pin)
for tn in TYPES:
    t = raw["partition_types"][tn]; r = rep["types"][tn] = {}
    lc = t["clock"]["landing_contract"]; ct = side["collector"]["types"][tn]
    old_tree = lc["collector_tree"]; assert ct["tree"] == old_tree
    r["old_local_taps"] = t["reset"]["local_taps_um"]
    r["old_local_taps_on_macro"] = sum(on_mac(p) for p in t["reset"]["local_taps_um"])
    r["old_relays_on_macro"] = sorted(x["name"] for x in old_tree["relays"] if on_mac(x["xy"]))
    r["old_bands"] = {k: v["rect_um"] for k, v in lc["bands"].items()}
    # 2. bands (ring_ff, macro + PHY supply obstacles)
    phy = CL.phy_supply_rects(P1, tn)
    r["phy_supply_rects"] = phy
    tt = copy.deepcopy(t); tt["_cland_geom"] = copy.deepcopy(ct["bus_geometry"])
    saved = (CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING)
    CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING = "ring_ff", 1.0, "all"

    def site_bands(resets=()):
        used, nbs = [], {}
        for bus in sorted(lc["bands"]):
            b = lc["bands"][bus]
            assert not bus.startswith("monitor_") and b.get("rect_um"), bus
            nb = CL._storage_band(tt, bus, int(b["width"]), list(used), phy=phy, resets=list(resets))
            nb.update(instance=b.get("instance", "u_cland_" + bus), resized_from_um=list(b["rect_um"]),
                      resize="DIE-KV-47-SD one-block re-site: band off the declared x6 PHY macro / VDDPHY region (ring_ff reserve)")
            used.append(nb["rect_um"]); nbs[bus] = nb
        return nbs
    try:
        resets = []
        for it in range(4):
            nbs = site_bands(resets)
            bands = [v["rect_um"] for v in nbs.values()]
            # 3. local reset taps off the macro, not inside a band
            sites, worst, npts = H.cover_sites(1900.8, 1036.8, RT.blockages(t), RT.CLEAR_UM, 300.0, g=4.32, site_excl=bands)
            t["reset"]["local_taps_um"] = [[round(float(x), 3), round(float(y), 3)] for x, y in sites]
            lc["bands"] = nbs
            P2 = S.Plan(copy.deepcopy(raw), pin)
            T = json.loads(json.dumps(RT.for_type(P2, tn)))
            rs = CL.reset_site_rects(T)
            hit = [b for b in bands if any(ov(b, o) for o in rs)]
            r["iterations"] = it + 1
            if not hit:
                break
            resets = sorted({tuple(o) for o in resets} | {tuple(o) for o in rs})
        else:
            raise SystemExit(f"{tn}: band / reset-site overlap does not converge")
    finally:
        CL.BAND_RESERVE, CL.BAND_SPREAD, CL.BAND_RING = saved
    for b in lc["bands"].values():
        assert not ov(b["rect_um"], MAC) and not any(ov(b["rect_um"], o) for o in phy), b
    # 4. collector tree = the new reset tree; local sources re-tapped
    assert T["depth"] == old_tree["depth"] and T["own_depth"] == old_tree["own_depth"], (tn, T["depth"], old_tree["depth"])
    assert T["taps"][:5] == old_tree["taps"][:5], "clock taps changed"
    assert T["max_hop_um"] <= T["reach_um"] + 1e-6, T["max_hop_um"]
    on = [x["name"] for x in T["relays"] if on_mac(x["xy"])] + (["root"] if on_mac(T["root"]) else [])
    assert not on, (tn, on)
    taps = {x["q"]: x["xy"] for x in T["relays"] if x["q"].startswith("rst_n_t")}
    srcs, rec = [], []
    for s_ in lc["collector_local_sources"]:
        q, xy = min(taps.items(), key=lambda kv: (man(kv[1], s_["xy_um"]), kv[0]))
        hop = man(xy, s_["xy_um"]); assert hop <= 405.0 + 1e-6, (s_["name"], q, hop)
        s2 = copy.deepcopy(s_); s2["tap"] = int(q[len("rst_n_t"):]); s2["band"] = copy.deepcopy(lc["bands"][s_["name"]])
        srcs.append(s2); rec.append(dict(source=s_["name"], old_tap=s_["tap"], new_tap=s2["tap"], hop_um=round(hop, 2)))
    assert not lc["collector_children"] and not ct["children"]
    par = {x["q"]: x["d"] for x in T["relays"]}
    def dep(n):
        k = 0
        while n != lc["collector_root_node"]:
            n = par[n]; k += 1
        return k
    cdep = max(dep(f"rst_n_t{s_['tap']}") for s_ in srcs) + 1
    pn = {"kv3_sys_SD": "sys_SW", "kv3_sys_SD_v1": "sys_SE"}[tn]
    budget = side["collector"]["boot_budget"]["local_registered_depths"][pn]
    assert cdep <= budget, (tn, cdep, budget)
    lc["collector_tree"] = T; lc["collector_local_sources"] = srcs
    ct["tree"] = copy.deepcopy(T); ct["local_sources"] = copy.deepcopy(srcs); ct["bands"] = copy.deepcopy(lc["bands"])
    r.update(new_local_taps=t["reset"]["local_taps_um"], cover_worst_um=round(float(worst), 2), cover_pts=int(npts),
             new_bands={k: dict(rect_um=v["rect_um"], area_um2=round((v["rect_um"][2]-v["rect_um"][0])*(v["rect_um"][3]-v["rect_um"][1]), 1),
                                reserve_um2=v["area_reserve_um2"], hop_um=v["max_pin_to_band_hop_um"]) for k, v in lc["bands"].items()},
             depth=T["depth"], own_depth=T["own_depth"], max_hop_um=T["max_hop_um"], reach_um=T["reach_um"],
             relays=[len(old_tree["relays"]), len(T["relays"])], new_relays_on_macro=0, sources=rec,
             collector_local_depth=cdep, boot_local_depth_budget=budget,
             old_sites_on_macro_total=r["old_local_taps_on_macro"] + len(r["old_relays_on_macro"]))

# fail closed: nothing else changed
for k in raw:
    if k not in ("partition_types", "die"):
        assert raw[k] == raw0[k], k
assert {k: v for k, v in raw["die"].items() if k != "pg"} == {k: v for k, v in raw0["die"].items() if k != "pg"}
assert {k: v for k, v in raw["die"]["pg"].items() if k != "domains"} == {k: v for k, v in raw0["die"]["pg"].items() if k != "domains"}
for tn in raw["partition_types"]:
    if tn not in TYPES:
        assert raw["partition_types"][tn] == raw0["partition_types"][tn], tn
        continue
    a, b = raw["partition_types"][tn], raw0["partition_types"][tn]
    for k in a:
        if k not in ("contents", "reset", "clock"):
            assert a[k] == b[k], (tn, k)
    assert {k: v for k, v in a["reset"].items() if k != "local_taps_um"} == {k: v for k, v in b["reset"].items() if k != "local_taps_um"}
    ca, cb = a["clock"], b["clock"]
    assert {k: v for k, v in ca.items() if k != "landing_contract"} == {k: v for k, v in cb.items() if k != "landing_contract"}
    la, lb = ca["landing_contract"], cb["landing_contract"]
    for k in la:
        if k not in ("bands", "collector_tree", "collector_local_sources"):
            assert la[k] == lb[k], (tn, k)
for k in side:
    if k != "collector":
        assert side[k] == side0[k], k
for k in side["collector"]:
    if k != "types":
        assert side["collector"][k] == side0["collector"][k], k
for tn in side["collector"]["types"]:
    if tn not in TYPES:
        assert side["collector"]["types"][tn] == side0["collector"]["types"][tn], tn
raw["note"] = raw0["note"] + " | DIE-KV-47-SD (12.20 one-block, COORD 15:05 10-30): kv3_sys_SD/_v1 x6 SerDes PHY macro declared (event33 views) + VDDPHY_SW/SE domains; reset local taps, landing bands and collector tree re-sited off the macro (existing tools; pins/outline/neighbours unchanged)"
pp, sp = os.path.join(out, "plan_c.json"), os.path.join(out, "eW_sidecar.json")
open(pp, "w").write(json.dumps(raw, indent=1) + "\n")
open(sp, "w").write(json.dumps(side, indent=1) + "\n")
rep.update(plan_sha256=sha(pp), sidecar_sha256=sha(sp))
json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
for tn, r in rep["types"].items():
    print(tn, "old on-macro sites", r["old_sites_on_macro_total"], "(taps", r["old_local_taps_on_macro"], "relays", len(r["old_relays_on_macro"]), ")",
          "| new taps", len(r["new_local_taps"]), "cover", r["cover_worst_um"], "| depth", r["depth"], "hop", r["max_hop_um"],
          "relays", r["relays"], "| bands", {k: (v["rect_um"], v["area_um2"], v["hop_um"]) for k, v in r["new_bands"].items()},
          "| sources", r["sources"], "cdep", r["collector_local_depth"], "/", r["boot_local_depth_budget"], "it", r["iterations"])
print("WROTE", pp, rep["plan_sha256"][:12], sp, rep["sidecar_sha256"][:12])
